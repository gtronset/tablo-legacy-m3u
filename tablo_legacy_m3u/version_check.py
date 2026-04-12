"""Utilities for checking the latest release version on GitHub."""

import logging
import threading

from concurrent.futures import Future, ThreadPoolExecutor

import requests

from cachetools import TTLCache
from packaging.version import InvalidVersion, Version

from tablo_legacy_m3u._version import __version__

logger = logging.getLogger(__name__)

REPOSITORY = "gtronset/tablo-legacy-m3u"
RELEASES_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"

CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours


class VersionChecker:
    """Checks GitHub for newer releases, caching results with a TTL."""

    def __init__(self, *, enabled: bool = True) -> None:
        """Initialize the version checker."""
        self._enabled = enabled
        self._lock = threading.Lock()
        self._cache: TTLCache[str, str | None] = TTLCache(
            maxsize=1, ttl=CACHE_TTL_SECONDS
        )
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._refresh_future: Future[None] | None = None

    def _submit_refresh(self) -> None:
        """Submit a background refresh if one isn't already in flight."""
        with self._lock:
            if self._refresh_future is not None and not self._refresh_future.done():
                return
            self._refresh_future = self._executor.submit(self._refresh)

    def get_latest_version(self) -> str | None:
        """Return the cached latest version, refreshing in the background if stale.

        Caches negative results to avoid repeated failed fetches.
        """
        if not self._enabled:
            return None

        with self._lock:
            cached = self._cache.get("latest")

        if cached is not None:
            return cached or None

        self._submit_refresh()

        return None

    def _refresh(self) -> None:
        """Fetch and cache the latest version.

        Caches negative results as empty string to avoid repeated failed fetches.
        """
        latest = check_latest_version()

        with self._lock:
            if is_update_available(current=__version__, latest=latest):
                self._cache["latest"] = latest
            else:
                self._cache["latest"] = ""

    def shutdown(self) -> None:
        """Shut down the background executor."""
        self._executor.shutdown(wait=False, cancel_futures=True)


def check_latest_version() -> str | None:
    """Fetch the latest release version from GitHub. Returns None on failure."""
    try:
        resp = requests.get(
            RELEASES_URL,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": f"tablo-legacy-m3u/{__version__}",
            },
            timeout=5,
        )
        resp.raise_for_status()
        tag: str = resp.json().get("tag_name", "")

        return tag.lstrip("v")
    except Exception:
        logger.debug("Failed to check for updates", exc_info=True)
        return None


def is_update_available(current: str, latest: str | None) -> bool:
    """Compare latest version against the running version."""
    if latest is None:
        return False
    try:
        return Version(latest) > Version(current)
    except InvalidVersion:
        return False
