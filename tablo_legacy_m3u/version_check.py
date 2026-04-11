"""Utilities for checking the latest release version on GitHub."""

import logging

from concurrent.futures import ThreadPoolExecutor

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
        self._cache: TTLCache[str, str | None] = TTLCache(
            maxsize=1, ttl=CACHE_TTL_SECONDS
        )
        self._executor = ThreadPoolExecutor(max_workers=1)

    def get_latest_version(self) -> str | None:
        """Return the cached latest version, refreshing in the background if stale."""
        if not self._enabled:
            return None

        cached = self._cache.get("latest")
        if cached is not None:
            return cached

        self._executor.submit(self._refresh)
        return None

    def _refresh(self) -> None:
        """Fetch and cache the latest version."""
        latest = check_latest_version()
        if is_update_available(current=__version__, latest=latest):
            self._cache["latest"] = latest


def check_latest_version() -> str | None:
    """Fetch the latest release version from GitHub. Returns None on failure."""
    try:
        resp = requests.get(
            RELEASES_URL,
            headers={"Accept": "application/vnd.github.v3+json"},
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
