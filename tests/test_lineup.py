"""Tests for the lineup generators."""

from tablo_legacy_m3u.lineup import (
    channel_number,
    generate_json,
    generate_m3u,
    generate_xml,
    sort_channels,
)
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


class TestSortChannels:
    """Tests for sort_channels()."""

    def test_sorts_by_major_then_minor(self) -> None:
        channels = [
            make_channel(300, "WNBC", 28, 1),
            make_channel(100, "WABC", 7, 1),
            make_channel(200, "WCBS", 2, 1),
        ]

        result = sort_channels(channels)

        assert (
            result[0]["object_id"] == 200  # noqa: PLR2004, Value here is more readable raw.
        )  # 2.1
        assert (
            result[1]["object_id"] == 100  # noqa: PLR2004, Value here is more readable raw.
        )  # 7.1
        assert (
            result[2]["object_id"] == 300  # noqa: PLR2004, Value here is more readable raw.
        )  # 28.1

    def test_empty_list(self) -> None:
        assert sort_channels([]) == []


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


class TestGenerateJson:
    """Tests for generate_json()."""

    def test_empty_channels(self) -> None:
        assert generate_json([], BASE_URL) == []

    def test_entry_has_required_fields(self) -> None:
        channels = [make_channel(100, "WABC", 7, 1)]

        result = generate_json(channels, BASE_URL)

        entry = result[0]
        assert entry["GuideNumber"] == "7.1"
        assert entry["GuideName"] == "WABC"
        assert entry["URL"] == f"{BASE_URL}/watch/100"

    def test_sorted_by_channel_number(self) -> None:
        channels = [
            make_channel(200, "WCBS", 11, 1),
            make_channel(100, "WABC", 7, 1),
        ]

        result = generate_json(channels, BASE_URL)

        assert result[0]["GuideNumber"] == "7.1"
        assert result[1]["GuideNumber"] == "11.1"


class TestGenerateXml:
    """Tests for `generate_xml()`."""

    def test_empty_channels(self) -> None:
        result = generate_xml([], BASE_URL)

        assert "<Lineup />" in result or "<Lineup/>" in result

    def test_single_channel(self) -> None:
        channels = [make_channel(100, "WABC", 7, 1)]

        result = generate_xml(channels, BASE_URL)

        assert "<GuideNumber>7.1</GuideNumber>" in result
        assert "<GuideName>WABC</GuideName>" in result
        assert f"<URL>{BASE_URL}/watch/100</URL>" in result

    def test_has_xml_declaration(self) -> None:
        result = generate_xml([], BASE_URL)

        assert result.startswith("<?xml")

    def test_sorted_by_channel_number(self) -> None:
        channels = [
            make_channel(200, "WCBS", 11, 1),
            make_channel(100, "WABC", 7, 1),
        ]

        result = generate_xml(channels, BASE_URL)

        # 7.1 should appear before 11.1 in the output
        position_of_channel_7 = result.index("<GuideNumber>7.1</GuideNumber>")
        position_of_channel_11 = result.index("<GuideNumber>11.1</GuideNumber>")
        assert position_of_channel_7 < position_of_channel_11

    def test_ends_with_newline(self) -> None:
        result = generate_xml([], BASE_URL)

        assert result.endswith("\n")
