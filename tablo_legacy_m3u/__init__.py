"""tablo-legacy-m3u: Tablo TV M3U & EPG generator for legacy devices."""

import logging
import time

from typing import TYPE_CHECKING

from flask import Flask, Response, g, request
from flask_compress import Compress

from tablo_legacy_m3u._version import __version__
from tablo_legacy_m3u.routes import register_routes

__all__ = ["__version__", "create_app"]

if TYPE_CHECKING:
    from tablo_legacy_m3u.app_state import AppState
    from tablo_legacy_m3u.config import Config

logger = logging.getLogger(__name__)

COMPRESS_ALGORITHM = ["br", "gzip"]
COMPRESS_MIN_SIZE = 256
COMPRESS_STREAMS = False


def create_app(
    *,
    config: "Config",
    app_state: "AppState",
) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    app.config.from_mapping(
        APP_CONFIG=config,
        APP_STATE=app_state,
        COMPRESS_ALGORITHM=COMPRESS_ALGORITHM,
        COMPRESS_MIN_SIZE=COMPRESS_MIN_SIZE,
        COMPRESS_STREAMS=COMPRESS_STREAMS,
    )

    Compress(app)
    register_routes(app)

    @app.after_request
    def no_cache_partials(response: Response) -> Response:
        if request.path.startswith("/partials/") or request.path == "/events":
            response.headers["Cache-Control"] = "no-store"
        return response

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
