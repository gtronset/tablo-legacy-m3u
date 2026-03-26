"""Tests for the M3U playlist generator."""

from tablo_legacy_m3u.m3u import channel_number, generate_m3u
from tests.helpers import make_channel

BASE_URL = "http://localhost:5004"


class TestChannelNumber:
    """Tests for channel_number()."""

    def test_major_and_minor_in_channel_number(self) -> None:
        channel = make_channel(100, "WABC", 7, 1)

        assert channel_number(channel) == "7.1"

    def test_double_digit_minor_in_channel_number(self) -> None:
        channel = make_channel(200, "WCBS", 2, 11)

        assert channel_number(channel) == "2.11"


class TestGenerateM3u:
    """Tests for `generate_m3u()`."""

    def test_empty_channels(self) -> None:
        result = generate_m3u([], BASE_URL)

        assert result == "#EXTM3U\n"

    def test_single_channel(self) -> None:
        channels = [make_channel(100, "WABC", 7, 1)]

        result = generate_m3u(channels, BASE_URL)

        lines = result.strip().split("\n")
        assert lines[0] == "#EXTM3U"
        assert 'tvg-name="WABC"' in lines[1]
        assert 'tvg-chno="7.1"' in lines[1]
        assert 'channel-id="7.1"' in lines[1]
        assert lines[1].endswith(",WABC")
        assert lines[2] == f"{BASE_URL}/watch/100"

    def test_sorted_by_channel_number(self) -> None:
        channels = [
            make_channel(300, "WNBC", 28, 1),
            make_channel(100, "WABC", 7, 1),
            make_channel(200, "WCBS", 2, 1),
        ]

        result = generate_m3u(channels, BASE_URL)

        lines = result.strip().split("\n")
        # Each channel produces 2 lines, after the header
        assert lines[2] == f"{BASE_URL}/watch/200"  # 2.1 first
        assert lines[4] == f"{BASE_URL}/watch/100"  # 7.1 second
        assert lines[6] == f"{BASE_URL}/watch/300"  # 28.1 third

    def test_minor_channel_sort_order(self) -> None:
        channels = [
            make_channel(101, "WABC-2", 7, 2),
            make_channel(100, "WABC", 7, 1),
        ]

        result = generate_m3u(channels, BASE_URL)

        lines = result.strip().split("\n")
        assert lines[2] == f"{BASE_URL}/watch/100"  # 7.1 before 7.2
        assert lines[4] == f"{BASE_URL}/watch/101"

    def test_ends_with_newline(self) -> None:
        result = generate_m3u([], BASE_URL)

        assert result.endswith("\n")

    def test_extinf_duration_is_negative_one(self) -> None:
        channels = [make_channel(100, "WABC", 7, 1)]

        result = generate_m3u(channels, BASE_URL)

        lines = result.strip().split("\n")
        assert lines[1].startswith("#EXTINF:-1 ")
