"""Shared test fixtures and factories."""

from tablo_legacy_m3u.tablo_types import (
    Channel,
    EpisodeAiring,
    MovieAiring,
    SportEventAiring,
)


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


def make_movie_airing(
    object_id: int = 600,
    show_title: str = "Test Movie",
    channel: Channel | None = None,
    film_rating: str | None = "pg",
) -> MovieAiring:
    """Build a MovieAiring dict for testing."""
    if channel is None:
        channel = make_channel()

    return {
        "path": f"/guide/movies/airings/{object_id}",
        "object_id": object_id,
        "movie_path": f"/guide/movies/{object_id - 1}",
        "movie_airing": {
            "release_year": 2008,
            "film_rating": film_rating,
            "quality_rating": 6,
        },
        "airing_details": {
            "datetime": "2026-03-28T11:00Z",
            "duration": 5400,
            "channel_path": channel["path"],
            "channel": channel,
            "show_title": show_title,
        },
        "qualifiers": [],
    }


def make_sport_event_airing(
    object_id: int = 700,
    show_title: str = "Test Sports",
    channel: Channel | None = None,
) -> SportEventAiring:
    """Build a SportEventAiring dict for testing."""
    if channel is None:
        channel = make_channel()

    return {
        "path": f"/guide/sports/events/{object_id}",
        "object_id": object_id,
        "sport_path": f"/guide/sports/{object_id - 1}",
        "event": {
            "title": "Team A at Team B",
            "description": "From Test Arena in Test City.",
            "season": None,
            "season_type": None,
            "venue": "Test Arena",
            "teams": [
                {"name": "Team A", "team_id": 1001},
                {"name": "Team B", "team_id": 1002},
            ],
            "home_team_id": 1002,
        },
        "airing_details": {
            "datetime": "2026-03-28T17:00Z",
            "duration": 10800,
            "channel_path": channel["path"],
            "channel": channel,
            "show_title": show_title,
        },
        "qualifiers": ["live"],
    }
