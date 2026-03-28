"""Main module."""

import logging

from typing import TYPE_CHECKING

from rich.logging import RichHandler

from tablo_legacy_m3u import create_app
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

    if config.enable_epg and not client.has_guide_subscription():
        logger.warning("EPG enabled but no active guide subscription. EPG disabled.")

    enable_epg = config.enable_epg and client.has_guide_subscription()

    app = create_app(
        config=config,
        tablo_client=client,
        server_info=server_info,
        enable_epg=enable_epg,
    )

    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug,
        use_reloader=config.debug,
        exclude_patterns=["**/tests/**"],
    )
