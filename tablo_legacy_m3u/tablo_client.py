"""HTTP client for the legacy Tablo device API.

Channels and airings are cached in a shared TTL cache. `get_channels()`,
`get_airings()`, and `get_tuners()` use double-checked locking to coalesce concurrent
requests: only one thread fetches while others wait and receive the cached result.
`refresh_channels()`, `refresh_airings()`, and `refresh_tuners()` bypass the cache check
and write fresh data directly. `refresh_channels()` and `refresh_airings()` are used
by background schedulers for periodic refresh, while `refresh_tuners()` is used by
request-driven paths such as `/watch` to refresh tuner state on demand.
"""

import logging
import threading

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

import requests

from cachetools import TTLCache
from cachetools.keys import hashkey
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tablo_legacy_m3u.config import DEFAULT_CACHE_TTL
from tablo_legacy_m3u.tablo_types import (
    Airing,
    BatchChannelResponse,
    Channel,
    DiscoveryResponse,
    GuideStatus,
    HarddriveInfo,
    ServerInfo,
    SubscriptionResponse,
    TunerStatus,
    WatchResponse,
)

if TYPE_CHECKING:
    from collections.abc import Hashable

# Batching parameters for fetching channels and airings
BATCH_SIZE = 50
MAX_CONCURRENT_BATCHES = 3

# Tablo API ports
TABLO_API_PORT = 8885
TABLO_DISCOVERY_URL = "https://api.tablotv.com/assocserver/getipinfo/"

REQUEST_TIMEOUT = 10
RETRY_COUNT = 2

TUNER_CACHE_TTL = 2


logger = logging.getLogger(__name__)


class TabloServerBusyError(requests.HTTPError):
    """Tablo returned server_busy with a retry hint."""

    def __init__(self, response: requests.Response, retry_in_ms: int) -> None:
        """Initialize with the response and retry delay."""
        self.retry_in_s: float = retry_in_ms / 1000
        super().__init__(
            f"Server busy, retry in {self.retry_in_s:.0f}s",
            response=response,
        )


class TabloClient:
    """Client for interacting with a legacy Tablo device."""

    def __init__(
        self,
        tablo_ip: str,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        tuner_cache_ttl: int = TUNER_CACHE_TTL,
    ) -> None:
        """Initialize with a resolved Tablo IP address.

        For most API calls, each thread uses its own persistent HTTP session with
        connection pooling via the internal `_get` and `_post` helpers, which provide
        automatic retry (with exponential backoff) for transient connection errors and
        `502`/`503`/`504` responses. Certain specialized calls, such as the watch
        endpoint used by `get_watch_url`, intentionally bypass this session and use a
        one-off `requests.post()` without connection pooling or adapter-level retries.

        """
        self.base_url: str = f"http://{tablo_ip}:{TABLO_API_PORT}"
        self._cache: TTLCache[Hashable, Any] = TTLCache(maxsize=4, ttl=cache_ttl)
        self._cache_lock = threading.Lock()
        self._tuner_cache: TTLCache[Hashable, Any] = TTLCache(
            maxsize=1, ttl=tuner_cache_ttl
        )
        self._fetch_locks: dict[str, threading.Lock] = {
            "channels": threading.Lock(),
            "airings": threading.Lock(),
            "tuners": threading.Lock(),
        }
        self._local = threading.local()
        self._retry = Retry(
            total=RETRY_COUNT,
            backoff_factor=0.5,
            allowed_methods={"GET", "POST"},
            status_forcelist=[502, 504],
            raise_on_status=False,
        )

    @property
    def _session(self) -> requests.Session:
        """Return a thread-local session, creating one if needed."""
        session: requests.Session | None = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.mount("http://", HTTPAdapter(max_retries=self._retry))
            self._local.session = session
        return session

    def _get(self, path: str) -> Any:
        """Make a GET request to the Tablo API."""
        response = self._session.get(f"{self.base_url}{path}", timeout=REQUEST_TIMEOUT)
        logger.debug(
            "GET %s %s (%.3fs)",
            path,
            response.status_code,
            response.elapsed.total_seconds(),
        )

        if not response.ok:
            try:
                body = response.json()
                details = body.get("error", {}).get("details", {})
                if details.get("reason") == "server_busy" and "retry_in" in details:
                    raise TabloServerBusyError(response, int(details["retry_in"]))
            except TabloServerBusyError:
                raise
            except Exception:  # noqa: BLE001, Malformed body falls through to raise_for_status
                logger.debug("Could not parse server_busy details from %s", path)

            logger.error("GET %s failed: %s", path, response.text)
            response.raise_for_status()

        return response.json()

    def _post(self, path: str, json: Any = None) -> Any:
        """Make a POST request to the Tablo API."""
        response = self._session.post(
            f"{self.base_url}{path}", json=json, timeout=REQUEST_TIMEOUT
        )
        logger.debug(
            "POST %s %s (%.3fs)",
            path,
            response.status_code,
            response.elapsed.total_seconds(),
        )

        if not response.ok:
            logger.error("POST %s failed: %s", path, response.text)
        response.raise_for_status()

        return response.json()

    def _batch(self, paths: list[str]) -> dict[str, Any]:
        """Fetch multiple resources in one call via POST `/batch`."""
        result: dict[str, Any] = self._post("/batch", json=paths)

        return result

    def _chunked_batch(self, paths: list[str]) -> dict[str, Any]:
        """Fetch paths via `/batch` in parallel chunks."""
        chunks = [paths[i : i + BATCH_SIZE] for i in range(0, len(paths), BATCH_SIZE)]

        results: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES) as executor:
            for batch_result in executor.map(self._batch, chunks):
                results.update(batch_result)

        return results

    def refresh_channels(self) -> list[Channel]:
        """Fetch fresh channel data and write directly into cache."""
        with self._fetch_locks["channels"]:
            channels = self._fetch_channels()

            with self._cache_lock:
                self._cache[hashkey("channels")] = channels

            return channels

    def _fetch_channels(self) -> list[Channel]:
        """Fetch channel data from the Tablo API.

        First GETs the channel path list, then hydrates via POST `/batch`.
        """
        paths: list[str] = self._get("/guide/channels")
        logger.debug("Found %d channel paths", len(paths))

        if not paths:
            logger.info("No channels found")
            return []

        batch: BatchChannelResponse = self._chunked_batch(paths)
        channels = list(batch.values())

        logger.debug("Hydrated %d channels", len(channels))

        return channels

    def get_channels(self) -> list[Channel]:
        """Return cached channels, fetching with coalescing if needed."""
        key = hashkey("channels")

        with self._cache_lock:
            cached: list[Channel] | None = self._cache.get(key)

        if cached is not None:
            return cached

        with self._fetch_locks["channels"]:
            with self._cache_lock:
                rechecked: list[Channel] | None = self._cache.get(key)

            if rechecked is not None:
                return rechecked

            channels = self._fetch_channels()
            with self._cache_lock:
                self._cache[key] = channels

            return channels

    def get_server_info(self) -> ServerInfo:
        """Fetch device info from `/server/info`."""
        server_info: ServerInfo = self._get("/server/info")
        model = server_info["model"]

        logger.info(
            "Tablo Server: %s (%s, %d tuners)",
            server_info["name"],
            model["name"],
            model["tuners"],
        )

        return server_info

    def _fetch_tuners(self) -> list[TunerStatus]:
        """Fetch tuner status from `/server/tuners`."""
        tuners: list[TunerStatus] = self._get("/server/tuners")
        return tuners

    def get_tuners(self) -> list[TunerStatus]:
        """Return cached tuner status, fetching with coalescing if needed."""
        key = hashkey("tuners")

        with self._cache_lock:
            cached: list[TunerStatus] | None = self._tuner_cache.get(key)

        if cached is not None:
            return cached

        with self._fetch_locks["tuners"]:
            with self._cache_lock:
                rechecked: list[TunerStatus] | None = self._tuner_cache.get(key)

            if rechecked is not None:
                return rechecked

            tuners = self._fetch_tuners()
            with self._cache_lock:
                self._tuner_cache[key] = tuners

            return tuners

    def refresh_tuners(self) -> list[TunerStatus]:
        """Fetch fresh tuner data and write directly into cache."""
        with self._fetch_locks["tuners"]:
            tuners = self._fetch_tuners()

            with self._cache_lock:
                self._tuner_cache[hashkey("tuners")] = tuners

            return tuners

    def get_harddrives(self) -> list[HarddriveInfo]:
        """Fetch storage device info from `/server/harddrives`."""
        harddrives: list[HarddriveInfo] = self._get("/server/harddrives")
        return harddrives

    def get_guide_status(self) -> GuideStatus:
        """Fetch guide data status from `/server/guide/status`."""
        guide_status: GuideStatus = self._get("/server/guide/status")
        return guide_status

    def has_guide_subscription(self) -> bool:
        """Check if the Tablo has an active guide data subscription."""
        data: SubscriptionResponse = self._get("/account/subscription")

        active = any(
            sub["kind"] == "guide" and sub["state"] == "active"
            for sub in data["subscriptions"]
        )

        logger.info("Tablo guide subscription: active=%s", active)

        return active

    def get_watch_url(self, channel_path: str) -> str:
        """Start a live stream and return the playlist URL.

        Uses a one-off request (no retry) since starting a stream is not idempotent.

        Args:
            channel_path: The channel path (e.g., `/guide/channels/1027125`).

        Returns:
            The HLS playlist URL for the live stream.
        """
        response = requests.post(
            f"{self.base_url}{channel_path}/watch", json=None, timeout=REQUEST_TIMEOUT
        )

        if not response.ok:
            logger.error("POST %s/watch failed: %s", channel_path, response.text)
        response.raise_for_status()

        data: WatchResponse = response.json()

        logger.debug(
            "Watch response for %s: token=%s...", channel_path, data["token"][:8]
        )

        return data["playlist_url"]

    def _fetch_airings(self) -> list[Airing]:
        """Fetch all upcoming guide airings from the Tablo."""
        paths: list[str] = self._get("/guide/airings")
        logger.debug("Found %d airing paths", len(paths))

        if not paths:
            logger.info("No airings found")
            return []

        batch: dict[str, Airing | None] = self._chunked_batch(paths)
        airings = [v for v in batch.values() if v is not None]

        logger.debug("Hydrated %d airings", len(airings))

        return airings

    def get_airings(self) -> list[Airing]:
        """Return cached airings, fetching with coalescing if needed."""
        key = hashkey("airings")

        with self._cache_lock:
            cached: list[Airing] | None = self._cache.get(key)

        if cached is not None:
            return cached

        with self._fetch_locks["airings"]:
            with self._cache_lock:
                rechecked: list[Airing] | None = self._cache.get(key)

            if rechecked is not None:
                return rechecked

            airings = self._fetch_airings()
            with self._cache_lock:
                self._cache[key] = airings

            return airings

    def refresh_airings(self) -> list[Airing]:
        """Fetch fresh airing data and write directly into cache."""
        with self._fetch_locks["airings"]:
            airings = self._fetch_airings()

            with self._cache_lock:
                self._cache[hashkey("airings")] = airings

            return airings


def discover_tablo_ip(autodiscover: bool, tablo_ip: str) -> str:
    """Resolve the Tablo device IP address.

    Args:
        autodiscover: Whether to use the cloud discovery API.
        tablo_ip: Manually configured IP (used if autodiscover is False).

    Returns:
        The Tablo device's private IP address.

    Raises:
        RuntimeError: If no Tablo device can be found.
    """
    if not autodiscover and tablo_ip:
        return tablo_ip

    if not autodiscover and not tablo_ip:
        msg = "No Tablo IP provided and autodiscover is disabled"
        raise RuntimeError(msg)

    response = requests.get(TABLO_DISCOVERY_URL, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data: DiscoveryResponse = response.json()

    cpes = data.get("cpes", [])

    if not cpes:
        msg = "No Tablo devices found via cloud discovery"
        raise RuntimeError(msg)

    logger.info(
        "Discovery: found %d device(s), using %s",
        len(cpes),
        cpes[0]["private_ip"],
    )

    return cpes[0]["private_ip"]
