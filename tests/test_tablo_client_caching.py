"""Tests for TTL cache behavior in the Tablo API client."""

import json
import threading
import time

from typing import Any

import responses

from tablo_legacy_m3u.tablo_client import (
    TabloClient,
)
from tests.helpers import make_channel, make_episode_airing

TABLO_IP = "192.168.1.100"
BASE_URL = f"http://{TABLO_IP}:8885"


class TestCaching:
    """Tests for TTL cache behavior on get_channels() and get_airings()."""

    @responses.activate
    def test_get_channels_cache_hit(self, tablo_client: TabloClient) -> None:
        """Second call returns cached result without hitting the API again."""
        responses.add(
            responses.GET, f"{BASE_URL}/guide/channels", json=["/guide/channels/100"]
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/channels/100": make_channel(100, "WABC", 7, 1)},
        )

        first = tablo_client.get_channels()
        second = tablo_client.get_channels()

        assert first == second
        assert len(responses.calls) == 2  # noqa: PLR2004, Value here is more readable raw.

    @responses.activate
    def test_get_channels_uses_refreshed_cache(self, tablo_client: TabloClient) -> None:
        """`get_channels()` returns cached data populated by a prior refresh."""
        channel = make_channel(100, "WABC", 7, 1)
        responses.add(
            responses.GET, f"{BASE_URL}/guide/channels", json=["/guide/channels/100"]
        )
        responses.add(
            responses.POST, f"{BASE_URL}/batch", json={"/guide/channels/100": channel}
        )

        tablo_client.refresh_channels()
        result = tablo_client.get_channels()

        assert result[0]["channel"]["call_sign"] == "WABC"
        assert len(responses.calls) == 2  # noqa: PLR2004, get_channels() used cache

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
    def test_get_airings_cache_hit(self, tablo_client: TabloClient) -> None:
        """Second call returns cached airings without hitting the API again."""
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
        first = tablo_client.get_airings()
        second = tablo_client.get_airings()
        assert first == second
        assert len(responses.calls) == 2  # noqa: PLR2004, Value here is more readable raw.

    @responses.activate
    def test_get_airings_uses_refreshed_cache(self, tablo_client: TabloClient) -> None:
        """`get_airings()` returns cached data populated by a prior refresh."""
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

        tablo_client.refresh_airings()
        result = tablo_client.get_airings()

        assert result[0]["airing_details"]["show_title"] == "Show A"
        assert len(responses.calls) == 2  # noqa: PLR2004, get_airings() used cache

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
    def test_channels_and_airings_caches_are_independent(
        self, tablo_client: TabloClient
    ) -> None:
        """get_channels() and get_airings() don't share cached values."""
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

        channels = tablo_client.get_channels()
        airings = tablo_client.get_airings()

        assert len(channels) == 1
        assert len(airings) == 1
        assert "channel" in channels[0]
        assert "airing_details" in airings[0]

    @responses.activate
    def test_refresh_channels_clears_cache(self, tablo_client: TabloClient) -> None:
        """`refresh_channels()` bypasses cache and makes a fresh API call."""
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

        tablo_client.get_channels()
        tablo_client.refresh_channels()

        assert len(responses.calls) == 4  # noqa: PLR2004

    @responses.activate
    def test_refresh_channels_returns_fresh_data(
        self, tablo_client: TabloClient
    ) -> None:
        """`refresh_channels()` returns updated data, not stale cache."""
        old_channel = make_channel(100, "WABC", 7, 1)
        new_channel = make_channel(100, "WABC-HD", 7, 1)

        responses.add(
            responses.GET, f"{BASE_URL}/guide/channels", json=["/guide/channels/100"]
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/channels/100": old_channel},
        )
        responses.add(
            responses.GET, f"{BASE_URL}/guide/channels", json=["/guide/channels/100"]
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/channels/100": new_channel},
        )

        first = tablo_client.get_channels()
        refreshed = tablo_client.refresh_channels()

        assert first[0]["channel"]["call_sign"] == "WABC"
        assert refreshed[0]["channel"]["call_sign"] == "WABC-HD"

    @responses.activate
    def test_refresh_airings_clears_cache(self, tablo_client: TabloClient) -> None:
        """`refresh_airings()` bypasses cache and makes a fresh API call."""
        airing = make_episode_airing(500, "Show A")

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

        tablo_client.get_airings()
        tablo_client.refresh_airings()

        assert len(responses.calls) == 4  # noqa: PLR2004

    @responses.activate
    def test_refresh_airings_returns_fresh_data(
        self, tablo_client: TabloClient
    ) -> None:
        """`refresh_airings()` returns updated data, not stale cache."""
        old_airing = make_episode_airing(500, "Show A")
        new_airing = make_episode_airing(500, "Show A Updated")

        responses.add(
            responses.GET,
            f"{BASE_URL}/guide/airings",
            json=["/guide/series/episodes/500"],
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/series/episodes/500": old_airing},
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/guide/airings",
            json=["/guide/series/episodes/500"],
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/series/episodes/500": new_airing},
        )

        first = tablo_client.get_airings()
        refreshed = tablo_client.refresh_airings()

        assert first[0]["airing_details"]["show_title"] == "Show A"
        assert refreshed[0]["airing_details"]["show_title"] == "Show A Updated"

    @responses.activate
    def test_get_tuners_cache_hit(self, tablo_client: TabloClient) -> None:
        """Second call returns cached result without hitting the API again."""
        tuners = [
            {
                "in_use": False,
                "channel": None,
                "recording": None,
                "channel_identifier": None,
            }
        ]
        responses.add(responses.GET, f"{BASE_URL}/server/tuners", json=tuners)

        first = tablo_client.get_tuners()
        second = tablo_client.get_tuners()

        assert first == second
        assert len(responses.calls) == 1

    @responses.activate
    def test_get_tuners_uses_refreshed_cache(self, tablo_client: TabloClient) -> None:
        """`get_tuners()` returns cached data populated by a prior refresh."""
        tuners = [
            {
                "in_use": True,
                "channel": "/guide/channels/100",
                "recording": None,
                "channel_identifier": "7.1",
            }
        ]
        responses.add(responses.GET, f"{BASE_URL}/server/tuners", json=tuners)

        tablo_client.refresh_tuners()
        result = tablo_client.get_tuners()

        assert result[0]["in_use"] is True
        assert len(responses.calls) == 1

    @responses.activate
    def test_get_tuners_cache_expiry(self, tablo_client: TabloClient) -> None:
        """Expired tuner cache triggers a fresh API call."""
        tuners = [
            {
                "in_use": False,
                "channel": None,
                "recording": None,
                "channel_identifier": None,
            }
        ]
        responses.add(responses.GET, f"{BASE_URL}/server/tuners", json=tuners)
        responses.add(responses.GET, f"{BASE_URL}/server/tuners", json=tuners)

        tablo_client.get_tuners()
        tablo_client._tuner_cache.clear()
        tablo_client.get_tuners()

        assert len(responses.calls) == 2  # noqa: PLR2004

    @responses.activate
    def test_refresh_tuners_bypasses_cache(self, tablo_client: TabloClient) -> None:
        """`refresh_tuners()` bypasses cache and makes a fresh API call."""
        tuners = [
            {
                "in_use": False,
                "channel": None,
                "recording": None,
                "channel_identifier": None,
            }
        ]
        responses.add(responses.GET, f"{BASE_URL}/server/tuners", json=tuners)
        responses.add(responses.GET, f"{BASE_URL}/server/tuners", json=tuners)

        tablo_client.get_tuners()
        tablo_client.refresh_tuners()

        assert len(responses.calls) == 2  # noqa: PLR2004

    @responses.activate
    def test_refresh_tuners_returns_fresh_data(self, tablo_client: TabloClient) -> None:
        """`refresh_tuners()` returns updated data, not stale cache."""
        old = [
            {
                "in_use": False,
                "channel": None,
                "recording": None,
                "channel_identifier": None,
            }
        ]
        new = [
            {
                "in_use": True,
                "channel": "/guide/channels/100",
                "recording": None,
                "channel_identifier": "7.1",
            }
        ]
        responses.add(responses.GET, f"{BASE_URL}/server/tuners", json=old)
        responses.add(responses.GET, f"{BASE_URL}/server/tuners", json=new)

        first = tablo_client.get_tuners()
        refreshed = tablo_client.refresh_tuners()

        assert first[0]["in_use"] is False
        assert refreshed[0]["in_use"] is True


class TestCoalescing:
    """Tests for concurrent request coalescing via double-checked locking."""

    @responses.activate
    def test_get_channels_coalesces_concurrent_requests(
        self, tablo_client: TabloClient
    ) -> None:
        """Concurrent cache misses trigger only one fetch; all get same result."""
        fetch_entered = threading.Event()
        proceed = threading.Event()

        def slow_response(_request: Any) -> tuple[int, dict[str, str], str]:
            fetch_entered.set()
            proceed.wait(timeout=5)
            return (200, {}, json.dumps(["/guide/channels/100"]))

        responses.add_callback(
            responses.GET, f"{BASE_URL}/guide/channels", callback=slow_response
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/channels/100": make_channel(100, "WABC", 7, 1)},
        )

        results: list[Any] = [None, None, None]
        errors: list[BaseException | None] = [None, None, None]

        def fetch(index: int) -> None:
            try:
                results[index] = tablo_client.get_channels()
            except Exception as e:  # noqa: BLE001
                errors[index] = e

        threads = [threading.Thread(target=fetch, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()

        assert fetch_entered.wait(
            timeout=5
        )  # Thread 1 is mid-fetch, holding _fetch_lock
        time.sleep(0.05)  # Let threads 2 & 3 reach the lock
        proceed.set()

        for t in threads:
            t.join(timeout=5)

        assert not any(t.is_alive() for t in threads)
        assert not any(errors), f"Worker thread raised: {errors}"

        assert len(responses.calls) == 2  # noqa: PLR2004, 1 GET + 1 POST
        assert all(r == results[0] for r in results)

    @responses.activate
    def test_get_airings_coalesces_concurrent_requests(
        self, tablo_client: TabloClient
    ) -> None:
        """Concurrent cache misses trigger only one fetch; all get same result."""
        fetch_entered = threading.Event()
        proceed = threading.Event()

        def slow_response(_request: Any) -> tuple[int, dict[str, str], str]:
            fetch_entered.set()
            proceed.wait(timeout=5)
            return (200, {}, json.dumps(["/guide/series/episodes/500"]))

        responses.add_callback(
            responses.GET, f"{BASE_URL}/guide/airings", callback=slow_response
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/batch",
            json={"/guide/series/episodes/500": make_episode_airing(500, "Show A")},
        )

        results: list[Any] = [None, None, None]
        errors: list[BaseException | None] = [None, None, None]

        def fetch(index: int) -> None:
            try:
                results[index] = tablo_client.get_airings()
            except Exception as e:  # noqa: BLE001
                errors[index] = e

        threads = [threading.Thread(target=fetch, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()

        assert fetch_entered.wait(timeout=5)
        time.sleep(0.05)
        proceed.set()

        for t in threads:
            t.join(timeout=5)

        assert not any(t.is_alive() for t in threads)
        assert not any(errors), f"Worker thread raised: {errors}"

        assert len(responses.calls) == 2  # noqa: PLR2004, 1 GET + 1 POST
        assert all(r == results[0] for r in results)

    @responses.activate
    def test_get_tuners_coalesces_concurrent_requests(
        self, tablo_client: TabloClient
    ) -> None:
        """Concurrent cache misses trigger only one fetch; all get same result."""
        fetch_entered = threading.Event()
        proceed = threading.Event()

        def slow_response(_request: Any) -> tuple[int, dict[str, str], str]:
            fetch_entered.set()
            proceed.wait(timeout=5)
            return (
                200,
                {},
                json.dumps([
                    {
                        "in_use": False,
                        "channel": None,
                        "recording": None,
                        "channel_identifier": None,
                    }
                ]),
            )

        responses.add_callback(
            responses.GET, f"{BASE_URL}/server/tuners", callback=slow_response
        )

        results: list[Any] = [None, None, None]
        errors: list[BaseException | None] = [None, None, None]

        def fetch(index: int) -> None:
            try:
                results[index] = tablo_client.get_tuners()
            except Exception as e:  # noqa: BLE001
                errors[index] = e

        threads = [threading.Thread(target=fetch, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()

        assert fetch_entered.wait(timeout=5)
        time.sleep(0.05)
        proceed.set()

        for t in threads:
            t.join(timeout=5)

        assert not any(t.is_alive() for t in threads)
        assert not any(errors), f"Worker thread raised: {errors}"

        assert len(responses.calls) == 1  # Only 1 GET, no batch for tuners
        assert all(r == results[0] for r in results)
