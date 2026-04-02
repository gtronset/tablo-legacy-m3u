"""Route handlers for HDHomeRun-compatible endpoints."""

from typing import TYPE_CHECKING

from flask import (
    Flask,
    Response,
    current_app,
    render_template,
    request,
    send_from_directory,
)

from tablo_legacy_m3u._version import __version__
from tablo_legacy_m3u.discover import device_info, generate_device_xml
from tablo_legacy_m3u.epg import generate_xmltv
from tablo_legacy_m3u.lineup import (
    generate_json,
    generate_m3u,
    generate_xml,
)

if TYPE_CHECKING:
    from tablo_legacy_m3u.config import Config
    from tablo_legacy_m3u.scheduler import Scheduler
    from tablo_legacy_m3u.tablo_client import TabloClient
    from tablo_legacy_m3u.tablo_types import Airing, Channel, ServerInfo

XML_MIMETYPE = "application/xml"
M3U_MIMETYPE = "application/x-mpegurl"
UTF8_CHARSET = "utf-8"


def register_routes(app: Flask) -> None:
    """Register all route handlers on the Flask app."""
    app.add_url_rule("/", view_func=index)

    app.add_url_rule("/favicon.ico", view_func=favicon)

    app.add_url_rule("/discover.json", view_func=discover)
    app.add_url_rule("/device.xml", view_func=device_xml)

    app.add_url_rule("/lineup.m3u", view_func=lineup_m3u)
    app.add_url_rule("/lineup.m3u8", view_func=lineup_m3u, endpoint="lineup_m3u8")

    # HDHR-compatible endpoints (not all clients support these, but some require them)
    app.add_url_rule("/lineup.xml", view_func=lineup_xml)
    app.add_url_rule("/lineup.json", view_func=lineup_json)
    app.add_url_rule("/lineup_status.json", view_func=lineup_status)

    if app.config["ENABLE_EPG"]:
        app.add_url_rule("/xmltv.xml", view_func=xmltv)

    app.add_url_rule("/watch/<int:channel_id>", view_func=watch)


def index() -> str:
    """Render the landing page with device info and endpoint links."""
    config: Config = current_app.config["APP_CONFIG"]
    server_info: ServerInfo = current_app.config["TABLO_SERVER_INFO"]
    schedulers: list[Scheduler] = current_app.config["SCHEDULERS"]

    friendly_name = config.device_name or server_info["name"]
    base_url = request.host_url.rstrip("/")

    enable_epg = current_app.config["ENABLE_EPG"]

    return render_template(
        "index.html",
        friendly_name=friendly_name,
        server_info=server_info,
        base_url=base_url,
        version=__version__,
        enable_epg=enable_epg,
        schedulers=schedulers,
    )


def favicon() -> Response:
    """Serve the favicon."""
    return send_from_directory(current_app.static_folder or "static", "favicon.ico")


def discover() -> dict[str, str | int]:
    """Return HDHomeRun-style device descriptor."""
    config: Config = current_app.config["APP_CONFIG"]
    server_info: ServerInfo = current_app.config["TABLO_SERVER_INFO"]
    base_url = request.host_url.rstrip("/")

    return device_info(config, server_info, base_url)


def device_xml() -> Response:
    """Return HDHomeRun-style device descriptor as XML."""
    config: Config = current_app.config["APP_CONFIG"]
    server_info: ServerInfo = current_app.config["TABLO_SERVER_INFO"]
    base_url = request.host_url.rstrip("/")

    body = generate_device_xml(config, server_info, base_url)

    return Response(
        body,
        mimetype=XML_MIMETYPE,
        content_type=f"{XML_MIMETYPE}; charset={UTF8_CHARSET}",
    )


def lineup_m3u() -> Response:
    """Return the channel lineup as an M3U playlist."""
    tablo_client: TabloClient = current_app.config["TABLO_CLIENT"]
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
    tablo_client: TabloClient = current_app.config["TABLO_CLIENT"]
    channels = tablo_client.get_channels()
    base_url = request.host_url.rstrip("/")

    return generate_json(channels, base_url)


def lineup_xml() -> Response:
    """Return the channel lineup as HDHomeRun-style XML."""
    tablo_client: TabloClient = current_app.config["TABLO_CLIENT"]
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
    tablo_client: TabloClient = current_app.config["TABLO_CLIENT"]
    channels: list[Channel] = tablo_client.get_channels()
    airings: list[Airing] = tablo_client.get_airings()

    body = generate_xmltv(channels, airings)

    return Response(
        body,
        mimetype=XML_MIMETYPE,
        content_type=f"{XML_MIMETYPE}; charset={UTF8_CHARSET}",
    )


def watch(channel_id: int) -> Response:
    """Redirect to a live stream for the given channel."""
    tablo_client: TabloClient = current_app.config["TABLO_CLIENT"]
    channel_path = f"/guide/channels/{channel_id}"

    playlist_url = tablo_client.get_watch_url(channel_path)

    return Response(status=302, headers={"Location": playlist_url})
