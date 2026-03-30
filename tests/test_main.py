"""Tests for the main module."""

from unittest.mock import MagicMock, patch

from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.main import main


@patch("tablo_legacy_m3u.main.serve")
@patch("tablo_legacy_m3u.main.create_app")
@patch("tablo_legacy_m3u.main.TabloClient")
@patch("tablo_legacy_m3u.main.discover_tablo_ip", return_value="10.0.0.1")
@patch("tablo_legacy_m3u.main.load_config")
def test_uses_waitress_when_production(
    mock_config: MagicMock,
    mock_discover: MagicMock,  # noqa: ARG001
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


@patch("tablo_legacy_m3u.main.serve")
@patch("tablo_legacy_m3u.main.create_app")
@patch("tablo_legacy_m3u.main.TabloClient")
@patch("tablo_legacy_m3u.main.discover_tablo_ip", return_value="10.0.0.1")
@patch("tablo_legacy_m3u.main.load_config")
def test_uses_flask_dev_server_when_development(
    mock_config: MagicMock,
    mock_discover: MagicMock,  # noqa: ARG001
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
