"""Main module."""

from tablo_legacy_m3u.app import app


def main() -> None:
    """Start the application."""
    app.run(host="0.0.0.0", port=5004)  # noqa: S104
