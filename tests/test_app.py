"""Tests for the Flask application routes."""

from http import HTTPStatus

import pytest

from flask.testing import FlaskClient

from tablo_legacy_m3u.app import app
from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.tablo_types import ServerInfo

TUNER_COUNT: int = 4


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
            "tuners": TUNER_COUNT,
            "type": "quad",
            "name": "TABLO_QUAD",
        },
        "availability": "available",
        "cache_key": "abc123",
        "product": "tablo",
    }


@pytest.fixture
def client(request: pytest.FixtureRequest, server_info: ServerInfo) -> FlaskClient:
    """Flask test client with configurable app config."""
    config = getattr(request, "param", Config())

    app.config["APP_CONFIG"] = config
    app.config["TABLO_SERVER_INFO"] = server_info

    return app.test_client()


class TestDiscoverJson:
    """Tests for GET /discover.json."""

    def test_returns_all_fields(self, client: FlaskClient) -> None:
        """discover.json should return all expected fields."""
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

    def test_friendly_name_defaults_to_server_name(self, client: FlaskClient) -> None:
        resp = client.get("/discover.json")

        data = resp.get_json()
        assert data["FriendlyName"] == "Test Tablo"

    @pytest.mark.parametrize(
        "client", [Config(device_name="My Custom Name")], indirect=True
    )
    def test_friendly_name_uses_device_name_from_config(
        self, client: FlaskClient
    ) -> None:
        resp = client.get("/discover.json")

        data = resp.get_json()
        assert data["FriendlyName"] == "My Custom Name"

    def test_device_fields_from_server_info(self, client: FlaskClient) -> None:
        resp = client.get("/discover.json")

        data = resp.get_json()

        assert data["Manufacturer"] == "Tablo"
        assert data["ModelNumber"] == "TABLO_QUAD"
        assert data["FirmwareVersion"] == "2.2.42"
        assert data["DeviceID"] == "SID_TEST123"
        assert data["TunerCount"] == TUNER_COUNT

        assert data["DeviceAuth"] == data["FriendlyName"]

    def test_base_url_from_request_host(self, client: FlaskClient) -> None:
        resp = client.get("/discover.json")

        data = resp.get_json()
        assert data["BaseURL"] == "http://localhost"
        assert data["LineupURL"] == "http://localhost/lineup.json"
