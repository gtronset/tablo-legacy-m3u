"""Shared test fixtures and factories."""

from tablo_legacy_m3u.tablo_types import Channel, EpisodeAiring


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


def make_episode_airing(
    object_id: int = 500,
    show_title: str = "Test Show",
    channel: Channel | None = None,
) -> EpisodeAiring:
    """Build an EpisodeAiring dict for testing."""
    if channel is None:
        channel = make_channel()

    return {
        "path": f"/guide/series/episodes/{object_id}",
        "object_id": object_id,
        "series_path": "/guide/series/1000",
        "season_path": "/guide/series/seasons/1001",
        "episode": {
            "title": "Pilot",
            "description": "The first episode.",
            "number": 1,
            "season_number": 1,
            "orig_air_date": "2026-03-27",
        },
        "airing_details": {
            "datetime": "2026-03-28T01:00Z",
            "duration": 3600,
            "channel_path": channel["path"],
            "channel": channel,
            "show_title": show_title,
        },
        "qualifiers": ["new"],
    }
