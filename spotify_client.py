"""Spotify side of the pipeline: auth, track search, playlist creation.

Deliberately knows nothing about setlist.fm or any other source - it only
consumes the shared `SongQuery` shape from `sources`, so it stays reusable
as-is when a second source is added.
"""
import os
from typing import List, Optional, Tuple

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from sources import SongQuery

SCOPE = "playlist-modify-public playlist-modify-private"
CACHE_PATH = ".cache"


def get_auth_manager() -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
        scope=SCOPE,
        cache_path=CACHE_PATH,
        open_browser=False,
    )


def is_authenticated(auth_manager: SpotifyOAuth) -> bool:
    return auth_manager.get_cached_token() is not None


def get_client(auth_manager: SpotifyOAuth) -> spotipy.Spotify:
    return spotipy.Spotify(auth_manager=auth_manager)


def _quote(value: str) -> str:
    # Quote as a phrase for Spotify's search syntax, escaping any embedded
    # quotes so a title like `She's "Gone"` can't break the query.
    return '"' + value.replace('"', "") + '"'


def _search_track(sp: spotipy.Spotify, song: SongQuery) -> Optional[dict]:
    query = f"track:{_quote(song.title)} artist:{_quote(song.artist)}"
    results = sp.search(q=query, type="track", limit=1)
    items = results.get("tracks", {}).get("items", [])
    if not items:
        # Fallback: loosen the query - field filters can miss on odd
        # punctuation/spacing between how setlist.fm and Spotify title things.
        results = sp.search(q=f"{song.title} {song.artist}", type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])
    return items[0] if items else None


def create_playlist_from_tracks(
    sp: spotipy.Spotify,
    name: str,
    description: str,
    songs: List[SongQuery],
) -> Tuple[str, List[dict], List[SongQuery]]:
    """Creates a new private playlist and adds every song it can match.

    Returns (playlist_url, matched, unmatched) where `matched` is a list of
    dicts describing what actually got added, and `unmatched` is the
    SongQuerys that had no confident Spotify match.
    """
    # NB: spotipy's user_playlist_create() posts to the now-blocked
    # /users/{user_id}/playlists endpoint (403s on current apps) - Spotify
    # requires /me/playlists instead, which current_user_playlist_create() uses.
    playlist = sp.current_user_playlist_create(name, public=False, description=description)

    matched = []
    unmatched = []
    for song in songs:
        track = _search_track(sp, song)
        if track:
            matched.append(
                {
                    "uri": track["uri"],
                    "title": track["name"],
                    "artist": ", ".join(a["name"] for a in track["artists"]),
                }
            )
        else:
            unmatched.append(song)

    uris = [t["uri"] for t in matched]
    for i in range(0, len(uris), 100):  # Spotify caps additions at 100 tracks per call
        sp.playlist_add_items(playlist["id"], uris[i : i + 100])

    return playlist["external_urls"]["spotify"], matched, unmatched
