"""Tests for retry, session, and error handling in the Tablo API client."""

import threading

import pytest
import requests
import responses

from tablo_legacy_m3u.tablo_client import (
    RETRY_COUNT,
    TabloClient,
    TabloServerBusyError,
)
from tablo_legacy_m3u.tablo_types import ServerInfo

TABLO_IP = "192.168.1.100"
BASE_URL = f"http://{TABLO_IP}:8885"


class TestRetry:
    """Tests for auto-retry on HTTP 5xx responses (502), no retry for watch endpoint."""

    @responses.activate
    def test_retries_on_502_and_succeeds(
        self, tablo_client: TabloClient, server_info: ServerInfo
    ) -> None:
        """A `502` followed by a success results in a valid response."""
        responses.add(responses.GET, f"{BASE_URL}/server/info", status=502)
        responses.add(
            responses.GET,
            f"{BASE_URL}/server/info",
            json=server_info,
        )

        result = tablo_client.get_server_info()

        assert result["name"] == "Test Tablo"
        assert len(responses.calls) == 2  # noqa: PLR2004, Value here is more readable raw.

    @responses.activate
    def test_raises_after_retries_exhausted(self, tablo_client: TabloClient) -> None:
        """Three consecutive `502`s exhaust retries and raise HTTPError."""
        responses.add(responses.GET, f"{BASE_URL}/server/info", status=502)
        responses.add(responses.GET, f"{BASE_URL}/server/info", status=502)
        responses.add(responses.GET, f"{BASE_URL}/server/info", status=502)

        with pytest.raises(requests.HTTPError):
            tablo_client.get_server_info()

        assert len(responses.calls) == RETRY_COUNT + 1

    @responses.activate
    def test_no_retry_on_watch(self, tablo_client: TabloClient) -> None:
        """Watch endpoint does not retry on failure."""
        responses.add(
            responses.POST,
            f"{BASE_URL}/guide/channels/100/watch",
            status=502,
        )

        with pytest.raises(requests.HTTPError):
            tablo_client.get_watch_url("/guide/channels/100")

        assert len(responses.calls) == 1


class TestThreadLocalSession:
    """Tests for thread-local session isolation."""

    def test_same_thread_reuses_session(self, tablo_client: TabloClient) -> None:
        """Accessing _session twice from the same thread returns the same object."""
        assert tablo_client._session is tablo_client._session

    def test_different_threads_get_different_sessions(
        self, tablo_client: TabloClient
    ) -> None:
        """Each thread receives its own Session instance."""
        sessions: dict[str, requests.Session] = {}

        def capture_session(name: str) -> None:
            sessions[name] = tablo_client._session

        t1 = threading.Thread(target=capture_session, args=("t1",))
        t2 = threading.Thread(target=capture_session, args=("t2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert sessions["t1"] is not sessions["t2"]


class TestServerBusy:
    """Tests for TabloServerBusyError parsing in _get()."""

    @responses.activate
    def test_raises_on_server_busy(self, tablo_client: TabloClient) -> None:
        """_get() raises TabloServerBusyError when Tablo returns server_busy."""
        server_busy_body = {
            "error": {
                "code": "unavailable",
                "details": {"reason": "server_busy", "retry_in": 15000},
            }
        }
        responses.add(
            responses.GET,
            f"{BASE_URL}/server/info",
            json=server_busy_body,
            status=503,
        )

        with pytest.raises(TabloServerBusyError) as exc_info:
            tablo_client.get_server_info()

        assert exc_info.value.retry_in_s == pytest.approx(15.0)

    @responses.activate
    def test_regular_503_raises_http_error(self, tablo_client: TabloClient) -> None:
        """Non-server_busy 503 raises standard HTTPError."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/server/info",
            body="Service Unavailable",
            status=503,
        )

        with pytest.raises(requests.HTTPError):
            tablo_client.get_server_info()

    @responses.activate
    def test_server_busy_is_http_error(self, tablo_client: TabloClient) -> None:
        """TabloServerBusyError is a subclass of HTTPError."""
        server_busy_body = {
            "error": {
                "code": "unavailable",
                "details": {"reason": "server_busy", "retry_in": 15000},
            }
        }
        responses.add(
            responses.GET,
            f"{BASE_URL}/server/info",
            json=server_busy_body,
            status=503,
        )

        with pytest.raises(requests.HTTPError):
            tablo_client.get_server_info()
