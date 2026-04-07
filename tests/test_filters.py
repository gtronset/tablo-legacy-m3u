"""Tests for Jinja filters."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from tablo_legacy_m3u.filters import localtime_filter


class TestLocaltimeFilter:
    """Tests the localtime Jinja filter converts UTC datetimes to a timezone/format."""

    def test_formats_datetime_in_timezone(self) -> None:
        dt = datetime(2025, 3, 15, 18, 30, tzinfo=UTC)
        tz = ZoneInfo("America/Chicago")

        result = localtime_filter(dt, tz)

        assert result == "Mar 15, 1:30 PM CDT"

    def test_utc_to_utc(self) -> None:
        dt = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)

        result = localtime_filter(dt, ZoneInfo("UTC"))

        assert result == "Jan 1, 12:00 AM UTC"
