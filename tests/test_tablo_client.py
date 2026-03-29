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
from tests.helpers import make_channel, make_episode_airing

TABLO_IP = "192.168.1.100"
BASE_URL = f"http://{TABLO_IP}:8885"


@pytest.fixture
def tablo() -> TabloClient:
    """TabloClient pointed at a fake IP."""
    return TabloClient(TABLO_IP)


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
    """Tests for `TabloClient.has_guide_subscription()`."""

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
    """Tests for `TabloClient.get_channels()`."""

    @responses.activate
    def test_returns_empty_list_when_no_channels(self, tablo: TabloClient) -> None:
        responses.add(responses.GET, f"{BASE_URL}/guide/channels", json=[])

        result = tablo.get_channels()

        assert result == []

    @responses.activate
    def test_returns_hydrated_channels(self, tablo: TabloClient) -> None:
        channel_paths = ["/guide/channels/100", "/guide/channels/200"]
        batch_response = {
            "/guide/channels/100": make_channel(100, "WABC", 7, 1),
            "/guide/channels/200": make_channel(200, "WCBS", 2, 1, network="CBS"),
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
                "/guide/channels/100": make_channel(100, "WABC", 7, 1),
            },
        )

        tablo.get_channels()

        assert responses.calls[1].request.body is not None

        posted = json.loads(responses.calls[1].request.body)
        assert posted == ["/guide/channels/100"]


class TestGetAirings:
    """Tests for `TabloClient.get_airings()`."""

    @responses.activate
    def test_returns_empty_list_when_no_airings(self, tablo: TabloClient) -> None:
        responses.add(responses.GET, f"{BASE_URL}/guide/airings", json=[])

        result = tablo.get_airings()

        assert result == []

    @responses.activate
    def test_returns_hydrated_airings(self, tablo: TabloClient) -> None:
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

        result = tablo.get_airings()

        assert len(result) == batch_length

    @responses.activate
    def test_filters_none_from_batch(self, tablo: TabloClient) -> None:
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

        result = tablo.get_airings()

        assert len(result) == 1

    @responses.activate
    def test_batch_receives_airing_paths(self, tablo: TabloClient) -> None:
        airing_paths = ["/guide/series/episodes/500"]
        responses.add(responses.GET, f"{BASE_URL}/guide/airings", json=airing_paths)
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/series/episodes/500": make_episode_airing(500)},
        )

        tablo.get_airings()

        assert responses.calls[1].request.body is not None

        posted = json.loads(responses.calls[1].request.body)
        assert posted == ["/guide/series/episodes/500"]

    @responses.activate
    def test_chunked_batch_splits_large_lists(self, tablo: TabloClient) -> None:
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

        result = tablo.get_airings()

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


class TestCaching:
    """Tests for TTL cache behavior on get_channels() and get_airings()."""

    @responses.activate
    def test_get_channels_cache_hit(self) -> None:
        """Second call returns cached result without hitting the API again."""
        tablo = TabloClient(TABLO_IP)

        responses.add(
            responses.GET, f"{BASE_URL}/guide/channels", json=["/guide/channels/100"]
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/channels/100": make_channel(100, "WABC", 7, 1)},
        )

        first = tablo.get_channels()
        second = tablo.get_channels()

        assert first == second
        assert len(responses.calls) == 2  # noqa: PLR2004, Value here is more readable raw.

    @responses.activate
    def test_get_channels_cache_expiry(self) -> None:
        """Expired cache triggers a fresh API call.

        Sets `cache_ttl=0` to force immediate expiry.
        """
        tablo = TabloClient(TABLO_IP, cache_ttl=0)

        channel = make_channel(100, "WABC", 7, 1)
        responses.add(
            responses.GET, f"{BASE_URL}/guide/channels", json=["/guide/channels/100"]
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/channels/100": channel},
        )
        responses.add(
            responses.GET, f"{BASE_URL}/guide/channels", json=["/guide/channels/100"]
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/channels/100": channel},
        )

        tablo.get_channels()
        tablo.get_channels()

        assert len(responses.calls) == 4  # noqa: PLR2004, Value here is more readable raw.

    @responses.activate
    def test_get_airings_cache_hit(self) -> None:
        """Second call returns cached airings without hitting the API again."""
        tablo = TabloClient(TABLO_IP)
        channel = make_channel(100, "WABC", 7, 1)
        airing = make_episode_airing(500, "Show A", channel=channel)

        responses.add(
            responses.GET,
            f"{BASE_URL}/guide/airings",
            json=["/guide/series/episodes/500"],
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/series/episodes/500": airing},
        )
        first = tablo.get_airings()
        second = tablo.get_airings()
        assert first == second
        assert len(responses.calls) == 2  # noqa: PLR2004, Value here is more readable raw.

    @responses.activate
    def test_get_airings_cache_expiry(self) -> None:
        """Expired cache for airings triggers a fresh API call.

        Sets `cache_ttl=0` to force immediate expiry.
        """
        tablo = TabloClient(TABLO_IP, cache_ttl=0)
        channel = make_channel(100, "WABC", 7, 1)
        airing = make_episode_airing(500, "Show A", channel=channel)
        responses.add(
            responses.GET,
            f"{BASE_URL}/guide/airings",
            json=["/guide/series/episodes/500"],
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/series/episodes/500": airing},
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/guide/airings",
            json=["/guide/series/episodes/500"],
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/series/episodes/500": airing},
        )
        tablo.get_airings()
        tablo.get_airings()
        assert len(responses.calls) == 4  # noqa: PLR2004, Value here is more readable raw.

    @responses.activate
    def test_channels_and_airings_caches_are_independent(self) -> None:
        """get_channels() and get_airings() don't share cached values."""
        tablo = TabloClient(TABLO_IP)

        channel = make_channel(100, "WABC", 7, 1)
        airing = make_episode_airing(500, "Show A", channel=channel)

        responses.add(
            responses.GET, f"{BASE_URL}/guide/channels", json=["/guide/channels/100"]
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/channels/100": channel},
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/guide/airings",
            json=["/guide/series/episodes/500"],
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/series/episodes/500": airing},
        )

        channels = tablo.get_channels()
        airings = tablo.get_airings()

        assert len(channels) == 1
        assert len(airings) == 1
        assert "channel" in channels[0]
        assert "airing_details" in airings[0]
