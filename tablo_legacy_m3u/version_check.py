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

_executor = ThreadPoolExecutor(max_workers=1)
_cache: TTLCache[str, str | None] = TTLCache(maxsize=1, ttl=CACHE_TTL_SECONDS)


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


def is_update_available(latest: str | None) -> bool:
    """Compare latest version against the running version."""
    if latest is None:
        return False
    try:
        return Version(latest) > Version(__version__)
    except InvalidVersion:
        return False


def get_latest_version() -> str | None:
    """Return the cached latest version, refreshing in the background if stale."""
    cached = _cache.get("latest")
    if cached is not None:
        return cached

    # First call or cache expired — fire background check
    _executor.submit(_refresh_cache)
    return _cache.get("latest")


def _refresh_cache() -> None:
    """Fetch and cache the latest version."""
    latest = check_latest_version()
    if is_update_available(latest):
        _cache["latest"] = latest
