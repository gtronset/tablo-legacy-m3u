"""Main module."""

from tablo_legacy_m3u.app import app
from tablo_legacy_m3u.config import load_config


def main() -> None:
    """Start the application."""
    config = load_config()
    app.config["APP_CONFIG"] = config

    app.run(host=config.host, port=config.port)
