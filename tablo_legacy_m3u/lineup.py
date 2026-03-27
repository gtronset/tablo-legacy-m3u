"""M3U playlist generator for Tablo channels."""

from xml.etree.ElementTree import (  # noqa: S405, This is only used for generating XML, not parsing untrusted input.
    Element,
    SubElement,
    tostring,
)

from tablo_legacy_m3u.tablo_types import Channel


def channel_number(channel: Channel) -> str:
    """Format the channel number as `major.minor`."""
    info = channel["channel"]

    return f"{info['major']}.{info['minor']}"


def sort_channels(channels: list[Channel]) -> list[Channel]:
    """Sort channels by major then minor number."""
    return sorted(
        channels,
        key=lambda channel: (channel["channel"]["major"], channel["channel"]["minor"]),
    )


def generate_m3u(channels: list[Channel], base_url: str) -> str:
    """Generate a sorted M3U playlist from a list of Tablo channels.

    For M3U format details, see https://en.wikipedia.org/wiki/M3U.

    Args:
        channels: Hydrated channel objects from the Tablo API.
        base_url: The base URL of this server (e.g., "http://localhost:5004").

    Returns:
        A complete M3U playlist string.
    """
    m3u_header = "#EXTM3U"
    live_stream_duration = -1

    lines = [m3u_header]

    for channel in sort_channels(channels):
        info = channel["channel"]
        channel_num = channel_number(channel)
        object_id = channel["object_id"]

        lines.append(
            f'#EXTINF:{live_stream_duration} channel-id="{channel_num}" channel-number='
            f'"{channel_num}" tvg-name="{info["call_sign"]}" tvg-chno="{channel_num}"'
            f",{info['call_sign']}"
        )
        lines.append(f"{base_url}/watch/{object_id}")

    return "\n".join(lines) + "\n"


def generate_json(channels: list[Channel], base_url: str) -> list[dict[str, str]]:
    """Generate an HDHomeRun-style JSON lineup from a list of Tablo channels."""
    return [
        {
            "Guide_ID": channel_number(channel),
            "GuideNumber": channel_number(channel),
            "GuideName": channel["channel"]["call_sign"],
            "Station": channel_number(channel),
            "URL": f"{base_url}/watch/{channel['object_id']}",
        }
        for channel in sort_channels(channels)
    ]


def generate_xml(channels: list[Channel], base_url: str) -> str:
    """Generate an HDHomeRun-style XML lineup from a list of Tablo channels.

    Args:
        channels: Hydrated channel objects from the Tablo API.
        base_url: The base URL of this server (e.g., "http://localhost:5004").

    Returns:
        An XML string with a `<Lineup>` root element.
    """
    root = Element("Lineup")

    for channel in sort_channels(channels):
        program = SubElement(root, "Program")
        SubElement(program, "GuideNumber").text = channel_number(channel)
        SubElement(program, "GuideName").text = channel["channel"]["call_sign"]
        SubElement(program, "URL").text = f"{base_url}/watch/{channel['object_id']}"

    return tostring(root, encoding="unicode", xml_declaration=True) + "\n"
