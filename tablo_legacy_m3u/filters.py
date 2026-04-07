"""Custom Jinja2 template filters."""

from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from flask import Flask

if TYPE_CHECKING:
    from tablo_legacy_m3u.config import Config


def localtime_filter(dt: datetime, tz: ZoneInfo) -> str:
    """Convert a UTC datetime to the given timezone and format for display."""
    local = dt.astimezone(tz)
    hour = local.hour % 12 or 12
    return f"{local:%b} {local.day}, {hour}:{local:%M} {local:%p} {local:%Z}"


def register_filters(app: Flask) -> None:
    """Register custom Jinja2 filters on the Flask app."""
    app.template_filter("localtime")(localtime_filter)

    @app.context_processor
    def inject_tz() -> dict[str, ZoneInfo]:
        config: Config = app.config["APP_CONFIG"]
        return {"tz": config.tz}
