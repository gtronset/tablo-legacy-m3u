"""Tests for the main module."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.main import main


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
@patch("tablo_legacy_m3u.main.serve")
@patch("tablo_legacy_m3u.main.create_app")
@patch("tablo_legacy_m3u.main.TabloClient")
@patch("tablo_legacy_m3u.main.load_config")
def test_uses_flask_dev_server_when_development(
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
