"""Shared test fixtures and factories."""

from tablo_legacy_m3u.tablo_types import Channel


def make_channel(
    object_id: int = 100,
    call_sign: str = "WABC",
    major: int = 7,
    minor: int = 1,
    network: str = "ABC",
) -> Channel:
    """Build a Channel dict for testing."""
    return {
        "object_id": object_id,
        "path": f"/guide/channels/{object_id}",
        "channel": {
            "call_sign": call_sign,
            "name": call_sign,
            "call_sign_src": "tms",
            "major": major,
            "minor": minor,
            "network": network,
            "flags": [],
            "resolution": "hd_1080",
            "favourite": False,
            "tms_station_id": "12345",
            "tms_affiliate_id": "67890",
            "channel_identifier": call_sign.lower(),
            "source": "antenna",
            "logos": [],
        },
    }
