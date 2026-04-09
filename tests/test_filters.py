"""Tests for Jinja filters."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from tablo_legacy_m3u.filters import bytes_to_gb_filter, localtime_filter


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


class TestBytesToGbFilter:
    """Tests the bytes_to_gb Jinja filter converts bytes to a GB string."""

    def test_converts_bytes_to_gb(self) -> None:
        result = bytes_to_gb_filter(1_000_000_000)  # exactly 1 GiB

        assert result == "1.0 GB"

    def test_rounds_to_one_decimal(self) -> None:
        result = bytes_to_gb_filter(1_500_000_000_000)

        assert result == "1500.0 GB"

    def test_zero_bytes(self) -> None:
        result = bytes_to_gb_filter(0)

        assert result == "0.0 GB"
