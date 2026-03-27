"""Pytest fixtures for testing."""

import pytest

from tablo_legacy_m3u.tablo_types import ServerInfo


@pytest.fixture
def server_info() -> ServerInfo:
    """Fake Tablo server info for testing."""
    return {
        "server_id": "SID_TEST123",
        "name": "Test Tablo",
        "timezone": "",
        "deprecated": "timezone",
        "version": "2.2.42",
        "local_address": "10.0.0.123",
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
