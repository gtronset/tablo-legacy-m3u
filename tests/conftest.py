"""Pytest fixtures for testing."""

import pytest

from tablo_legacy_m3u.tablo_types import ServerInfo


@pytest.fixture
def server_info(
    request: pytest.FixtureRequest,
) -> ServerInfo:
    """Fake Tablo server info for testing."""
    tablo_ip = getattr(request, "param", "10.0.0.123")

    return {
        "server_id": "SID_TEST123",
        "name": "Test Tablo",
        "timezone": "",
        "deprecated": "timezone",
        "version": "2.2.42",
        "local_address": tablo_ip,
        "setup_completed": True,
        "build_number": 1234,
        "model": {
            "wifi": False,
            "tuners": 4,
            "type": "quad",
            "name": "TABLO_QUAD",
        },
        "availability": "available",
        "cache_key": "abc123",
        "product": "tablo",
    }
