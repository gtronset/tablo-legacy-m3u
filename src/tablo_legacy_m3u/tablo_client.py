"""HTTP client for the legacy Tablo device API."""

import logging

from typing import Any

import requests

from tablo_legacy_m3u.tablo_types import DiscoveryResponse, ServerInfo

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

    def get_server_info(self) -> ServerInfo:
        """Fetch device info from /server/info."""
        server_info: ServerInfo = self._get("/server/info")
        logger.debug("Tablo server info: %s", server_info)

        return server_info


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

    response = requests.get(TABLO_DISCOVERY_URL, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data: DiscoveryResponse = response.json()

    logger.debug("Cloud discovery response: %s", data)

    cpes = data.get("cpes", [])
    if not cpes:
        msg = "No Tablo devices found via cloud discovery"
        raise RuntimeError(msg)

    return cpes[0]["private_ip"]
