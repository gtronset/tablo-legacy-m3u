"""Tests for the Flask application routes partials."""

from http import HTTPStatus
from unittest.mock import MagicMock

from flask.testing import FlaskClient

from tablo_legacy_m3u import create_app
from tablo_legacy_m3u.app_state import AppState, InitPhase
from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.scheduler import Scheduler
from tablo_legacy_m3u.tablo_types import ServerInfo


class TestEvents:
    """Tests for GET `/events`."""

    def test_returns_event_stream_content_type(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/events")

        assert resp.status_code == HTTPStatus.OK
        assert "text/event-stream" in resp.content_type


class TestPartialStatus:
    """Tests for GET `/partials/status`."""

    def test_returns_200_when_ready(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/partials/status")

        assert resp.status_code == HTTPStatus.OK
        assert "text/html" in resp.content_type

    def test_contains_server_running(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/partials/status")

        body = resp.data.decode()

        assert "Running" in body

    def test_contains_scheduler_rows(
        self,
        server_info: ServerInfo,
        tablo_client_mock: MagicMock,
    ) -> None:
        app_state = AppState()
        app_state.tablo_client = tablo_client_mock
        app_state.device_status.server_info = server_info
        app_state.enable_epg = True
        app_state.schedulers = [
            Scheduler("channels", 300, MagicMock()),
        ]
        app_state.set_phase(InitPhase.READY)

        app = create_app(config=Config(), app_state=app_state)
        resp = app.test_client().get("/partials/status")

        body = resp.data.decode()

        assert "Channels" in body

    def test_shows_epg_disabled(
        self,
        server_info: ServerInfo,
        tablo_client_mock: MagicMock,
    ) -> None:
        app_state = AppState()
        app_state.tablo_client = tablo_client_mock
        app_state.device_status.server_info = server_info
        app_state.enable_epg = False
        app_state.set_phase(InitPhase.READY)

        app = create_app(config=Config(), app_state=app_state)
        resp = app.test_client().get("/partials/status")

        body = resp.data.decode()

        assert "EPG Disabled" in body

    def test_returns_503_when_not_ready(self) -> None:
        app_state = AppState()
        app = create_app(config=Config(), app_state=app_state)

        resp = app.test_client().get("/partials/status")

        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE


class TestPartialTuners:
    """Tests for GET `/partials/tuners`."""

    def test_returns_200_when_ready(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/partials/tuners")

        assert resp.status_code == HTTPStatus.OK
        assert "text/html" in resp.content_type

    def test_contains_tuner_dots(
        self,
        flask_client: FlaskClient,
        app_state: AppState,
    ) -> None:
        app_state.device_status.tuners = [
            {
                "in_use": True,
                "channel": None,
                "recording": None,
                "channel_identifier": "wabc",
            },
            {
                "in_use": False,
                "channel": None,
                "recording": None,
                "channel_identifier": None,
            },
        ]

        resp = flask_client.get("/partials/tuners")

        body = resp.data.decode()

        assert "dot-active" in body
        assert "dot-free" in body

    def test_empty_when_no_tuners(
        self,
        flask_client: FlaskClient,
        app_state: AppState,
    ) -> None:
        app_state.device_status.tuners = []

        resp = flask_client.get("/partials/tuners")

        body = resp.data.decode()

        assert "dot-" not in body

    def test_returns_503_when_not_ready(self) -> None:
        app_state = AppState()
        app = create_app(config=Config(), app_state=app_state)

        resp = app.test_client().get("/partials/tuners")

        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE


class TestPartialDevice:
    """Tests for GET `/partials/device`."""

    def test_returns_200_when_ready(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/partials/device")

        assert resp.status_code == HTTPStatus.OK
        assert "text/html" in resp.content_type

    def test_contains_storage_info(
        self,
        flask_client: FlaskClient,
        app_state: AppState,
    ) -> None:
        app_state.device_status.harddrives = [
            {
                "name": "sda",
                "connected": True,
                "format_state": "ok",
                "busy_state": "idle",
                "kind": "internal",
                "size": 1_000_000_000_000,
                "usage": 500_000_000_000,
                "free": 500_000_000_000,
                "error": None,
            },
        ]

        resp = flask_client.get("/partials/device")

        body = resp.data.decode()

        assert "Storage" in body
        assert "storage-fill" in body

    def test_empty_when_no_device_data(
        self,
        flask_client: FlaskClient,
        app_state: AppState,
    ) -> None:
        app_state.device_status.harddrives = []
        app_state.device_status.guide_status = None
        app_state.device_status.last_probe = None

        resp = flask_client.get("/partials/device")

        body = resp.data.decode()

        assert "Storage" not in body
        assert "Guide" not in body

    def test_returns_503_when_not_ready(self) -> None:
        app_state = AppState()
        app = create_app(config=Config(), app_state=app_state)

        resp = app.test_client().get("/partials/device")

        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE
