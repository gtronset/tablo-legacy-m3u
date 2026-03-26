"""HTTP client for the legacy Tablo device API."""

import logging

from typing import Any

import requests

from tablo_legacy_m3u.tablo_types import (
    BatchChannelResponse,
    Channel,
    DiscoveryResponse,
    ServerInfo,
    SubscriptionResponse,
    WatchResponse,
)

# Tablo API ports
TABLO_API_PORT = 8885
TABLO_DISCOVERY_URL = "https://api.tablotv.com/assocserver/getipinfo/"

# Request timeout (seconds)
REQUEST_TIMEOUT = 10

logger = logging.getLogger(__name__)


class TabloClient:
    """Client for interacting with a legacy Tablo device."""

    def __init__(self, tablo_ip: str) -> None:
        """Initialize with a resolved Tablo IP address."""
        self.base_url = f"http://{tablo_ip}:{TABLO_API_PORT}"

    def _get(self, path: str) -> Any:
        """Make a GET request to the Tablo API."""
        response = requests.get(f"{self.base_url}{path}", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        return response.json()

    def _post(self, path: str, json: Any = None) -> Any:
        """Make a POST request to the Tablo API."""
        response = requests.post(
            f"{self.base_url}{path}", json=json, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        return response.json()

    def _batch(self, paths: list[str]) -> dict[str, Any]:
        """Fetch multiple resources in one call via POST `/batch`."""
        result: dict[str, Any] = self._post("/batch", json=paths)

        return result

    def get_channels(self) -> list[Channel]:
        """Fetch all channel details from the Tablo.

        First GETs the channel path list, then hydrates via POST `/batch`.
        """
        paths: list[str] = self._get("/guide/channels")
        logger.debug("Found %d channel paths", len(paths))

        if not paths:
            logger.info("No channels found")
            return []

        batch: BatchChannelResponse = self._batch(paths)
        channels = list(batch.values())

        logger.debug("Hydrated %d channels", len(channels))

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

        Args:
            channel_path: The channel path (e.g., `/guide/channels/1027125`).

        Returns:
            The HLS playlist URL for the live stream.
        """
        data: WatchResponse = self._post(f"{channel_path}/watch")
        logger.debug("Watch response for %s: token=%s", channel_path, data["token"])

        return data["playlist_url"]


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
