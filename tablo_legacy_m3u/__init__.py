"""tablo-legacy-m3u: Tablo TV M3U & EPG generator for legacy devices."""

import logging
import time

from typing import TYPE_CHECKING

from flask import Flask, Response, g, request

from tablo_legacy_m3u._version import __version__
from tablo_legacy_m3u.routes import register_routes

__all__ = ["__version__", "create_app"]

if TYPE_CHECKING:
    from tablo_legacy_m3u.config import Config
    from tablo_legacy_m3u.scheduler import Scheduler
    from tablo_legacy_m3u.tablo_client import TabloClient
    from tablo_legacy_m3u.tablo_types import ServerInfo

logger = logging.getLogger(__name__)


def create_app(
    *,
    config: "Config",
    tablo_client: "TabloClient",
    server_info: "ServerInfo",
    enable_epg: bool,
    schedulers: "list[Scheduler] | None" = None,
) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    app.config.from_mapping(
        APP_CONFIG=config,
        TABLO_CLIENT=tablo_client,
        TABLO_SERVER_INFO=server_info,
        ENABLE_EPG=enable_epg,
        SCHEDULERS=schedulers or [],
    )

    register_routes(app)

    if not config.is_dev:

        @app.before_request
        def start_timer() -> None:
            g.start_time = time.monotonic()

        @app.after_request
        def log_request(response: Response) -> Response:
            duration = time.monotonic() - g.start_time
            logger.info(
                '%s %s - "%s %s" %s (%.3fs)',
                request.remote_addr,
                request.host,
                request.method,
                request.path,
                response.status_code,
                duration,
            )
            return response

    return app
