"""Tests for the Tablo API client."""

from http import HTTPStatus

import pytest
import requests
import responses

from tablo_legacy_m3u.tablo_client import (
    TABLO_DISCOVERY_URL,
    TabloClient,
    discover_tablo_ip,
)

TABLO_IP = "192.168.1.100"
BASE_URL = f"http://{TABLO_IP}:8885"


@pytest.fixture
def tablo() -> TabloClient:
    """TabloClient pointed at a fake IP."""
    return TabloClient(TABLO_IP)


class TestDiscoverTabloIp:
    """Tests for the discover_tablo_ip() standalone function."""

    def test_returns_manual_ip_when_autodiscover_off(self) -> None:
        ip = discover_tablo_ip(autodiscover=False, tablo_ip="10.0.0.123")

        assert ip == "10.0.0.123"

    @responses.activate
    def test_discovers_ip_from_cloud(self) -> None:
        responses.add(
            responses.GET,
            TABLO_DISCOVERY_URL,
            json={"cpes": [{"private_ip": "192.168.1.200"}]},
        )

        ip = discover_tablo_ip(autodiscover=True, tablo_ip="")

        assert ip == "192.168.1.200"

    @responses.activate
    def test_raises_when_no_devices_found(self) -> None:
        responses.add(
            responses.GET,
            TABLO_DISCOVERY_URL,
            json={"cpes": []},
        )

        with pytest.raises(RuntimeError, match="No Tablo devices found"):
            discover_tablo_ip(autodiscover=True, tablo_ip="")

    @responses.activate
    def test_raises_on_http_error(self) -> None:
        responses.add(
            responses.GET,
            TABLO_DISCOVERY_URL,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        with pytest.raises(requests.HTTPError):
            discover_tablo_ip(autodiscover=True, tablo_ip="")
