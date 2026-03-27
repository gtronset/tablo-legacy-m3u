"""Tests for the Flask application routes."""

from http import HTTPStatus
from unittest.mock import MagicMock

import pytest

from flask.testing import FlaskClient

from tablo_legacy_m3u import create_app
from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.tablo_types import ServerInfo
from tests.helpers import make_channel

TABLO_IP: str = "10.0.0.123"
TUNER_COUNT: int = 4


@pytest.fixture
def tablo_client() -> MagicMock:
    """Mock TabloClient for route tests."""
    return MagicMock()


@pytest.fixture
def client(
    request: pytest.FixtureRequest,
    server_info: ServerInfo,
    tablo_client: MagicMock,
) -> FlaskClient:
    """Flask test client with configurable app config."""
    config = getattr(request, "param", Config())

    app = create_app(
        config=config,
        tablo_client=tablo_client,
        server_info=server_info,
    )

    return app.test_client()


class TestDiscoverJson:
    """Tests for GET /discover.json."""

    def test_returns_json_content_type(self, client: FlaskClient) -> None:
        resp = client.get("/discover.json")

        assert resp.status_code == HTTPStatus.OK
        assert "application/json" in resp.content_type

    def test_returns_all_fields(self, client: FlaskClient) -> None:
        """`discover.json` should return all expected fields."""
        resp = client.get("/discover.json")

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

    def test_base_url_from_request_host(self, client: FlaskClient) -> None:
        resp = client.get("/discover.json")

        data = resp.get_json()
        assert data["BaseURL"] == "http://localhost"
        assert data["LineupURL"] == "http://localhost/lineup.json"


class TestDeviceXml:
    """Tests for GET /device.xml."""

    def test_returns_xml_content_type(self, client: FlaskClient) -> None:
        resp = client.get("/device.xml")

        assert resp.status_code == HTTPStatus.OK
        assert "application/xml" in resp.content_type

    def test_contains_all_fields(self, client: FlaskClient) -> None:
        resp = client.get("/device.xml")

        body = resp.data.decode()

        assert "<FriendlyName>" in body
        assert "<DeviceID>" in body
        assert "<BaseURL>" in body
        assert "<LineupURL>" in body
        assert "<TunerCount>" in body

    def test_contains_device_info(self, client: FlaskClient) -> None:
        resp = client.get("/device.xml")

        body = resp.data.decode()

        assert "<FriendlyName>Test Tablo</FriendlyName>" in body
        assert "<DeviceID>SID_TEST123</DeviceID>" in body


class TestLineupM3u:
    """Tests for GET `/lineup.m3u`."""

    def test_returns_m3u_content_type(
        self, client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = []

        resp = client.get("/lineup.m3u")

        assert resp.status_code == HTTPStatus.OK
        assert "application/x-mpegurl" in resp.content_type

    def test_empty_playlist_when_no_channels(
        self, client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = []

        resp = client.get("/lineup.m3u")

        assert resp.data.decode() == "#EXTM3U\n"

    def test_playlist_contains_channel_entries(
        self, client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        resp = client.get("/lineup.m3u")

        body = resp.data.decode()

        assert "#EXTM3U" in body
        assert 'tvg-name="WABC"' in body
        assert "/watch/100" in body


class TestLineupM3u8:
    """Tests for GET `/lineup.m3u8`."""

    def test_returns_same_content_as_m3u(
        self, client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        m3u_resp = client.get("/lineup.m3u")
        m3u8_resp = client.get("/lineup.m3u8")

        assert m3u8_resp.status_code == HTTPStatus.OK
        assert m3u8_resp.data == m3u_resp.data


class TestLineupXml:
    """Tests for GET `/lineup.xml`."""

    def test_returns_xml_content_type(
        self, client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = []

        resp = client.get("/lineup.xml")

        assert resp.status_code == HTTPStatus.OK
        assert "application/xml" in resp.content_type

    def test_empty_lineup(self, client: FlaskClient, tablo_client: MagicMock) -> None:
        tablo_client.get_channels.return_value = []

        resp = client.get("/lineup.xml")

        body = resp.data.decode()

        assert "<Lineup" in body

    def test_contains_channel_entries(
        self, client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        resp = client.get("/lineup.xml")

        body = resp.data.decode()

        assert "<GuideNumber>7.1</GuideNumber>" in body
        assert "<GuideName>WABC</GuideName>" in body
        assert "/watch/100</URL>" in body


class TestLineupJson:
    """Tests for GET `/lineup.json`."""

    def test_returns_json_array(
        self, client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        resp = client.get("/lineup.json")

        assert resp.status_code == HTTPStatus.OK

        data = resp.get_json()

        assert isinstance(data, list)
        assert len(data) == 1

    def test_entry_has_required_fields(
        self, client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        resp = client.get("/lineup.json")

        entry = resp.get_json()[0]

        assert entry["GuideNumber"] == "7.1"
        assert entry["GuideName"] == "WABC"
        assert entry["URL"].endswith("/watch/100")

    def test_empty_array_when_no_channels(
        self, client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = []

        resp = client.get("/lineup.json")

        assert resp.get_json() == []


class TestLineupStatus:
    """Tests for GET `/lineup_status.json`."""

    def test_returns_scan_complete(self, client: FlaskClient) -> None:
        resp = client.get("/lineup_status.json")

        assert resp.status_code == HTTPStatus.OK

        data = resp.get_json()

        assert data["ScanInProgress"] == 0
        assert data["ScanPossible"] == 1
        assert data["Source"] == "Antenna"


class TestWatch:
    """Tests for GET `/watch/<channel_id>`."""

    def test_redirects_to_playlist_url(
        self, client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_watch_url.return_value = (
            f"http://{TABLO_IP}:18080/pvr/100/pl.m3u8"
        )

        resp = client.get("/watch/100")

        assert resp.status_code == HTTPStatus.FOUND
        assert resp.headers["Location"] == f"http://{TABLO_IP}:18080/pvr/100/pl.m3u8"

    def test_calls_get_watch_url_with_channel_path(
        self, client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_watch_url.return_value = "http://example.com/stream.m3u8"

        client.get("/watch/12345")

        tablo_client.get_watch_url.assert_called_once_with("/guide/channels/12345")
