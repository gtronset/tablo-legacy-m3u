"""Pytest fixtures for testing."""

from unittest.mock import MagicMock

import pytest

from flask.testing import FlaskClient

from tablo_legacy_m3u import create_app
from tablo_legacy_m3u.app_state import AppState, InitPhase
from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.scheduler import Scheduler
from tablo_legacy_m3u.tablo_client import TabloClient
from tablo_legacy_m3u.tablo_types import ServerInfo

TABLO_IP = "192.168.1.100"


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


@pytest.fixture
def tablo_client_mock() -> MagicMock:
    """Mock TabloClient for route tests."""
    return MagicMock()


@pytest.fixture
def tablo_client() -> TabloClient:
    """TabloClient pointed at a fake IP."""
    return TabloClient(TABLO_IP)


@pytest.fixture
def flask_client(
    request: pytest.FixtureRequest,
    server_info: ServerInfo,
    tablo_client_mock: MagicMock,
) -> FlaskClient:
    """Flask test client with configurable app config."""
    config = getattr(request, "param", Config())

    app_state = AppState()
    app_state.tablo_client = tablo_client_mock
    app_state.device_status.server_info = server_info
    app_state.enable_epg = True
    app_state.set_phase(InitPhase.READY)

    app = create_app(config=config, app_state=app_state)

    return app.test_client()


@pytest.fixture
def scheduler_task() -> MagicMock:
    """Mock callable used as the scheduler task."""
    return MagicMock()


@pytest.fixture
def scheduler(scheduler_task: MagicMock) -> Scheduler:
    """Scheduler with a 300s interval and mock task."""
    return Scheduler("test", 300, scheduler_task)
