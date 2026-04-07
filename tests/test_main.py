"""Tests for the main module."""

import logging
import os

from collections.abc import Callable
from typing import cast
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from tablo_legacy_m3u.app_state import AppState, InitPhase
from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.main import _init_tablo, _probe_device, _run_startup_probe, main
from tablo_legacy_m3u.tablo_client import TabloServerBusyError
from tests.conftest import TABLO_IP

TEST_LOGGER: logging.Logger = logging.getLogger("test")

type InitTabloFn = Callable[..., AppState]


class TestMain:
    """Tests for main() orchestration."""

    @patch("tablo_legacy_m3u.main.threading")
    @patch("tablo_legacy_m3u.main.serve")
    @patch("tablo_legacy_m3u.main.create_app")
    @patch("tablo_legacy_m3u.main.load_config")
    def test_uses_waitress_when_production(
        self,
        mock_config: MagicMock,
        mock_create_app: MagicMock,
        mock_serve: MagicMock,
        mock_threading: MagicMock,
    ) -> None:
        """Production mode starts waitress."""
        mock_config.return_value = Config(environment="production", tablo_ip=TABLO_IP)
        mock_create_app.return_value = MagicMock()

        main()

        mock_serve.assert_called_once()

    @patch.dict(os.environ, {"WERKZEUG_RUN_MAIN": "true"})
    @patch("tablo_legacy_m3u.main.threading")
    @patch("tablo_legacy_m3u.main.serve")
    @patch("tablo_legacy_m3u.main.create_app")
    @patch("tablo_legacy_m3u.main.load_config")
    def test_dev_child_uses_flask_dev_server(
        self,
        mock_config: MagicMock,
        mock_create_app: MagicMock,
        mock_serve: MagicMock,
        mock_threading: MagicMock,
    ) -> None:
        """Dev child process uses Flask dev server."""
        mock_config.return_value = Config(environment="development", tablo_ip=TABLO_IP)
        app = MagicMock()
        mock_create_app.return_value = app

        main()

        app.run.assert_called_once()
        mock_serve.assert_not_called()

    @patch("tablo_legacy_m3u.main.Flask")
    @patch("tablo_legacy_m3u.main.load_config")
    def test_dev_parent_returns_early(
        self,
        mock_config: MagicMock,
        mock_flask: MagicMock,
    ) -> None:
        """Reloader parent skips Tablo init and starts Flask directly."""
        mock_config.return_value = Config(environment="development", tablo_ip=TABLO_IP)

        main()

        mock_flask.assert_called_once()
        mock_flask.return_value.run.assert_called_once()

    @patch("tablo_legacy_m3u.main.threading")
    @patch("tablo_legacy_m3u.main.serve")
    @patch("tablo_legacy_m3u.main.create_app")
    @patch("tablo_legacy_m3u.main.load_config")
    def test_spawns_init_thread(
        self,
        mock_config: MagicMock,
        mock_create_app: MagicMock,
        mock_serve: MagicMock,
        mock_threading: MagicMock,
    ) -> None:
        """`main()` spawns a daemon thread for _init_tablo."""
        mock_config.return_value = Config(environment="production", tablo_ip=TABLO_IP)
        mock_create_app.return_value = MagicMock()

        main()

        mock_threading.Thread.assert_called_once()
        call_kwargs = mock_threading.Thread.call_args.kwargs

        assert call_kwargs["name"] == "init-tablo"
        assert call_kwargs["daemon"] is True

        mock_threading.Thread.return_value.start.assert_called_once()

    @patch("tablo_legacy_m3u.main.threading")
    @patch("tablo_legacy_m3u.main.serve", side_effect=RuntimeError("server crashed"))
    @patch("tablo_legacy_m3u.main.create_app")
    @patch("tablo_legacy_m3u.main.load_config")
    def test_schedulers_stopped_on_server_error(
        self,
        mock_config: MagicMock,
        mock_create_app: MagicMock,
        mock_serve: MagicMock,
        mock_threading: MagicMock,
    ) -> None:
        """All schedulers in `app_state` are stopped when server raises."""
        mock_config.return_value = Config(environment="production", tablo_ip=TABLO_IP)
        mock_create_app.return_value = MagicMock()

        sched1, sched2 = MagicMock(), MagicMock()
        fake_state = AppState()
        fake_state.schedulers.extend([sched1, sched2])

        with (
            patch("tablo_legacy_m3u.main.AppState", return_value=fake_state),
            pytest.raises(RuntimeError, match="server crashed"),
        ):
            main()

        sched1.stop.assert_called_once()
        sched2.stop.assert_called_once()


class TestInitTablo:
    """Tests for _init_tablo background initialization."""

    @pytest.fixture
    def init_tablo(self) -> InitTabloFn:
        """Factory that runs _init_tablo and returns the resulting AppState."""

        def _run(config: Config | None = None) -> AppState:
            app_state = AppState()

            _init_tablo(
                config or Config(environment="production", tablo_ip=TABLO_IP),
                app_state,
                TEST_LOGGER,
            )

            return app_state

        return _run

    @patch("tablo_legacy_m3u.main.Scheduler")
    @patch("tablo_legacy_m3u.main.TabloClient")
    @patch("tablo_legacy_m3u.main.discover_tablo_ip", return_value=TABLO_IP)
    def test_reaches_ready(
        self,
        mock_discover: MagicMock,
        mock_client_cls: MagicMock,
        mock_sched: MagicMock,
        init_tablo: InitTabloFn,
    ) -> None:
        """Successful init transitions through all phases to READY."""
        mock_client_cls.return_value.has_guide_subscription.return_value = True

        app_state = init_tablo()

        assert app_state.phase == InitPhase.READY
        assert app_state.ready.is_set()
        assert app_state.device_status.server_info is not None
        assert app_state.tablo_client is not None

    @patch("tablo_legacy_m3u.main.time")
    @patch("tablo_legacy_m3u.main.TabloClient")
    @patch("tablo_legacy_m3u.main.discover_tablo_ip", return_value=TABLO_IP)
    def test_sets_error_on_failure(
        self,
        mock_discover: MagicMock,
        mock_client_cls: MagicMock,
        mock_time: MagicMock,
        init_tablo: InitTabloFn,
    ) -> None:
        """Failed init sets ERROR phase and stores error message."""
        busy = TabloServerBusyError(MagicMock(), 15000)
        mock_client_cls.return_value.get_server_info.side_effect = busy

        app_state = init_tablo()

        assert app_state.phase == InitPhase.ERROR
        assert not app_state.ready.is_set()
        assert app_state.error is not None
        assert "Tablo unavailable" in app_state.error

    @patch("tablo_legacy_m3u.main.time")
    @patch("tablo_legacy_m3u.main.Scheduler")
    @patch("tablo_legacy_m3u.main.TabloClient")
    @patch("tablo_legacy_m3u.main.discover_tablo_ip", return_value=TABLO_IP)
    def test_retries_server_busy_then_succeeds(
        self,
        mock_discover: MagicMock,
        mock_client_cls: MagicMock,
        mock_sched: MagicMock,
        mock_time: MagicMock,
        init_tablo: InitTabloFn,
    ) -> None:
        """Init retries on TabloServerBusyError and reaches READY."""
        busy = TabloServerBusyError(MagicMock(), 15000)
        client = mock_client_cls.return_value
        client.get_server_info.side_effect = [busy, busy, MagicMock()]
        client.has_guide_subscription.return_value = True

        app_state = init_tablo()

        assert app_state.phase == InitPhase.READY
        assert client.get_server_info.call_count == 3  # noqa: PLR2004, Value here is more readable raw.
        assert mock_time.sleep.call_count == 2  # noqa: PLR2004, Value here is more readable raw.
        mock_time.sleep.assert_called_with(15.0)

    @patch("tablo_legacy_m3u.main.Scheduler")
    @patch("tablo_legacy_m3u.main.TabloClient")
    @patch("tablo_legacy_m3u.main.discover_tablo_ip", return_value=TABLO_IP)
    def test_guide_scheduler_skipped_when_no_subscription(
        self,
        mock_discover: MagicMock,
        mock_client_cls: MagicMock,
        mock_sched: MagicMock,
        init_tablo: InitTabloFn,
    ) -> None:
        """Only channel and probe schedulers are created when guide sub. is absent."""
        mock_client_cls.return_value.has_guide_subscription.return_value = False

        init_tablo()

        names = [call.args[0] for call in mock_sched.call_args_list]
        assert names == ["probe", "channels"]

    @patch("tablo_legacy_m3u.main.Scheduler")
    @patch("tablo_legacy_m3u.main.TabloClient")
    @patch("tablo_legacy_m3u.main.discover_tablo_ip", return_value=TABLO_IP)
    def test_guide_scheduler_skipped_when_epg_disabled(
        self,
        mock_discover: MagicMock,
        mock_client_cls: MagicMock,
        mock_sched: MagicMock,
        init_tablo: InitTabloFn,
    ) -> None:
        """Only channel and probe schedulers are created when EPG config is disabled."""
        mock_client_cls.return_value.has_guide_subscription.return_value = True

        init_tablo(
            Config(environment="production", tablo_ip=TABLO_IP, enable_epg=False)
        )

        names = [call.args[0] for call in mock_sched.call_args_list]
        assert names == ["probe", "channels"]

    @patch("tablo_legacy_m3u.main.Scheduler")
    @patch("tablo_legacy_m3u.main.TabloClient")
    @patch("tablo_legacy_m3u.main.discover_tablo_ip", return_value=TABLO_IP)
    def test_both_schedulers_created_with_epg(
        self,
        mock_discover: MagicMock,
        mock_client_cls: MagicMock,
        mock_sched: MagicMock,
        init_tablo: InitTabloFn,
    ) -> None:
        """Channel, guide, and probe schedulers are created when EPG is enabled."""
        mock_client_cls.return_value.has_guide_subscription.return_value = True

        app_state = init_tablo()

        names = [call.args[0] for call in mock_sched.call_args_list]
        assert names == ["probe", "channels", "guide"]
        assert len(app_state.schedulers) == 3  # noqa: PLR2004, Value here is more readable raw.

    @patch("tablo_legacy_m3u.main.Scheduler")
    @patch("tablo_legacy_m3u.main.TabloClient")
    @patch("tablo_legacy_m3u.main.discover_tablo_ip", return_value=TABLO_IP)
    def test_enable_epg_false_when_no_subscription(
        self,
        mock_discover: MagicMock,
        mock_client_cls: MagicMock,
        mock_sched: MagicMock,
        init_tablo: InitTabloFn,
    ) -> None:
        """enable_epg is set to False when guide subscription is absent."""
        mock_client_cls.return_value.has_guide_subscription.return_value = False

        app_state = init_tablo()

        assert app_state.enable_epg is False

    @patch("tablo_legacy_m3u.main.discover_tablo_ip", side_effect=OSError("no device"))
    def test_sets_error_on_discovery_failure(
        self,
        mock_discover: MagicMock,
        init_tablo: InitTabloFn,
    ) -> None:
        """Discovery failure sets ERROR phase and stores error message."""
        app_state = init_tablo()

        assert app_state.phase == InitPhase.ERROR
        assert app_state.error is not None
        assert "no device" in app_state.error

    @patch("tablo_legacy_m3u.main.Scheduler")
    @patch("tablo_legacy_m3u.main.TabloClient")
    @patch("tablo_legacy_m3u.main.discover_tablo_ip", return_value=TABLO_IP)
    def test_stops_schedulers_on_warming_error(
        self,
        mock_discover: MagicMock,
        mock_client_cls: MagicMock,
        mock_sched: MagicMock,
        init_tablo: InitTabloFn,
    ) -> None:
        """Schedulers are stopped if init fails during WARMING phase."""
        mock_client_cls.return_value.has_guide_subscription.return_value = True

        mock_sched.side_effect = [MagicMock(), Exception("Guide scheduler failed")]

        app_state = init_tablo()

        assert app_state.phase == InitPhase.ERROR
        assert len(app_state.schedulers) == 1
        cast("MagicMock", app_state.schedulers[0]).stop.assert_called_once()

        assert app_state.error is not None
        assert "Guide scheduler failed" in app_state.error


class TestStartupProbe:
    """Tests for the `_run_startup_probe` helper function."""

    @patch("tablo_legacy_m3u.main.time")
    def test_retries_on_busy(self, mock_time: MagicMock) -> None:
        """_run_startup_probe retries using the server's retry hint."""
        busy = TabloServerBusyError(MagicMock(), 10000)
        fn = MagicMock(side_effect=[busy, "ok"])

        result = _run_startup_probe(fn, logger=TEST_LOGGER)

        assert result == "ok"
        assert fn.call_count == 2  # noqa: PLR2004, Value here is more readable raw.
        mock_time.sleep.assert_called_once_with(10.0)

    @patch("tablo_legacy_m3u.main.time")
    def test_raises_after_max_attempts(self, mock_time: MagicMock) -> None:
        """_run_startup_probe raises RuntimeError after exhausting attempts."""
        busy = TabloServerBusyError(MagicMock(), 5000)
        fn = MagicMock(side_effect=busy)

        with pytest.raises(RuntimeError, match="Tablo unavailable after 3 attempts"):
            _run_startup_probe(fn, logger=TEST_LOGGER, max_attempts=3)

        assert fn.call_count == 3  # noqa: PLR2004, Value here is more readable raw.
        assert mock_time.sleep.call_count == 2  # noqa: PLR2004, Value here is more readable raw.


class TestProbeDevice:
    """Tests for the _probe_device background function."""

    def test_returns_early_without_client(self) -> None:
        """Probe safely returns if tablo initializing is incomplete."""
        app_state = AppState()
        _probe_device(app_state, ZoneInfo("UTC"), TEST_LOGGER)
        assert app_state.device_status.last_probe is None

    def test_fetches_and_updates_data(self) -> None:
        """Probe successfully sets server_info, tuners, drives, and guide."""
        app_state = AppState()
        mock_client = MagicMock()
        app_state.tablo_client = mock_client

        mock_client.get_server_info.return_value = {"name": "Test Tablo"}
        mock_client.get_tuners.return_value = ["tuner1", "tuner2"]
        mock_client.get_harddrives.return_value = ["drive1"]
        mock_client.get_guide_status.return_value = {"state": "normal"}

        _probe_device(app_state, ZoneInfo("UTC"), TEST_LOGGER)

        assert (
            app_state.device_status.server_info
            is mock_client.get_server_info.return_value
        )
        assert app_state.device_status.tuners is mock_client.get_tuners.return_value
        assert (
            app_state.device_status.harddrives
            is mock_client.get_harddrives.return_value
        )
        assert (
            app_state.device_status.guide_status
            is mock_client.get_guide_status.return_value
        )
        assert app_state.device_status.error is None
        assert app_state.device_status.last_probe is not None

    def test_catches_and_logs_exception(self) -> None:
        """Probe network errors update the state error but don't crash."""
        app_state = AppState()
        mock_client = MagicMock()
        app_state.tablo_client = mock_client

        mock_client.get_server_info.side_effect = ConnectionError(
            "Tablo dropped off WiFi"
        )

        _probe_device(app_state, ZoneInfo("UTC"), TEST_LOGGER)

        assert app_state.device_status.error == "Tablo dropped off WiFi"
        assert app_state.device_status.last_probe is not None

    def test_last_probe_uses_configured_timezone(self) -> None:
        """last_probe timestamp uses the provided timezone."""
        app_state = AppState()
        app_state.tablo_client = MagicMock()
        tz = ZoneInfo("America/Chicago")

        _probe_device(app_state, tz, TEST_LOGGER)

        assert app_state.device_status.last_probe is not None
        assert app_state.device_status.last_probe.tzinfo == tz
