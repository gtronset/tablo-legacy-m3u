"""Flask application for serving HDHomeRun-compatible endpoints."""

from flask import Flask, current_app, request

app = Flask(__name__)


@app.route("/discover.json")
def discover() -> dict[str, str | int]:
    """Return HDHomeRun-style device descriptor."""
    config = current_app.config["APP_CONFIG"]

    request_host = request.host_url.rstrip("/")

    return {
        "FriendlyName": config.device_name,
        "Manufacturer": config.device_name,
        "ModelNumber": "HDTC-2US",
        "FirmwareVersion": "0.1.0",
        "DeviceID": config.device_id,
        "DeviceAuth": config.device_name,
        "BaseURL": request_host,
        "LineupURL": f"{request_host}/lineup.json",
        "TunerCount": 2,
    }
