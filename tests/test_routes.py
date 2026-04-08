"""Tests for the Flask application routes."""

from http import HTTPStatus
from unittest.mock import MagicMock

import pytest

from flask.testing import FlaskClient

from tablo_legacy_m3u import create_app
from tablo_legacy_m3u.app_state import AppState, InitPhase
from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.tablo_types import ServerInfo
from tests.helpers import make_channel, make_episode_airing

TABLO_IP: str = "10.0.0.123"


class TestIndex:
    """Tests for GET `/`."""

    def test_returns_html_content_type(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/")

        assert resp.status_code == HTTPStatus.OK
        assert "text/html" in resp.content_type

    def test_contains_device_name(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/")

        body = resp.data.decode()

        assert "Test Tablo" in body

    def test_contains_endpoint_links(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/")

        body = resp.data.decode()

        assert "/lineup.m3u" in body
        assert "/discover.json" in body

    def test_shows_epg_disabled_when_epg_not_enabled(
        self, server_info: ServerInfo, tablo_client_mock: MagicMock
    ) -> None:
        app_state = AppState()
        app_state.tablo_client = tablo_client_mock
        app_state.device_status.server_info = server_info
        app_state.enable_epg = False
        app_state.set_phase(InitPhase.READY)

        app = create_app(config=Config(), app_state=app_state)

        resp = app.test_client().get("/")

        body = resp.data.decode()

        assert "EPG Disabled" in body

    def test_shows_epg_link_when_enabled(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/")

        body = resp.data.decode()

        assert "/xmltv.xml" in body


class TestIndexNotReady:
    """The index page works even before init completes."""

    def test_returns_200_when_not_ready(self) -> None:
        app_state = AppState()
        app = create_app(config=Config(), app_state=app_state)

        resp = app.test_client().get("/")

        assert resp.status_code == HTTPStatus.OK

    def test_contains_auto_refresh_when_not_ready(self) -> None:
        app_state = AppState()
        app = create_app(config=Config(), app_state=app_state)

        resp = app.test_client().get("/")
        body = resp.data.decode()

        assert '<meta http-equiv="refresh" content="5">' in body

    def test_no_auto_refresh_when_ready(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/")
        body = resp.data.decode()

        assert 'http-equiv="refresh"' not in body

    def test_no_auto_refresh_when_error(self) -> None:
        app_state = AppState()
        app_state.set_phase(InitPhase.ERROR)
        app = create_app(config=Config(), app_state=app_state)

        resp = app.test_client().get("/")
        body = resp.data.decode()

        assert 'http-equiv="refresh"' not in body


class TestFavicon:
    """Tests for GET `/favicon.ico`."""

    def test_returns_icon(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/favicon.ico")

        assert resp.status_code == HTTPStatus.OK
        assert "image/" in resp.content_type
        assert len(resp.data) > 0


class TestHealth:
    """Tests for GET `/health`."""

    def test_returns_ready_when_initialized(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/health")

        assert resp.status_code == HTTPStatus.OK
        assert resp.get_json() == {"status": "ready"}

    def test_returns_discovering_when_not_ready(self) -> None:
        app_state = AppState()  # defaults to DISCOVERING, ready not set

        app = create_app(config=Config(), app_state=app_state)
        resp = app.test_client().get("/health")

        assert resp.status_code == HTTPStatus.OK
        assert resp.get_json() == {"status": "discovering"}

    def test_returns_error_when_failed(self) -> None:
        app_state = AppState()
        app_state.set_phase(InitPhase.ERROR)

        app = create_app(config=Config(), app_state=app_state)
        resp = app.test_client().get("/health")

        assert resp.status_code == HTTPStatus.OK
        assert resp.get_json() == {"status": "error"}


class TestDiscoverJson:
    """Tests for GET `/discover.json`."""

    def test_returns_json_content_type(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/discover.json")

        assert resp.status_code == HTTPStatus.OK
        assert "application/json" in resp.content_type

    def test_returns_all_fields(self, flask_client: FlaskClient) -> None:
        """`discover.json` should return all expected fields."""
        resp = flask_client.get("/discover.json")

        assert resp.status_code == HTTPStatus.OK

        data = resp.get_json()
        assert set(data.keys()) == {
            "FriendlyName",
            "Manufacturer",
            "ModelNumber",
            "FirmwareVersion",
            "DeviceID",
            "DeviceAuth",
            "BaseURL",
            "LineupURL",
            "TunerCount",
        }

    def test_base_url_from_request_host(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/discover.json")

        data = resp.get_json()
        assert data["BaseURL"] == "http://localhost"
        assert data["LineupURL"] == "http://localhost/lineup.json"


class TestDeviceXml:
    """Tests for GET `/device.xml`."""

    def test_returns_xml_content_type(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/device.xml")

        assert resp.status_code == HTTPStatus.OK
        assert "application/xml" in resp.content_type

    def test_contains_all_fields(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/device.xml")

        body = resp.data.decode()

        assert "<FriendlyName>" in body
        assert "<DeviceID>" in body
        assert "<BaseURL>" in body
        assert "<LineupURL>" in body
        assert "<TunerCount>" in body

    def test_contains_device_info(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/device.xml")

        body = resp.data.decode()

        assert "<FriendlyName>Test Tablo</FriendlyName>" in body
        assert "<DeviceID>SID_TEST123</DeviceID>" in body


class TestLineupM3u:
    """Tests for GET `/lineup.m3u`."""

    def test_returns_m3u_content_type(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = []

        resp = flask_client.get("/lineup.m3u")

        assert resp.status_code == HTTPStatus.OK
        assert "application/x-mpegurl" in resp.content_type

    def test_empty_playlist_when_no_channels(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = []

        resp = flask_client.get("/lineup.m3u")

        assert resp.data.decode() == "#EXTM3U\n"

    def test_playlist_contains_channel_entries(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        resp = flask_client.get("/lineup.m3u")

        body = resp.data.decode()

        assert "#EXTM3U" in body
        assert 'tvg-id="7.1"' in body
        assert 'tvg-name="WABC"' in body
        assert "/watch/100" in body


class TestLineupM3u8:
    """Tests for GET `/lineup.m3u8`."""

    def test_returns_same_content_as_m3u(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        m3u_resp = flask_client.get("/lineup.m3u")
        m3u8_resp = flask_client.get("/lineup.m3u8")

        assert m3u8_resp.status_code == HTTPStatus.OK
        assert m3u8_resp.data == m3u_resp.data


class TestLineupXml:
    """Tests for GET `/lineup.xml`."""

    def test_returns_xml_content_type(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = []

        resp = flask_client.get("/lineup.xml")

        assert resp.status_code == HTTPStatus.OK
        assert "application/xml" in resp.content_type

    def test_empty_lineup(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = []

        resp = flask_client.get("/lineup.xml")

        body = resp.data.decode()

        assert "<Lineup" in body

    def test_contains_channel_entries(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        resp = flask_client.get("/lineup.xml")

        body = resp.data.decode()

        assert "<GuideNumber>7.1</GuideNumber>" in body
        assert "<GuideName>WABC</GuideName>" in body
        assert "/watch/100</URL>" in body


class TestLineupJson:
    """Tests for GET `/lineup.json`."""

    def test_returns_json_array(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        resp = flask_client.get("/lineup.json")

        assert resp.status_code == HTTPStatus.OK

        data = resp.get_json()

        assert isinstance(data, list)
        assert len(data) == 1

    def test_entry_has_required_fields(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        resp = flask_client.get("/lineup.json")

        entry = resp.get_json()[0]

        assert entry["GuideNumber"] == "7.1"
        assert entry["GuideName"] == "WABC"
        assert entry["URL"].endswith("/watch/100")

    def test_empty_array_when_no_channels(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = []

        resp = flask_client.get("/lineup.json")

        assert resp.get_json() == []


class TestXmltvXml:
    """Tests for GET `/xmltv.xml`."""

    def test_returns_xml_content_type(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = []
        tablo_client_mock.get_airings.return_value = []

        resp = flask_client.get("/xmltv.xml")

        assert resp.status_code == HTTPStatus.OK
        assert "application/xml" in resp.content_type

    def test_contains_xml_declaration(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = []
        tablo_client_mock.get_airings.return_value = []

        resp = flask_client.get("/xmltv.xml")

        body = resp.data.decode()

        assert body.startswith("<?xml version='1.0' encoding='utf-8'?>")

    def test_contains_channel_element(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]
        tablo_client_mock.get_airings.return_value = []

        resp = flask_client.get("/xmltv.xml")

        body = resp.data.decode()

        assert '<channel id="7.1">' in body
        assert "<display-name>WABC</display-name>" in body

    def test_contains_programme_element(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        channel = make_channel(100, "WABC", 7, 1)
        tablo_client_mock.get_channels.return_value = [channel]
        tablo_client_mock.get_airings.return_value = [
            make_episode_airing(500, "Test Show", channel),
        ]

        resp = flask_client.get("/xmltv.xml")

        body = resp.data.decode()

        assert "<programme" in body
        assert "<title>Test Show</title>" in body

    def test_returns_404_when_epg_disabled(
        self, server_info: ServerInfo, tablo_client_mock: MagicMock
    ) -> None:
        app_state = AppState()
        app_state.tablo_client = tablo_client_mock
        app_state.device_status.server_info = server_info
        app_state.enable_epg = False
        app_state.set_phase(InitPhase.READY)

        app = create_app(config=Config(), app_state=app_state)

        resp = app.test_client().get("/xmltv.xml")

        assert resp.status_code == HTTPStatus.NOT_FOUND


class TestLineupStatus:
    """Tests for GET `/lineup_status.json`."""

    def test_returns_scan_complete(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/lineup_status.json")

        assert resp.status_code == HTTPStatus.OK

        data = resp.get_json()

        assert data["ScanInProgress"] == 0
        assert data["ScanPossible"] == 1
        assert data["Source"] == "Antenna"


class TestWatch:
    """Tests for GET `/watch/<channel_id>`."""

    WATCH_URL = f"http://{TABLO_IP}:18080/pvr/100/pl.m3u8"

    def test_redirects_to_playlist_url(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_watch_url.return_value = self.WATCH_URL

        resp = flask_client.get("/watch/100")

        assert resp.status_code == HTTPStatus.FOUND
        assert resp.headers["Location"] == self.WATCH_URL

    def test_calls_get_watch_url_with_channel_path(
        self, flask_client: FlaskClient, tablo_client_mock: MagicMock
    ) -> None:
        tablo_client_mock.get_watch_url.return_value = self.WATCH_URL

        flask_client.get("/watch/12345")

        tablo_client_mock.get_watch_url.assert_called_once_with("/guide/channels/12345")

    def test_refreshes_tuners_after_watch(
        self,
        flask_client: FlaskClient,
        tablo_client_mock: MagicMock,
        app_state: AppState,
    ) -> None:
        tablo_client_mock.get_watch_url.return_value = self.WATCH_URL
        tablo_client_mock.refresh_tuners.return_value = []

        flask_client.get("/watch/100")
        app_state.drain_tuner_refresh()

        tablo_client_mock.refresh_tuners.assert_called_once()

    def test_updates_device_status_tuners_after_watch(
        self,
        flask_client: FlaskClient,
        tablo_client_mock: MagicMock,
        app_state: AppState,
    ) -> None:
        new_tuners = [
            {
                "in_use": True,
                "channel": "/guide/channels/100",
                "recording": None,
                "channel_identifier": "7.1",
            }
        ]
        tablo_client_mock.get_watch_url.return_value = self.WATCH_URL
        tablo_client_mock.refresh_tuners.return_value = new_tuners

        flask_client.get("/watch/100")
        app_state.drain_tuner_refresh()

        assert app_state.device_status.tuners == new_tuners

    def test_still_redirects_when_tuner_refresh_fails(
        self,
        flask_client: FlaskClient,
        tablo_client_mock: MagicMock,
        app_state: AppState,
    ) -> None:
        tablo_client_mock.get_watch_url.return_value = self.WATCH_URL
        tablo_client_mock.refresh_tuners.side_effect = ConnectionError(
            "Tablo unreachable"
        )

        resp = flask_client.get("/watch/100")
        app_state.drain_tuner_refresh()

        assert resp.status_code == HTTPStatus.FOUND
        assert resp.headers["Location"] == self.WATCH_URL


class TestRequireReady:
    """Routes behind `_require_ready()` return 503 when not yet initialized."""

    @pytest.fixture
    def not_ready_client(self) -> FlaskClient:
        app_state = AppState()
        app = create_app(config=Config(), app_state=app_state)
        return app.test_client()

    def test_discover_json_returns_503(self, not_ready_client: FlaskClient) -> None:
        resp = not_ready_client.get("/discover.json")
        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    def test_device_xml_returns_503(self, not_ready_client: FlaskClient) -> None:
        resp = not_ready_client.get("/device.xml")
        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    def test_lineup_m3u_returns_503(self, not_ready_client: FlaskClient) -> None:
        resp = not_ready_client.get("/lineup.m3u")
        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    def test_lineup_json_returns_503(self, not_ready_client: FlaskClient) -> None:
        resp = not_ready_client.get("/lineup.json")
        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    def test_lineup_xml_returns_503(self, not_ready_client: FlaskClient) -> None:
        resp = not_ready_client.get("/lineup.xml")
        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    def test_xmltv_xml_returns_503(self, not_ready_client: FlaskClient) -> None:
        resp = not_ready_client.get("/xmltv.xml")
        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    def test_watch_returns_503(self, not_ready_client: FlaskClient) -> None:
        resp = not_ready_client.get("/watch/100")
        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE


class TestRequireClient:
    """Routes behind `_require_client()` return 503 when tablo_client is None."""

    @pytest.fixture
    def client_no_tablo(self) -> FlaskClient:
        app_state = AppState()
        app_state.set_phase(InitPhase.READY)  # ready but no tablo_client
        app = create_app(config=Config(), app_state=app_state)
        return app.test_client()

    def test_lineup_m3u_returns_503(self, client_no_tablo: FlaskClient) -> None:
        resp = client_no_tablo.get("/lineup.m3u")
        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    def test_lineup_json_returns_503(self, client_no_tablo: FlaskClient) -> None:
        resp = client_no_tablo.get("/lineup.json")
        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    def test_watch_returns_503(self, client_no_tablo: FlaskClient) -> None:
        resp = client_no_tablo.get("/watch/100")
        assert resp.status_code == HTTPStatus.SERVICE_UNAVAILABLE
