"""Flask application for serving HDHomeRun-compatible endpoints."""

from flask import Flask, current_app, request

app = Flask(__name__)


@app.route("/discover.json")
def discover() -> dict[str, str | int]:
    """Return HDHomeRun-style device descriptor."""
    config = current_app.config["APP_CONFIG"]
    server_info = current_app.config["TABLO_SERVER_INFO"]

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
        "LineupURL": f"{request_host}/lineup.json",
        "TunerCount": server_info["model"]["tuners"],
    }
