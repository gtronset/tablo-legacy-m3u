"""Tests for the Tablo API client."""

import json

from http import HTTPStatus

import pytest
import requests
import responses

from tablo_legacy_m3u.tablo_client import (
    BATCH_SIZE,
    TABLO_DISCOVERY_URL,
    TabloClient,
    discover_tablo_ip,
)
from tablo_legacy_m3u.tablo_types import ServerInfo
from tests.helpers import make_channel, make_episode_airing

TABLO_IP = "192.168.1.100"
BASE_URL = f"http://{TABLO_IP}:8885"


class TestDiscoverTabloIp:
    """Tests for the `discover_tablo_ip()` standalone function."""

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
    """Tests for `TabloClient.get_server_info()`."""

    @responses.activate
    def test_returns_server_info(
        self, tablo_client: TabloClient, server_info: ServerInfo
    ) -> None:
        expected = server_info

        responses.add(responses.GET, f"{BASE_URL}/server/info", json=expected)

        result = tablo_client.get_server_info()

        assert result == expected

    @responses.activate
    def test_raises_on_http_error(self, tablo_client: TabloClient) -> None:
        responses.add(
            responses.GET,
            f"{BASE_URL}/server/info",
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

        with pytest.raises(requests.HTTPError):
            tablo_client.get_server_info()


class TestGetTuners:
    """Tests for `TabloClient.get_tuners()`."""

    @responses.activate
    def test_returns_tuner_list(self, tablo_client: TabloClient) -> None:
        tuners_list = [
            {
                "in_use": False,
                "channel": None,
                "recording": None,
                "channel_identifier": None,
            },
            {
                "in_use": True,
                "channel": "/guide/channels/100",
                "recording": None,
                "channel_identifier": "7.1",
            },
        ]

        responses.add(
            responses.GET,
            f"{BASE_URL}/server/tuners",
            json=tuners_list,
        )
        result = tablo_client.get_tuners()

        assert len(result) == len(tuners_list)
        assert result[1]["in_use"] is True

    @responses.activate
    def test_raises_on_http_error(self, tablo_client: TabloClient) -> None:
        responses.add(responses.GET, f"{BASE_URL}/server/tuners", status=500)
        with pytest.raises(requests.HTTPError):
            tablo_client.get_tuners()


class TestGetHarddrives:
    """Tests for `TabloClient.get_harddrives()`."""

    @responses.activate
    def test_returns_harddrive_list(self, tablo_client: TabloClient) -> None:
        harddrives_list = [
            {
                "name": "Seagate 1TB",
                "connected": True,
                "format_state": "authorized",
                "busy_state": "ready",
                "kind": "external",
                "size": 984373075968,
                "usage": 102127366144,
                "free": 882245709824,
                "error": None,
            }
        ]
        responses.add(
            responses.GET,
            f"{BASE_URL}/server/harddrives",
            json=harddrives_list,
        )
        result = tablo_client.get_harddrives()

        assert len(result) == len(harddrives_list)
        assert result[0]["connected"] is True

    @responses.activate
    def test_raises_on_http_error(self, tablo_client: TabloClient) -> None:
        responses.add(responses.GET, f"{BASE_URL}/server/harddrives", status=500)
        with pytest.raises(requests.HTTPError):
            tablo_client.get_harddrives()


class TestGetGuideStatus:
    """Tests for `TabloClient.get_guide_status()`."""

    @responses.activate
    def test_returns_guide_status(self, tablo_client: TabloClient) -> None:
        responses.add(
            responses.GET,
            f"{BASE_URL}/server/guide/status",
            json={
                "guide_seeded": True,
                "last_update": "2026-04-03T10:56:50Z",
                "limit": "2026-04-17T04:30Z",
                "download_progress": None,
            },
        )
        result = tablo_client.get_guide_status()
        assert result["guide_seeded"] is True

    @responses.activate
    def test_raises_on_http_error(self, tablo_client: TabloClient) -> None:
        responses.add(responses.GET, f"{BASE_URL}/server/guide/status", status=500)
        with pytest.raises(requests.HTTPError):
            tablo_client.get_guide_status()


class TestHasGuideSubscription:
    """Tests for `TabloClient.has_guide_subscription()`."""

    @responses.activate
    def test_true_when_guide_active(self, tablo_client: TabloClient) -> None:
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

        assert tablo_client.has_guide_subscription() is True

    @responses.activate
    def test_false_when_guide_expired(self, tablo_client: TabloClient) -> None:
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

        assert tablo_client.has_guide_subscription() is False

    @responses.activate
    def test_false_when_no_subscriptions(self, tablo_client: TabloClient) -> None:
        responses.add(
            responses.GET,
            f"{BASE_URL}/account/subscription",
            json={"state": "none", "trial": None, "subscriptions": []},
        )

        assert tablo_client.has_guide_subscription() is False


class TestGetChannels:
    """Tests for `TabloClient.get_channels()`."""

    @responses.activate
    def test_returns_empty_list_when_no_channels(
        self, tablo_client: TabloClient
    ) -> None:
        responses.add(responses.GET, f"{BASE_URL}/guide/channels", json=[])

        result = tablo_client.get_channels()

        assert result == []

    @responses.activate
    def test_returns_hydrated_channels(self, tablo_client: TabloClient) -> None:
        channel_paths = ["/guide/channels/100", "/guide/channels/200"]
        batch_response = {
            "/guide/channels/100": make_channel(100, "WABC", 7, 1),
            "/guide/channels/200": make_channel(200, "WCBS", 2, 1, network="CBS"),
        }

        batch_length = len(batch_response.keys())

        responses.add(responses.GET, f"{BASE_URL}/guide/channels", json=channel_paths)
        responses.add(responses.POST, f"{BASE_URL}/batch", json=batch_response)

        result = tablo_client.get_channels()

        assert len(result) == batch_length
        assert result[0]["channel"]["call_sign"] in {"WABC", "WCBS"}

    @responses.activate
    def test_batch_receives_channel_paths(self, tablo_client: TabloClient) -> None:
        channel_paths = ["/guide/channels/100"]
        responses.add(responses.GET, f"{BASE_URL}/guide/channels", json=channel_paths)
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={
                "/guide/channels/100": make_channel(100, "WABC", 7, 1),
            },
        )

        tablo_client.get_channels()

        assert responses.calls[1].request.body is not None

        posted = json.loads(responses.calls[1].request.body)
        assert posted == ["/guide/channels/100"]


class TestGetAirings:
    """Tests for `TabloClient.get_airings()`."""

    @responses.activate
    def test_returns_empty_list_when_no_airings(
        self, tablo_client: TabloClient
    ) -> None:
        responses.add(responses.GET, f"{BASE_URL}/guide/airings", json=[])

        result = tablo_client.get_airings()

        assert result == []

    @responses.activate
    def test_returns_hydrated_airings(self, tablo_client: TabloClient) -> None:
        airing_paths = [
            "/guide/series/episodes/500",
            "/guide/series/episodes/501",
        ]
        batch_response = {
            "/guide/series/episodes/500": make_episode_airing(500, "Show A"),
            "/guide/series/episodes/501": make_episode_airing(501, "Show B"),
        }

        batch_length = len(batch_response.keys())

        responses.add(responses.GET, f"{BASE_URL}/guide/airings", json=airing_paths)
        responses.add(responses.POST, f"{BASE_URL}/batch", json=batch_response)

        result = tablo_client.get_airings()

        assert len(result) == batch_length

    @responses.activate
    def test_filters_none_from_batch(self, tablo_client: TabloClient) -> None:
        airing_paths = [
            "/guide/series/episodes/500",
            "/guide/series/episodes/999",
        ]
        batch_response = {
            "/guide/series/episodes/500": make_episode_airing(500),
            "/guide/series/episodes/999": None,
        }

        responses.add(responses.GET, f"{BASE_URL}/guide/airings", json=airing_paths)
        responses.add(responses.POST, f"{BASE_URL}/batch", json=batch_response)

        result = tablo_client.get_airings()

        assert len(result) == 1

    @responses.activate
    def test_batch_receives_airing_paths(self, tablo_client: TabloClient) -> None:
        airing_paths = ["/guide/series/episodes/500"]
        responses.add(responses.GET, f"{BASE_URL}/guide/airings", json=airing_paths)
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/series/episodes/500": make_episode_airing(500)},
        )

        tablo_client.get_airings()

        assert responses.calls[1].request.body is not None

        posted = json.loads(responses.calls[1].request.body)
        assert posted == ["/guide/series/episodes/500"]

    @responses.activate
    def test_chunked_batch_splits_large_lists(self, tablo_client: TabloClient) -> None:
        path_count = 75

        paths = [f"/guide/series/episodes/{i}" for i in range(path_count)]
        batch_response_1 = {
            p: make_episode_airing(i) for i, p in enumerate(paths[:BATCH_SIZE])
        }
        batch_response_2 = {
            p: make_episode_airing(i)
            for i, p in enumerate(paths[BATCH_SIZE:], start=BATCH_SIZE)
        }

        responses.add(responses.GET, f"{BASE_URL}/guide/airings", json=paths)
        responses.add(responses.POST, f"{BASE_URL}/batch", json=batch_response_1)
        responses.add(responses.POST, f"{BASE_URL}/batch", json=batch_response_2)

        result = tablo_client.get_airings()

        assert len(result) == path_count

        batch_calls = [c for c in responses.calls if c.request.method == "POST"]
        assert len(batch_calls) == 2  # noqa: PLR2004, Value here is more readable raw.

        assert batch_calls[0].request.body is not None
        assert batch_calls[1].request.body is not None

        # Execution order of batches is not guaranteed; check sizes as a set
        batch_sizes = {
            len(json.loads(batch_calls[0].request.body)),
            len(json.loads(batch_calls[1].request.body)),
        }
        assert batch_sizes == {BATCH_SIZE, path_count - BATCH_SIZE}


class TestGetWatchUrl:
    """Tests for `TabloClient.get_watch_url()`."""

    @responses.activate
    def test_returns_playlist_url(self, tablo_client: TabloClient) -> None:
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

        url = tablo_client.get_watch_url("/guide/channels/100")

        assert url == f"http://{TABLO_IP}:18080/pvr/100/pl.m3u8"

    @responses.activate
    def test_raises_on_http_error(self, tablo_client: TabloClient) -> None:
        responses.add(
            responses.POST,
            f"{BASE_URL}/guide/channels/999/watch",
            status=404,
        )

        with pytest.raises(requests.HTTPError):
            tablo_client.get_watch_url("/guide/channels/999")
