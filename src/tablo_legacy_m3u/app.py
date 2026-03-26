"""Flask application for serving HDHomeRun-compatible endpoints."""

from typing import TYPE_CHECKING, Any

from flask import Flask, Response, current_app, request

from tablo_legacy_m3u.m3u import channel_number, generate_m3u

if TYPE_CHECKING:
    from tablo_legacy_m3u.config import Config
    from tablo_legacy_m3u.tablo_client import TabloClient
    from tablo_legacy_m3u.tablo_types import Channel, ServerInfo

app = Flask(__name__)


def _require_config(key: str) -> Any:
    """Get a required app config value or raise a clear error."""
    try:
        return current_app.config[key]
    except KeyError:
        msg = (
            f"Missing app config '{key}'. Start the app via '"
            "'python -m tablo_legacy_m3u'."
        )
        raise RuntimeError(msg) from None


@app.route("/discover.json")
def discover() -> dict[str, str | int]:
    """Return HDHomeRun-style device descriptor."""
    config: Config = _require_config("APP_CONFIG")
    server_info: ServerInfo = _require_config("TABLO_SERVER_INFO")

    friendly_name = config.device_name or server_info["name"]

    request_host = request.host_url.rstrip("/")

    return {
        "FriendlyName": friendly_name,
        "Manufacturer": "Tablo",
        "ModelNumber": server_info["model"]["name"],
        "FirmwareVersion": server_info["version"],
        "DeviceID": server_info["server_id"],
        "DeviceAuth": friendly_name,
        "BaseURL": request_host,
        "LineupURL": f"{request_host}/hdhr/lineup.json",
        "TunerCount": server_info["model"]["tuners"],
    }


@app.route("/lineup.m3u")
def lineup_m3u() -> Response:
    """Return the channel lineup as an M3U playlist."""
    tablo_client: TabloClient = _require_config("TABLO_CLIENT")
    channels: list[Channel] = tablo_client.get_channels()

    m3u_mimetype = "application/x-mpegurl"

    base_url = request.host_url.rstrip("/")
    body = generate_m3u(channels, base_url)

    return Response(
        body,
        mimetype=m3u_mimetype,
        content_type=f"{m3u_mimetype}; charset=utf-8",
    )


@app.route("/hdhr/lineup.json")
def lineup_json() -> list[dict[str, str]]:
    """Return the channel lineup in HDHomeRun JSON format."""
    tablo_client: TabloClient = _require_config("TABLO_CLIENT")
    channels = tablo_client.get_channels()

    base_url = request.host_url.rstrip("/")

    sorted_channels = sorted(
        channels,
        key=lambda c: (c["channel"]["major"], c["channel"]["minor"]),
    )

    return [
        {
            "Guide_ID": channel_number(ch),
            "GuideNumber": channel_number(ch),
            "GuideName": ch["channel"]["call_sign"],
            "Station": channel_number(ch),
            "URL": f"{base_url}/watch/{ch['object_id']}",
        }
        for ch in sorted_channels
    ]


@app.route("/hdhr/lineup_status.json")
def lineup_status() -> dict[str, str | int | list[str]]:
    """Return the lineup scan status."""
    return {
        "ScanInProgress": 0,
        "ScanPossible": 1,
        "Source": "Antenna",
        "SourceList": ["Antenna"],
    }


@app.route("/watch/<int:channel_id>")
def watch(channel_id: int) -> Response:
    """Redirect to a live stream for the given channel."""
    tablo_client: TabloClient = _require_config("TABLO_CLIENT")
    channel_path = f"/guide/channels/{channel_id}"

    playlist_url = tablo_client.get_watch_url(channel_path)

    return Response(status=302, headers={"Location": playlist_url})
