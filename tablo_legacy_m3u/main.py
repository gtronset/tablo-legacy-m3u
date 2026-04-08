"""Main module."""

import logging
import os
import threading
import time

from collections.abc import Callable
from datetime import UTC, datetime

from flask import Flask
from rich.logging import RichHandler
from waitress import serve

from tablo_legacy_m3u import create_app
from tablo_legacy_m3u.app_state import AppState, DeviceStatus, InitPhase
from tablo_legacy_m3u.config import Config, load_config
from tablo_legacy_m3u.scheduler import Scheduler
from tablo_legacy_m3u.tablo_client import (
    TabloClient,
    TabloServerBusyError,
    discover_tablo_ip,
)

PROBE_REFRESH_INTERVAL = 60  # seconds


def _run_startup_probe[T](
    fn: Callable[[], T],
    *,
    logger: logging.Logger,
    max_attempts: int = 5,
) -> T:
    """Retry a callable on TabloServerBusyError, using the server's retry hint."""
    for attempt in range(max_attempts):
        try:
            return fn()
        except TabloServerBusyError as e:
            if attempt < max_attempts - 1:
                logger.warning(
                    "Tablo busy during startup, retrying in %ds", int(e.retry_in_s)
                )
                time.sleep(e.retry_in_s)

    msg = f"Tablo unavailable after {max_attempts} attempts"
    raise RuntimeError(msg)


def _probe_device(app_state: AppState) -> None:
    """Periodically fetch health data from the Tablo and update device status."""
    client = app_state.tablo_client
    if client is None:
        return

    try:
        server_info = client.get_server_info()
        tuners = client.get_tuners()
        harddrives = client.get_harddrives()
        guide_status = client.get_guide_status()

        last_guide_update = None
        if guide_status and guide_status.get("last_update"):
            last_guide_update = datetime.fromisoformat(guide_status["last_update"])

        app_state.device_status = DeviceStatus(
            server_info=server_info,
            tuners=tuners,
            harddrives=harddrives,
            guide_status=guide_status,
            last_guide_update=last_guide_update,
            last_probe=datetime.now(tz=UTC),
        )

    except Exception as exception:
        app_state.device_status = DeviceStatus(
            server_info=app_state.device_status.server_info,
            tuners=app_state.device_status.tuners,
            harddrives=app_state.device_status.harddrives,
            guide_status=app_state.device_status.guide_status,
            last_guide_update=app_state.device_status.last_guide_update,
            last_probe=datetime.now(tz=UTC),
            error=str(exception),
        )
        raise


def _init_tablo(config: Config, app_state: AppState, logger: logging.Logger) -> None:
    """Background Tablo initialization."""
    try:
        # Phase: `DISCOVERING`
        app_state.set_phase(InitPhase.DISCOVERING)

        tablo_ip = discover_tablo_ip(config.autodiscover, config.tablo_ip)
        logger.info("Using Tablo device at %s", tablo_ip)

        # Phase: `CONNECTING`
        app_state.set_phase(InitPhase.CONNECTING)

        client = TabloClient(tablo_ip, cache_ttl=config.cache_ttl)
        app_state.tablo_client = client

        server_info = _run_startup_probe(client.get_server_info, logger=logger)
        app_state.device_status.server_info = server_info

        has_guide = _run_startup_probe(client.has_guide_subscription, logger=logger)
        if config.enable_epg and not has_guide:
            logger.warning(
                "EPG enabled but no active guide subscription. EPG disabled."
            )
        app_state.enable_epg = config.enable_epg and has_guide

        # Phase: `WARMING`
        app_state.set_phase(InitPhase.WARMING)

        probe_scheduler = Scheduler(
            "probe",
            interval=PROBE_REFRESH_INTERVAL,
            task=lambda: _probe_device(app_state),
        )
        app_state.schedulers.append(probe_scheduler)

        channel_scheduler = Scheduler(
            "channels", config.channel_refresh_interval, client.refresh_channels
        )
        app_state.schedulers.append(channel_scheduler)

        if app_state.enable_epg:
            guide_scheduler = Scheduler(
                "guide", config.guide_refresh_interval, client.refresh_airings
            )
            app_state.schedulers.append(guide_scheduler)

        probe_scheduler.warm()
        probe_scheduler.start()

        channel_scheduler.warm()
        channel_scheduler.start()

        if app_state.enable_epg:
            guide_scheduler.warm()
            guide_scheduler.start()

        # Phase: `READY`
        app_state.set_phase(InitPhase.READY)
    except Exception as exception:
        logger.exception("Tablo initialization failed")
        app_state.error = str(exception)

        for scheduler in app_state.schedulers:
            scheduler.stop()

        app_state.shutdown_executor()

        app_state.set_phase(InitPhase.ERROR)


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

    app_state = AppState()
    app = create_app(config=config, app_state=app_state)

    init_thread = threading.Thread(
        target=_init_tablo,
        args=(config, app_state, logger),
        name="init-tablo",
        daemon=True,
    )
    init_thread.start()

    try:
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
        for scheduler in app_state.schedulers:
            scheduler.stop()

        app_state.shutdown_executor()
