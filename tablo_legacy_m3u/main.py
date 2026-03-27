"""Main module."""

import logging

from typing import TYPE_CHECKING

from rich.logging import RichHandler

from tablo_legacy_m3u.app import app
from tablo_legacy_m3u.config import load_config
from tablo_legacy_m3u.tablo_client import TabloClient, discover_tablo_ip

if TYPE_CHECKING:
    from tablo_legacy_m3u.config import Config
    from tablo_legacy_m3u.tablo_types import ServerInfo


def main() -> None:
    """Start the application."""
    config: Config = load_config()

    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=config.log_level,
        format="%(name)s  %(message)s",
        datefmt="[%H:%M:%S]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    tablo_ip = discover_tablo_ip(config.autodiscover, config.tablo_ip)

    logger.info("Using Tablo device at %s", tablo_ip)

    client = TabloClient(tablo_ip)
    server_info: ServerInfo = client.get_server_info()
    has_guide = client.has_guide_subscription()

    app.config["APP_CONFIG"] = config
    app.config["TABLO_CLIENT"] = client
    app.config["TABLO_SERVER_INFO"] = server_info
    app.config["ENABLE_EPG"] = config.enable_epg and has_guide

    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug,
        use_reloader=config.debug,
        exclude_patterns=["**/tests/**"],
    )
