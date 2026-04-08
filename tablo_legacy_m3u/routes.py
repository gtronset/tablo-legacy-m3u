"""Route handlers for HDHomeRun-compatible endpoints."""

import logging
import queue

from collections.abc import Generator
from dataclasses import replace
from typing import TYPE_CHECKING

from flask import (
    Flask,
    Response,
    abort,
    current_app,
    render_template,
    request,
    send_from_directory,
)

from tablo_legacy_m3u._version import __version__
from tablo_legacy_m3u.app_state import AppState, InitPhase
from tablo_legacy_m3u.discover import device_info, generate_device_xml
from tablo_legacy_m3u.epg import generate_xmltv
from tablo_legacy_m3u.filters import register_filters
from tablo_legacy_m3u.lineup import (
    generate_json,
    generate_m3u,
    generate_xml,
)
from tablo_legacy_m3u.tablo_client import TabloClient

if TYPE_CHECKING:
    from tablo_legacy_m3u.config import Config
    from tablo_legacy_m3u.tablo_types import Airing, Channel


TABLO_DEFAULT_DEVICE_NAME = "Tablo"

XML_MIMETYPE = "application/xml"
M3U_MIMETYPE = "application/x-mpegurl"
UTF8_CHARSET = "utf-8"

logger = logging.getLogger(__name__)


def register_routes(app: Flask) -> None:
    """Register all route handlers on the Flask app."""
    register_filters(app)

    app.add_url_rule("/events", view_func=events)

    app.add_url_rule("/", view_func=index)
    app.add_url_rule("/partials/status", view_func=partial_status)
    app.add_url_rule("/partials/tuners", view_func=partial_tuners)
    app.add_url_rule("/partials/device", view_func=partial_device)

    app.add_url_rule("/favicon.ico", view_func=favicon)

    app.add_url_rule("/health", view_func=health)

    app.add_url_rule("/discover.json", view_func=discover)
    app.add_url_rule("/device.xml", view_func=device_xml)

    app.add_url_rule("/lineup.m3u", view_func=lineup_m3u)
    app.add_url_rule("/lineup.m3u8", view_func=lineup_m3u, endpoint="lineup_m3u8")

    # HDHR-compatible endpoints (not all clients support these, but some require them)
    app.add_url_rule("/lineup.xml", view_func=lineup_xml)
    app.add_url_rule("/lineup.json", view_func=lineup_json)
    app.add_url_rule("/lineup_status.json", view_func=lineup_status)

    app.add_url_rule("/xmltv.xml", view_func=xmltv)

    app.add_url_rule("/watch/<int:channel_id>", view_func=watch)


def _require_ready() -> AppState:
    """Return app_state if ready, else abort 503."""
    app_state: AppState = current_app.config["APP_STATE"]

    if not app_state.ready.is_set():
        abort(503, description=f"Initializing ({app_state.phase})")

    return app_state


def _require_initialized() -> AppState:
    """Return app_state if past connecting phase, else abort 503."""
    app_state: AppState = current_app.config["APP_STATE"]

    if app_state.phase in {InitPhase.DISCOVERING, InitPhase.CONNECTING}:
        abort(503, description=f"Initializing ({app_state.phase})")

    return app_state


def _require_client(app_state: AppState) -> TabloClient:
    """Return the Tablo client if initialized, else abort 503."""
    tablo_client = app_state.tablo_client
    if tablo_client is None:
        abort(503, description="Tablo client not initialized")

    return tablo_client


def index() -> str:
    """Render the landing page with device info and endpoint links."""
    app_state: AppState = current_app.config["APP_STATE"]
    config: Config = current_app.config["APP_CONFIG"]
    server_info = app_state.device_status.server_info

    friendly_name = (
        config.device_name
        or (server_info["name"] if server_info else None)
        or TABLO_DEFAULT_DEVICE_NAME
    )
    base_url = request.host_url.rstrip("/")

    return render_template(
        "index.html",
        friendly_name=friendly_name,
        phase=app_state.phase,
        server_info=server_info,
        device_status=app_state.device_status,
        base_url=base_url,
        version=__version__,
        enable_epg=app_state.enable_epg,
        schedulers=app_state.schedulers,
    )


def partial_status() -> str:
    """Return status rows fragment for HTMX polling."""
    app_state = _require_initialized()

    return render_template(
        "_status_rows.html",
        schedulers=app_state.schedulers,
        enable_epg=app_state.enable_epg,
    )


def partial_tuners() -> str:
    """Return tuner dots fragment for HTMX polling."""
    app_state = _require_initialized()
    server_info = app_state.device_status.server_info

    if server_info is None:
        return ""

    return render_template(
        "_tuners.html",
        device_status=app_state.device_status,
        server_info=app_state.device_status.server_info,
    )


def partial_device() -> str:
    """Return device rows fragment for HTMX polling."""
    app_state = _require_initialized()

    return render_template(
        "_device_rows.html",
        device_status=app_state.device_status,
    )


def events() -> Response:
    """SSE endpoint for server-sent events about status changes."""
    app_state: AppState = current_app.config["APP_STATE"]
    q = app_state.sse_subscribe()

    def stream() -> Generator[str]:
        try:
            while True:
                try:
                    event = q.get(timeout=15)
                    yield f"event: {event}\ndata:\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            app_state.sse_unsubscribe(q)

    return Response(stream(), mimetype="text/event-stream")


def favicon() -> Response:
    """Serve the favicon."""
    return send_from_directory(current_app.static_folder or "static", "favicon.ico")


def health() -> tuple[dict[str, str], int]:
    """Return the health status of the application."""
    app_state: AppState = current_app.config["APP_STATE"]

    return {"status": app_state.phase}, 200


def discover() -> dict[str, str | int]:
    """Return HDHomeRun-style device descriptor."""
    config: Config = current_app.config["APP_CONFIG"]
    app_state: AppState = _require_ready()

    server_info = app_state.device_status.server_info
    if server_info is None:
        abort(503, description="Server info not available")

    base_url = request.host_url.rstrip("/")

    return device_info(config, server_info, base_url)


def device_xml() -> Response:
    """Return HDHomeRun-style device descriptor as XML."""
    config: Config = current_app.config["APP_CONFIG"]
    app_state: AppState = _require_ready()

    server_info = app_state.device_status.server_info
    if server_info is None:
        abort(503, description="Server info not available")

    base_url = request.host_url.rstrip("/")

    body = generate_device_xml(config, server_info, base_url)

    return Response(
        body,
        mimetype=XML_MIMETYPE,
        content_type=f"{XML_MIMETYPE}; charset={UTF8_CHARSET}",
    )


def lineup_m3u() -> Response:
    """Return the channel lineup as an M3U playlist."""
    app_state: AppState = _require_ready()

    tablo_client = _require_client(app_state)

    channels: list[Channel] = tablo_client.get_channels()

    base_url = request.host_url.rstrip("/")

    body = generate_m3u(channels, base_url)

    return Response(
        body,
        mimetype=M3U_MIMETYPE,
        content_type=f"{M3U_MIMETYPE}; charset={UTF8_CHARSET}",
    )


def lineup_json() -> list[dict[str, str]]:
    """Return the channel lineup in HDHomeRun JSON format."""
    app_state: AppState = _require_ready()

    tablo_client = _require_client(app_state)

    channels = tablo_client.get_channels()
    base_url = request.host_url.rstrip("/")

    return generate_json(channels, base_url)


def lineup_xml() -> Response:
    """Return the channel lineup as HDHomeRun-style XML."""
    app_state: AppState = _require_ready()

    tablo_client = _require_client(app_state)

    channels: list[Channel] = tablo_client.get_channels()

    base_url = request.host_url.rstrip("/")

    body = generate_xml(channels, base_url)

    return Response(
        body,
        mimetype=XML_MIMETYPE,
        content_type=f"{XML_MIMETYPE}; charset={UTF8_CHARSET}",
    )


def lineup_status() -> dict[str, str | int | list[str]]:
    """Return the lineup scan status."""
    return {
        "ScanInProgress": 0,
        "ScanPossible": 1,
        "Source": "Antenna",
        "SourceList": ["Antenna"],
    }


def xmltv() -> Response:
    """Return the XMLTV EPG guide."""
    app_state: AppState = _require_ready()

    if not app_state.enable_epg:
        abort(404, description="EPG is disabled")

    tablo_client = _require_client(app_state)

    channels: list[Channel] = tablo_client.get_channels()
    airings: list[Airing] = tablo_client.get_airings()

    body = generate_xmltv(channels, airings)

    return Response(
        body,
        mimetype=XML_MIMETYPE,
        content_type=f"{XML_MIMETYPE}; charset={UTF8_CHARSET}",
    )


def watch(channel_id: int) -> Response:
    """Redirect to a live stream for the given channel.

    Refreshes tuner status in the background so the status page reflects the new stream.
    """
    app_state: AppState = _require_ready()
    tablo_client = _require_client(app_state)
    channel_path = f"/guide/channels/{channel_id}"
    playlist_url = tablo_client.get_watch_url(channel_path)

    def _refresh_tuners() -> None:
        try:
            tuners = tablo_client.refresh_tuners()
            app_state.device_status = replace(app_state.device_status, tuners=tuners)
            app_state.sse_publish("tuners")
        except Exception:
            logger.exception("Failed to refresh tuners after watch")

    app_state.submit_tuner_refresh(_refresh_tuners)

    return Response(status=302, headers={"Location": playlist_url})
