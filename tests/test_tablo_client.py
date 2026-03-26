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


class TestGetServerInfo:
    """Tests for TabloClient.get_server_info()."""

    @responses.activate
    def test_returns_server_info(self, tablo: TabloClient) -> None:
        expected = {
            "server_id": "SID_ABC123",
            "name": "My Tablo",
            "timezone": "America/New_York",
            "deprecated": "timezone",
            "version": "2.2.42",
            "local_address": TABLO_IP,
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
        responses.add(responses.GET, f"{BASE_URL}/server/info", json=expected)

        result = tablo.get_server_info()

        assert result == expected

    @responses.activate
    def test_raises_on_http_error(self, tablo: TabloClient) -> None:
        responses.add(
            responses.GET,
            f"{BASE_URL}/server/info",
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        with pytest.raises(requests.HTTPError):
            tablo.get_server_info()


class TestHasGuideSubscription:
    """Tests for TabloClient.has_guide_subscription()."""

    @responses.activate
    def test_true_when_guide_active(self, tablo: TabloClient) -> None:
        responses.add(
            responses.GET,
            f"{BASE_URL}/account/subscription",
            json={
                "state": "subscribed",
                "trial": None,
                "subscriptions": [
                    {
                        "kind": "guide",
                        "state": "active",
                        "name": "guide",
                        "title": "TV Guide Data",
                        "deprecated": "",
                        "expires": None,
                        "registration_url": "",
                        "registration_identifier": "",
                        "subtitle": "",
                        "description": "",
                        "actions": [],
                        "warnings": [],
                    },
                ],
            },
        )

        assert tablo.has_guide_subscription() is True

    @responses.activate
    def test_false_when_guide_expired(self, tablo: TabloClient) -> None:
        responses.add(
            responses.GET,
            f"{BASE_URL}/account/subscription",
            json={
                "state": "expired",
                "trial": None,
                "subscriptions": [
                    {
                        "kind": "guide",
                        "state": "expired",
                        "name": "guide",
                        "title": "TV Guide Data",
                        "deprecated": "",
                        "expires": "2024-01-01T00:00Z",
                        "registration_url": "",
                        "registration_identifier": "",
                        "subtitle": "",
                        "description": "",
                        "actions": [],
                        "warnings": [],
                    },
                ],
            },
        )

        assert tablo.has_guide_subscription() is False

    @responses.activate
    def test_false_when_no_subscriptions(self, tablo: TabloClient) -> None:
        responses.add(
            responses.GET,
            f"{BASE_URL}/account/subscription",
            json={"state": "none", "trial": None, "subscriptions": []},
        )

        assert tablo.has_guide_subscription() is False
