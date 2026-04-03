"""Tests for the main module."""

import logging
import os

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.main import _run_startup_probe, main
from tablo_legacy_m3u.tablo_client import TabloServerBusyError


@pytest.fixture
def patch_discover() -> Generator[MagicMock]:
    """Patch `discover_tablo_ip` to prevent real network calls in tests."""
    with patch(
        "tablo_legacy_m3u.main.discover_tablo_ip", return_value="10.0.0.1"
    ) as mock:
        yield mock


@pytest.fixture
def mock_scheduler() -> Generator[MagicMock]:
    """Patch `Scheduler` to prevent real scheduling in tests."""
    with patch("tablo_legacy_m3u.main.Scheduler") as mock:
        mock.instances = []

        def make_instance(*args: object, **kwargs: object) -> MagicMock:
            instance = MagicMock()
            mock.instances.append(instance)
            return instance

        mock.side_effect = make_instance
        yield mock


@pytest.mark.usefixtures("patch_discover", "mock_scheduler")
@patch("tablo_legacy_m3u.main.serve")
@patch("tablo_legacy_m3u.main.create_app")
@patch("tablo_legacy_m3u.main.TabloClient")
@patch("tablo_legacy_m3u.main.load_config")
def test_uses_waitress_when_production(
    mock_config: MagicMock,
    mock_client_cls: MagicMock,
    mock_create_app: MagicMock,
    mock_serve: MagicMock,
) -> None:
    """When `environment` is production, `main()` starts `waitress`."""
    mock_config.return_value = Config(environment="production", tablo_ip="10.0.0.1")
    mock_client_cls.return_value.has_guide_subscription.return_value = True

    app = MagicMock()
    mock_create_app.return_value = app

    main()

    mock_serve.assert_called_once()
    app.run.assert_not_called()


@pytest.mark.usefixtures("patch_discover", "mock_scheduler")
@patch.dict(os.environ, {"WERKZEUG_RUN_MAIN": "true"})
@patch("tablo_legacy_m3u.main.serve")
@patch("tablo_legacy_m3u.main.create_app")
@patch("tablo_legacy_m3u.main.TabloClient")
@patch("tablo_legacy_m3u.main.load_config")
def test_dev_child_uses_flask_dev_server(
    mock_config: MagicMock,
    mock_client_cls: MagicMock,
    mock_create_app: MagicMock,
    mock_serve: MagicMock,
) -> None:
    """When `environment` is development, `main()` starts the Flask dev server."""
    mock_config.return_value = Config(environment="development", tablo_ip="10.0.0.1")
    mock_client_cls.return_value.has_guide_subscription.return_value = True

    app = MagicMock()
    mock_create_app.return_value = app

    main()

    app.run.assert_called_once()
    mock_serve.assert_not_called()


@patch("tablo_legacy_m3u.main.Flask")
@patch("tablo_legacy_m3u.main.load_config")
def test_dev_parent_returns_early(
    mock_config: MagicMock,
    mock_flask: MagicMock,
    patch_discover: MagicMock,
    mock_scheduler: MagicMock,
) -> None:
    """Reloader parent skips Tablo init and scheduler creation."""
    mock_config.return_value = Config(environment="development", tablo_ip="10.0.0.1")

    main()

    mock_flask.assert_called_once()
    mock_flask.return_value.run.assert_called_once()
    patch_discover.assert_not_called()
    mock_scheduler.assert_not_called()


@pytest.mark.usefixtures("patch_discover")
@patch("tablo_legacy_m3u.main.serve")
@patch("tablo_legacy_m3u.main.create_app")
@patch("tablo_legacy_m3u.main.TabloClient")
@patch("tablo_legacy_m3u.main.load_config")
def test_guide_scheduler_skipped_when_no_subscription(
    mock_config: MagicMock,
    mock_client_cls: MagicMock,
    mock_create_app: MagicMock,
    mock_serve: MagicMock,  # noqa: ARG001
    mock_scheduler: MagicMock,
) -> None:
    """Only channel scheduler is created when guide subscription is absent."""
    mock_config.return_value = Config(environment="production", tablo_ip="10.0.0.1")
    mock_client_cls.return_value.has_guide_subscription.return_value = False
    mock_create_app.return_value = MagicMock()

    main()

    names = [call.args[0] for call in mock_scheduler.call_args_list]
    assert names == ["channels"]


@pytest.mark.usefixtures("patch_discover")
@patch("tablo_legacy_m3u.main.serve")
@patch("tablo_legacy_m3u.main.create_app")
@patch("tablo_legacy_m3u.main.TabloClient")
@patch("tablo_legacy_m3u.main.load_config")
def test_guide_scheduler_skipped_when_epg_disabled(
    mock_config: MagicMock,
    mock_client_cls: MagicMock,
    mock_create_app: MagicMock,
    mock_serve: MagicMock,  # noqa: ARG001
    mock_scheduler: MagicMock,
) -> None:
    """Only channel scheduler is created when EPG is disabled in config."""
    mock_config.return_value = Config(
        environment="production", tablo_ip="10.0.0.1", enable_epg=False
    )
    mock_client_cls.return_value.has_guide_subscription.return_value = True
    mock_create_app.return_value = MagicMock()

    main()

    names = [call.args[0] for call in mock_scheduler.call_args_list]
    assert names == ["channels"]


@pytest.mark.usefixtures("patch_discover")
@patch("tablo_legacy_m3u.main.serve", side_effect=RuntimeError("server crashed"))
@patch("tablo_legacy_m3u.main.create_app")
@patch("tablo_legacy_m3u.main.TabloClient")
@patch("tablo_legacy_m3u.main.load_config")
def test_schedulers_stopped_on_server_error(
    mock_config: MagicMock,
    mock_client_cls: MagicMock,
    mock_create_app: MagicMock,
    mock_serve: MagicMock,  # noqa: ARG001
    mock_scheduler: MagicMock,
) -> None:
    """All schedulers are stopped even when the server raises."""
    mock_config.return_value = Config(environment="production", tablo_ip="10.0.0.1")
    mock_client_cls.return_value.has_guide_subscription.return_value = True
    mock_create_app.return_value = MagicMock()

    with pytest.raises(RuntimeError, match="server crashed"):
        main()

    assert len(mock_scheduler.instances) == 2  # noqa: PLR2004, one for guide and one for channels
    for instance in mock_scheduler.instances:
        instance.stop.assert_called_once()


@pytest.mark.usefixtures("patch_discover", "mock_scheduler")
@patch("tablo_legacy_m3u.main.time")
@patch("tablo_legacy_m3u.main.serve")
@patch("tablo_legacy_m3u.main.create_app")
@patch("tablo_legacy_m3u.main.TabloClient")
@patch("tablo_legacy_m3u.main.load_config")
def test_retries_on_tablo_server_busy(
    mock_config: MagicMock,
    mock_client_cls: MagicMock,
    mock_create_app: MagicMock,
    mock_serve: MagicMock,  # noqa: ARG001
    mock_time: MagicMock,
) -> None:
    """Startup retries get_server_info when Tablo returns server_busy."""
    mock_config.return_value = Config(environment="production", tablo_ip="10.0.0.1")

    busy = TabloServerBusyError(MagicMock(), 15000)
    client = mock_client_cls.return_value
    client.get_server_info.side_effect = [busy, busy, MagicMock()]
    client.has_guide_subscription.return_value = True
    mock_create_app.return_value = MagicMock()

    main()

    assert client.get_server_info.call_count == 3  # noqa: PLR2004, Value here is more readable raw.
    assert mock_time.sleep.call_count == 2  # noqa: PLR2004, Value here is more readable raw.
    mock_time.sleep.assert_called_with(15.0)


@pytest.mark.usefixtures("patch_discover", "mock_scheduler")
@patch("tablo_legacy_m3u.main.time")
@patch("tablo_legacy_m3u.main.TabloClient")
@patch("tablo_legacy_m3u.main.load_config")
def test_raises_after_max_retries(
    mock_config: MagicMock,
    mock_client_cls: MagicMock,
    mock_time: MagicMock,  # noqa: ARG001
) -> None:
    """Startup raises RuntimeError after 5 failed attempts."""
    mock_config.return_value = Config(environment="production", tablo_ip="10.0.0.1")

    busy = TabloServerBusyError(MagicMock(), 15000)
    client = mock_client_cls.return_value
    client.get_server_info.side_effect = busy  # always busy

    with pytest.raises(RuntimeError, match="Tablo unavailable after 5 attempts"):
        main()

    assert client.get_server_info.call_count == 5  # noqa: PLR2004, Value here is more readable raw.


@patch("tablo_legacy_m3u.main.time")
def test_run_startup_probe_retries_on_busy(mock_time: MagicMock) -> None:
    """_run_startup_probe retries using the server's retry hint."""
    busy = TabloServerBusyError(MagicMock(), 10000)
    fn = MagicMock(side_effect=[busy, "ok"])

    result = _run_startup_probe(fn, logger=logging.getLogger("test"))

    assert result == "ok"
    assert fn.call_count == 2  # noqa: PLR2004, Value here is more readable raw.
    mock_time.sleep.assert_called_once_with(10.0)


@patch("tablo_legacy_m3u.main.time")
def test_run_startup_probe_raises_after_max_attempts(mock_time: MagicMock) -> None:
    """_run_startup_probe raises RuntimeError after exhausting attempts."""
    busy = TabloServerBusyError(MagicMock(), 5000)
    fn = MagicMock(side_effect=busy)

    with pytest.raises(RuntimeError, match="Tablo unavailable after 3 attempts"):
        _run_startup_probe(fn, logger=logging.getLogger("test"), max_attempts=3)

    assert fn.call_count == 3  # noqa: PLR2004, Value here is more readable raw.
    assert mock_time.sleep.call_count == 3  # noqa: PLR2004, Value here is more readable raw.
