"""Main module."""

import logging

from rich.logging import RichHandler

from tablo_legacy_m3u.app import app
from tablo_legacy_m3u.config import load_config
from tablo_legacy_m3u.tablo_client import TabloClient, discover_tablo_ip


def main() -> None:
    """Start the application."""
    config = load_config()

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
    server_info = client.get_server_info()
    has_guide = client.has_guide_subscription()

    app.config["APP_CONFIG"] = config
    app.config["TABLO_CLIENT"] = client
    app.config["TABLO_SERVER_INFO"] = server_info
    app.config["ENABLE_EPG"] = config.enable_epg and has_guide

    app.run(host=config.host, port=config.port, use_reloader=True)
