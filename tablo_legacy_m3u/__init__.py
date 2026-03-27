"""tablo-legacy-m3u: Tablo TV M3U & EPG generator for legacy devices."""

from typing import TYPE_CHECKING

from flask import Flask

# from tablo_legacy_m3u.routes import register_routes

if TYPE_CHECKING:
    from tablo_legacy_m3u.config import Config
    from tablo_legacy_m3u.tablo_client import TabloClient
    from tablo_legacy_m3u.tablo_types import ServerInfo


def create_app(
    *,
    config: "Config | None" = None,
    tablo_client: "TabloClient | None" = None,
    server_info: "ServerInfo | None" = None,
    enable_epg: bool = False,
) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    app.config.from_mapping(
        APP_CONFIG=config,
        TABLO_CLIENT=tablo_client,
        TABLO_SERVER_INFO=server_info,
        ENABLE_EPG=enable_epg,
    )

    # register_routes(app)

    return app
