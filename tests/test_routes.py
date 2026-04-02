"""Tests for the Flask application routes."""

from http import HTTPStatus
from unittest.mock import MagicMock

from flask.testing import FlaskClient

from tablo_legacy_m3u import create_app
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
        self, server_info: ServerInfo, tablo_client: MagicMock
    ) -> None:
        app = create_app(
            config=Config(),
            tablo_client=tablo_client,
            server_info=server_info,
            enable_epg=False,
        )

        resp = app.test_client().get("/")

        body = resp.data.decode()

        assert "EPG Disabled" in body

    def test_shows_epg_link_when_enabled(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/")

        body = resp.data.decode()

        assert "/xmltv.xml" in body


class TestFavicon:
    """Tests for GET `/favicon.ico`."""

    def test_returns_icon(self, flask_client: FlaskClient) -> None:
        resp = flask_client.get("/favicon.ico")

        assert resp.status_code == HTTPStatus.OK
        assert "image/" in resp.content_type
        assert len(resp.data) > 0


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
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = []

        resp = flask_client.get("/lineup.m3u")

        assert resp.status_code == HTTPStatus.OK
        assert "application/x-mpegurl" in resp.content_type

    def test_empty_playlist_when_no_channels(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = []

        resp = flask_client.get("/lineup.m3u")

        assert resp.data.decode() == "#EXTM3U\n"

    def test_playlist_contains_channel_entries(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = [
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
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        m3u_resp = flask_client.get("/lineup.m3u")
        m3u8_resp = flask_client.get("/lineup.m3u8")

        assert m3u8_resp.status_code == HTTPStatus.OK
        assert m3u8_resp.data == m3u_resp.data


class TestLineupXml:
    """Tests for GET `/lineup.xml`."""

    def test_returns_xml_content_type(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = []

        resp = flask_client.get("/lineup.xml")

        assert resp.status_code == HTTPStatus.OK
        assert "application/xml" in resp.content_type

    def test_empty_lineup(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = []

        resp = flask_client.get("/lineup.xml")

        body = resp.data.decode()

        assert "<Lineup" in body

    def test_contains_channel_entries(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = [
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
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        resp = flask_client.get("/lineup.json")

        assert resp.status_code == HTTPStatus.OK

        data = resp.get_json()

        assert isinstance(data, list)
        assert len(data) == 1

    def test_entry_has_required_fields(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]

        resp = flask_client.get("/lineup.json")

        entry = resp.get_json()[0]

        assert entry["GuideNumber"] == "7.1"
        assert entry["GuideName"] == "WABC"
        assert entry["URL"].endswith("/watch/100")

    def test_empty_array_when_no_channels(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = []

        resp = flask_client.get("/lineup.json")

        assert resp.get_json() == []


class TestXmltvXml:
    """Tests for GET `/xmltv.xml`."""

    def test_returns_xml_content_type(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = []
        tablo_client.get_airings.return_value = []

        resp = flask_client.get("/xmltv.xml")

        assert resp.status_code == HTTPStatus.OK
        assert "application/xml" in resp.content_type

    def test_contains_xml_declaration(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = []
        tablo_client.get_airings.return_value = []

        resp = flask_client.get("/xmltv.xml")

        body = resp.data.decode()

        assert body.startswith("<?xml version='1.0' encoding='utf-8'?>")

    def test_contains_channel_element(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_channels.return_value = [
            make_channel(100, "WABC", 7, 1),
        ]
        tablo_client.get_airings.return_value = []

        resp = flask_client.get("/xmltv.xml")

        body = resp.data.decode()

        assert '<channel id="7.1">' in body
        assert "<display-name>WABC</display-name>" in body

    def test_contains_programme_element(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        channel = make_channel(100, "WABC", 7, 1)
        tablo_client.get_channels.return_value = [channel]
        tablo_client.get_airings.return_value = [
            make_episode_airing(500, "Test Show", channel),
        ]

        resp = flask_client.get("/xmltv.xml")

        body = resp.data.decode()

        assert "<programme" in body
        assert "<title>Test Show</title>" in body

    def test_returns_404_when_epg_disabled(
        self, server_info: ServerInfo, tablo_client: MagicMock
    ) -> None:
        app = create_app(
            config=Config(),
            tablo_client=tablo_client,
            server_info=server_info,
            enable_epg=False,
        )

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

    def test_redirects_to_playlist_url(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_watch_url.return_value = (
            f"http://{TABLO_IP}:18080/pvr/100/pl.m3u8"
        )

        resp = flask_client.get("/watch/100")

        assert resp.status_code == HTTPStatus.FOUND
        assert resp.headers["Location"] == f"http://{TABLO_IP}:18080/pvr/100/pl.m3u8"

    def test_calls_get_watch_url_with_channel_path(
        self, flask_client: FlaskClient, tablo_client: MagicMock
    ) -> None:
        tablo_client.get_watch_url.return_value = "http://example.com/stream.m3u8"

        flask_client.get("/watch/12345")

        tablo_client.get_watch_url.assert_called_once_with("/guide/channels/12345")
