"""Tests for the Tablo API client."""

import json

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


class TestGetChannels:
    """Tests for TabloClient.get_channels()."""

    @responses.activate
    def test_returns_empty_list_when_no_channels(self, tablo: TabloClient) -> None:
        responses.add(responses.GET, f"{BASE_URL}/guide/channels", json=[])

        result = tablo.get_channels()

        assert result == []

    @responses.activate
    def test_returns_hydrated_channels(self, tablo: TabloClient) -> None:
        channel_paths = ["/guide/channels/100", "/guide/channels/200"]
        batch_response = {
            "/guide/channels/100": {
                "object_id": 100,
                "path": "/guide/channels/100",
                "channel": {
                    "call_sign": "WABC",
                    "name": "WABC",
                    "call_sign_src": "tms",
                    "major": 7,
                    "minor": 1,
                    "network": "ABC",
                    "flags": [],
                    "resolution": "hd_1080",
                    "favourite": False,
                    "tms_station_id": "12345",
                    "tms_affiliate_id": "67890",
                    "channel_identifier": "abc",
                    "source": "antenna",
                    "logos": [],
                },
            },
            "/guide/channels/200": {
                "object_id": 200,
                "path": "/guide/channels/200",
                "channel": {
                    "call_sign": "WCBS",
                    "name": "WCBS",
                    "call_sign_src": "tms",
                    "major": 2,
                    "minor": 1,
                    "network": "CBS",
                    "flags": [],
                    "resolution": "hd_1080",
                    "favourite": True,
                    "tms_station_id": "54321",
                    "tms_affiliate_id": "09876",
                    "channel_identifier": "cbs",
                    "source": "antenna",
                    "logos": [],
                },
            },
        }

        batch_length = len(batch_response.keys())

        responses.add(responses.GET, f"{BASE_URL}/guide/channels", json=channel_paths)
        responses.add(responses.POST, f"{BASE_URL}/batch", json=batch_response)

        result = tablo.get_channels()

        assert len(result) == batch_length
        assert result[0]["channel"]["call_sign"] in {"WABC", "WCBS"}

    @responses.activate
    def test_batch_receives_channel_paths(self, tablo: TabloClient) -> None:
        channel_paths = ["/guide/channels/100"]
        responses.add(responses.GET, f"{BASE_URL}/guide/channels", json=channel_paths)
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={
                "/guide/channels/100": {
                    "object_id": 100,
                    "path": "/guide/channels/100",
                    "channel": {
                        "call_sign": "WABC",
                        "name": "WABC",
                        "call_sign_src": "tms",
                        "major": 7,
                        "minor": 1,
                        "network": "ABC",
                        "flags": [],
                        "resolution": "hd_1080",
                        "favourite": False,
                        "tms_station_id": "12345",
                        "tms_affiliate_id": "67890",
                        "channel_identifier": "abc",
                        "source": "antenna",
                        "logos": [],
                    },
                },
            },
        )

        tablo.get_channels()

        assert responses.calls[1].request.body is not None

        posted = json.loads(responses.calls[1].request.body)
        assert posted == ["/guide/channels/100"]


class TestGetWatchUrl:
    """Tests for TabloClient.get_watch_url()."""

    @responses.activate
    def test_returns_playlist_url(self, tablo: TabloClient) -> None:
        responses.add(
            responses.POST,
            f"{BASE_URL}/guide/channels/100/watch",
            json={
                "token": "abc-token-123",
                "expires": "2026-03-25T12:00:00Z",
                "keepalive": 60,
                "playlist_url": f"http://{TABLO_IP}:18080/pvr/100/pl.m3u8",
                "bif_url_sd": None,
                "bif_url_hd": None,
                "canRecord": True,
            },
        )

        url = tablo.get_watch_url("/guide/channels/100")

        assert url == f"http://{TABLO_IP}:18080/pvr/100/pl.m3u8"

    @responses.activate
    def test_raises_on_http_error(self, tablo: TabloClient) -> None:
        responses.add(
            responses.POST,
            f"{BASE_URL}/guide/channels/999/watch",
            status=404,
        )

        with pytest.raises(requests.HTTPError):
            tablo.get_watch_url("/guide/channels/999")
