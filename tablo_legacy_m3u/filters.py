"""Custom Jinja2 template filters."""

from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask


def localtime_filter(dt: datetime, tz: ZoneInfo) -> str:
    """Convert a UTC datetime to the given timezone and format for display."""
    return dt.astimezone(tz).strftime("%b %-d, %-I:%M %p %Z")


def register_filters(app: Flask) -> None:
    """Register custom Jinja2 filters on the Flask app."""
    app.template_filter("localtime")(localtime_filter)
