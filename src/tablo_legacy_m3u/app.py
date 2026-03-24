"""Flask application for serving HDHomeRun-compatible endpoints."""

from flask import Flask

app = Flask(__name__)


@app.route("/discover.json")
def discover() -> dict[str, str | int]:
    """Return HDHomeRun-style device descriptor."""
    return {
        "FriendlyName": "tablo-legacy-m3u",
        "Manufacturer": "tablo-legacy-m3u",
        "ModelNumber": "HDTC-2US",
        "FirmwareVersion": "0.1.0",
        "DeviceID": "12345678",
        "DeviceAuth": "tablo-legacy-m3u",
        "BaseURL": "http://localhost:5004",
        "LineupURL": "http://localhost:5004/lineup.json",
        "TunerCount": 2,
    }
