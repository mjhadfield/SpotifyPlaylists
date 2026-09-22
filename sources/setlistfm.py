"""setlist.fm source: turns a setlist.fm page URL into a SetlistData.

Uses setlist.fm's public REST API (https://api.setlist.fm/docs/1.0/index.html)
rather than scraping the HTML page - the page URL already embeds the setlist
ID, so we just need that ID to ask the API for structured data directly.
"""
import os
import re
import time
from datetime import datetime

import requests

from . import SetlistData, SongQuery

API_BASE = "https://api.setlist.fm/rest/1.0"

# setlist.fm URLs end in "...-<8-char-hex-id>.html", e.g.
# ".../first-direct-bank-arena-leeds-england-434cc7e7.html" -> "434cc7e7"
_ID_RE = re.compile(r"-([0-9a-fA-F]{7,8})\.html(?:$|\?)")


class SetlistFMError(Exception):
    """Raised for anything that stops us turning a URL into song data."""


def _extract_setlist_id(url: str) -> str:
    match = _ID_RE.search(url)
    if not match:
        raise SetlistFMError(
            f"Couldn't find a setlist ID in that URL: {url}"
        )
    return match.group(1)


def fetch_setlist(url: str) -> SetlistData:
    api_key = os.environ.get("SETLISTFM_API_KEY")
    if not api_key:
        raise SetlistFMError(
            "SETLISTFM_API_KEY is not set - copy .env.example to .env and add your key."
        )

    setlist_id = _extract_setlist_id(url)

    # setlist.fm's free tier throttles bursts of requests with a bare 403
    # (indistinguishable from a bad key) - one short-backoff retry smooths
    # over that without mislabeling it as a config problem.
    attempts = 2
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(
                f"{API_BASE}/setlist/{setlist_id}",
                headers={"x-api-key": api_key, "Accept": "application/json"},
                timeout=15,
            )
        except requests.RequestException as e:
            raise SetlistFMError(f"Couldn't reach setlist.fm: {e}") from e

        if resp.status_code == 403 and attempt < attempts:
            time.sleep(2)
            continue
        break

    if resp.status_code == 404:
        raise SetlistFMError(f"No setlist found for ID {setlist_id}.")
    if resp.status_code == 403:
        raise SetlistFMError(
            "setlist.fm rejected the request - either SETLISTFM_API_KEY is wrong, "
            "or you're being rate-limited (try again in a few seconds)."
        )
    resp.raise_for_status()
    data = resp.json()

    artist_name = data.get("artist", {}).get("name", "Unknown Artist")

    venue = data.get("venue", {})
    venue_name = venue.get("name", "Unknown Venue")
    city_name = venue.get("city", {}).get("name")
    venue_label = f"{venue_name}, {city_name}" if city_name else venue_name

    raw_date = data.get("eventDate")  # setlist.fm format: "dd-MM-yyyy"
    try:
        date = datetime.strptime(raw_date, "%d-%m-%Y").strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        date = raw_date or "unknown-date"

    songs = []
    for set_ in data.get("sets", {}).get("set", []):
        for song in set_.get("song", []):
            name = (song.get("name") or "").strip()
            if not name or song.get("tape"):
                # Skip blank entries and intro/outro tape - not real songs to search for.
                continue
            cover_artist = song.get("cover", {}).get("name")
            songs.append(
                SongQuery(
                    title=name,
                    artist=cover_artist if cover_artist else artist_name,
                    is_cover_of=cover_artist,
                )
            )

    return SetlistData(
        source_url=data.get("url", url),
        artist=artist_name,
        venue=venue_label,
        date=date,
        songs=songs,
    )
