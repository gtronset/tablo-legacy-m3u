"""Main module."""

import logging
import os

from typing import TYPE_CHECKING

from flask import Flask
from rich.logging import RichHandler
from waitress import serve

from tablo_legacy_m3u import create_app
from tablo_legacy_m3u.config import load_config
from tablo_legacy_m3u.scheduler import Scheduler
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
        handlers=[
            RichHandler(
                omit_repeated_times=False,
                show_path=config.is_dev,
                rich_tracebacks=True,
            )
        ],
    )

    logger.debug("Loaded config: %s", config)

    # In dev mode, run the parent reloader and start the server in the child process
    if config.is_dev and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        Flask(__name__).run(
            host=config.host,
            port=config.port,
            debug=True,
            use_reloader=True,
            exclude_patterns=["**/tests/**"],
        )
        return

    tablo_ip = discover_tablo_ip(config.autodiscover, config.tablo_ip)

    logger.info("Using Tablo device at %s", tablo_ip)

    client = TabloClient(tablo_ip, cache_ttl=config.cache_ttl)
    server_info: ServerInfo = client.get_server_info()

    has_guide_subscription = client.has_guide_subscription()

    if config.enable_epg and not has_guide_subscription:
        logger.warning("EPG enabled but no active guide subscription. EPG disabled.")

    enable_epg = config.enable_epg and has_guide_subscription

    schedulers: list[Scheduler] = []

    try:
        channel_scheduler = Scheduler(
            "channels", config.channel_refresh_interval, client.refresh_channels
        )
        channel_scheduler.warm_async()
        schedulers.append(channel_scheduler)
        channel_scheduler.start()

        if enable_epg:
            guide_scheduler = Scheduler(
                "guide", config.guide_refresh_interval, client.refresh_airings
            )
            guide_scheduler.warm_async()
            schedulers.append(guide_scheduler)
            guide_scheduler.start()

        app = create_app(
            config=config,
            tablo_client=client,
            server_info=server_info,
            enable_epg=enable_epg,
            schedulers=schedulers,
        )

        if config.is_dev:
            app.run(
                host=config.host,
                port=config.port,
                debug=True,
                use_reloader=True,
                exclude_patterns=["**/tests/**"],
            )
        else:
            logger.info("Starting waitress on %s:%d", config.host, config.port)
            serve(app, host=config.host, port=config.port)
    finally:
        for scheduler in schedulers:
            scheduler.stop()
