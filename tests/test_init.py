"""Tests for application creation."""

import logging

import pytest

from flask.testing import FlaskClient

from tablo_legacy_m3u.config import Config


class TestAccessLogging:
    """Tests for production access logging."""

    @pytest.mark.parametrize(
        "client",
        [Config(environment="production")],
        indirect=True,
    )
    def test_logs_access_in_production_mode(
        self, client: FlaskClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="tablo_legacy_m3u"):
            client.get("/discover.json")

        assert any("GET /discover.json" in record.message for record in caplog.records)

    @pytest.mark.parametrize(
        "client",
        [Config(environment="development")],
        indirect=True,
    )
    def test_no_access_log_in_debug_mode(
        self, client: FlaskClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="tablo_legacy_m3u"):
            client.get("/discover.json")

        assert not any(
            "GET /discover.json" in record.message for record in caplog.records
        )
