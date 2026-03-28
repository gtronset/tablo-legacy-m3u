"""XMLTV EPG generator from Tablo guide airings.

- For XMLTV format details, see https://wiki.xmltv.org/index.php/XMLTVFormat.
- For offical XMLTV DTD, see: https://github.com/XMLTV/xmltv/blob/master/xmltv.dtd
"""

from datetime import UTC, datetime, timedelta
from typing import TypeGuard
from xml.etree.ElementTree import (  # noqa: S405
    Element,
    SubElement,
    tostring,
)

from tablo_legacy_m3u.lineup import channel_number
from tablo_legacy_m3u.tablo_types import (
    Airing,
    Channel,
    EpisodeAiring,
    MovieAiring,
    SportEventAiring,
)

XMLTV_DATETIME_FORMAT = "%Y%m%d%H%M%S +0000"


def _xmltv_datetime(iso: str) -> str:
    """Convert an ISO 8601 UTC string to XMLTV datetime format.

    See: https://github.com/XMLTV/xmltv/blob/e5bb5b03bfe5433b7c66c06a188e895d3fc46ab6/xmltv.dtd#L132-L137

    Args:
        iso: A datetime string like `2026-03-28T01:00Z`.

    Returns:
        A string like `20260328010000 +0000`.
    """
    dt = datetime.fromisoformat(iso).replace(tzinfo=UTC)

    return dt.strftime(XMLTV_DATETIME_FORMAT)


def _stop_time(iso: str, duration: int) -> str:
    """Calculate the XMLTV stop time from a start time and duration.

    Args:
        iso: The airing start time in ISO 8601 UTC.
        duration: The airing duration in seconds.

    Returns:
        The stop time in XMLTV datetime format.
    """
    dt = datetime.fromisoformat(iso).replace(tzinfo=UTC)
    stop = dt + timedelta(seconds=duration)

    return stop.strftime(XMLTV_DATETIME_FORMAT)


def _channel_id(channel: Channel) -> str:
    """Return the XMLTV channel ID, matching the M3U tvg-id."""
    return channel_number(channel)


def _is_episode(airing: Airing) -> TypeGuard[EpisodeAiring]:
    """Check if the airing is a series episode."""
    return "episode" in airing


def _is_sport_event(airing: Airing) -> TypeGuard[SportEventAiring]:
    """Check if the airing is a sport event."""
    return "event" in airing


def _is_movie(airing: Airing) -> TypeGuard[MovieAiring]:
    """Check if the airing is a movie."""
    return "movie_airing" in airing


def _add_episode_details(programme: Element, airing: EpisodeAiring) -> None:
    """Add episode-specific sub-elements to a programme.

    Example output::

        <sub-title>Pilot</sub-title>
        <desc>The first episode.</desc>
        <episode-num system="onscreen">S1E1</episode-num>
    """
    episode = airing["episode"]

    if episode["title"]:
        SubElement(programme, "sub-title").text = episode["title"]

    SubElement(programme, "desc").text = episode["description"]

    season = episode["season_number"]
    number = episode["number"]

    if season > 0:
        SubElement(
            programme, "episode-num", system="onscreen"
        ).text = f"S{season}E{number}"


def _add_sport_event_details(programme: Element, airing: SportEventAiring) -> None:
    """Add sport event-specific sub-elements to a programme.

    Example output::

        <desc>From Place Bell in Laval-Ouest, Québec.</desc>
    """
    SubElement(programme, "desc").text = airing["event"]["description"]


def _add_movie_details(programme: Element, airing: MovieAiring) -> None:
    """Add movie-specific sub-elements to a programme.

    Example output::

        <rating><value>pg</value></rating>
    """
    movie_info = airing["movie_airing"]

    if movie_info["film_rating"]:
        rating_el = SubElement(programme, "rating")
        SubElement(rating_el, "value").text = movie_info["film_rating"]


def _add_programme(root: Element, airing: Airing) -> None:
    """Add a single <programme> element for any airing type.

    Example output::

        <programme start="20260328010000 +0000"
                   stop="20260328020000 +0000" channel="7.1">
          <title>Test Show</title>
          ...
        </programme>
    """
    details = airing["airing_details"]
    channel = details["channel"]

    programme = SubElement(
        root,
        "programme",
        start=_xmltv_datetime(details["datetime"]),
        stop=_stop_time(details["datetime"], details["duration"]),
        channel=_channel_id(channel),
    )

    SubElement(programme, "title").text = details["show_title"]

    if _is_episode(airing):
        _add_episode_details(programme, airing)
    elif _is_sport_event(airing):
        _add_sport_event_details(programme, airing)
    elif _is_movie(airing):
        _add_movie_details(programme, airing)


def generate_xmltv(channels: list[Channel], airings: list[Airing]) -> str:
    """Generate an XMLTV document from channels and guide airings.

    Example output::

        <?xml version='1.0' encoding='us-ascii'?>
        <tv generator-info-name="tablo-legacy-m3u">
          <channel id="7.1">
            <display-name>WABC</display-name>
            <display-name>7.1 WABC</display-name>
          </channel>
          <programme start="20260328010000 +0000"
                     stop="20260328020000 +0000" channel="7.1">
            <title>Test Show</title>
            ...
          </programme>
        </tv>

    Args:
        channels: Hydrated channel objects from the Tablo API.
        airings: Hydrated guide airings from the Tablo API.

    Returns:
        A complete XMLTV XML string.
    """
    root = Element(
        "tv",
        attrib={"generator-info-name": "tablo-legacy-m3u"},
    )

    for channel in channels:
        ch_id = _channel_id(channel)
        info = channel["channel"]

        ch_el = SubElement(root, "channel", id=ch_id)
        SubElement(ch_el, "display-name").text = info["call_sign"]
        SubElement(ch_el, "display-name").text = f"{ch_id} {info['call_sign']}"

    for airing in airings:
        _add_programme(root, airing)

    return tostring(root, encoding="unicode", xml_declaration=True) + "\n"
