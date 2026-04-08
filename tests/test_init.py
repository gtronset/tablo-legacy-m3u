"""Tests for application creation."""

import logging

import pytest

from flask.testing import FlaskClient

from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.routes import events


class TestPartialCacheControl:
    """Partial and `/events` routes return `Cache-Control: no-store`."""

    @pytest.mark.parametrize(
        "path",
        ["/partials/status", "/partials/tuners", "/partials/device"],
    )
    def test_no_store(self, flask_client: FlaskClient, path: str) -> None:
        resp = flask_client.get(path)

        assert resp.headers["Cache-Control"] == "no-store"

    def test_events_no_store(self, flask_client: FlaskClient) -> None:
        with flask_client.application.test_request_context("/events"):
            resp = events()

            assert resp.headers.get("Cache-Control") is None
            resp.close()


class TestAccessLogging:
    """Tests for production access logging."""

    @pytest.mark.parametrize(
        "flask_client",
        [Config(environment="production")],
        indirect=True,
    )
    def test_logs_access_in_production_mode(
        self, flask_client: FlaskClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="tablo_legacy_m3u"):
            flask_client.get("/discover.json")

        assert any("GET /discover.json" in record.message for record in caplog.records)

    @pytest.mark.parametrize(
        "flask_client",
        [Config(environment="development")],
        indirect=True,
    )
    def test_no_access_log_in_development_mode(
        self, flask_client: FlaskClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="tablo_legacy_m3u"):
            flask_client.get("/discover.json")

        assert not any(
            "GET /discover.json" in record.message for record in caplog.records
        )
