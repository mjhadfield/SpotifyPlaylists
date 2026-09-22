"""Shared types every source module produces.

A source turns "some URL for a show/list" into a `SetlistData`: show metadata
plus an ordered list of songs to look up on Spotify. `app.py` and
`spotify_client.py` only ever deal with `SetlistData` / `SongQuery`, so a new
source just needs one function with this return shape - it doesn't need to
touch playlist creation at all.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SongQuery:
    """One song to look up on Spotify."""
    title: str
    artist: str
    # Set when the source flags this as a cover, e.g. `artist` is the
    # original performer rather than whoever played it at the show.
    is_cover_of: Optional[str] = None


@dataclass
class SetlistData:
    source_url: str
    artist: str
    venue: str
    date: str  # ISO yyyy-mm-dd
    songs: List[SongQuery] = field(default_factory=list)

    @property
    def playlist_name(self) -> str:
        return f"{self.artist} @ {self.venue} — {self.date}"
