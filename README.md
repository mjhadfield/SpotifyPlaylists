# Setlist → Spotify Playlist Generator

Paste a setlist.fm link into a small local web page; get back a Spotify
playlist with that show's songs, in the order they were played.

## How it works

1. **setlist.fm** ([`sources/setlistfm.py`](sources/setlistfm.py)) - pulls the
   setlist ID out of the page URL and calls the [setlist.fm REST
   API](https://api.setlist.fm/docs/1.0/index.html) for structured data
   (artist, venue, date, ordered songs). Cover songs are searched under the
   original artist; intro/outro "tape" entries are skipped.
2. **Spotify** ([`spotify_client.py`](spotify_client.py)) - via
   [spotipy](https://spotipy.readthedocs.io/), logs you into your Spotify
   account once (OAuth), searches each song, and creates a new private
   playlist named `"{artist} @ {venue} — {date}"` with everything it could
   match. Anything it couldn't confidently match is reported back instead of
   guessed at.

Every source module (`sources/*.py`) just needs to expose a function that
returns a `SetlistData` (see [`sources/__init__.py`](sources/__init__.py)) -
the Spotify side never needs to change to support a new source.

## Setup

### 1. Spotify app

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   and create an app.
2. In the app's settings, add this Redirect URI: `http://127.0.0.1:8888/callback`
3. Copy the app's **Client ID** and **Client Secret**.

### 2. setlist.fm API key

Apply for a free key at [api.setlist.fm](https://api.setlist.fm/) - approval
is near-instant.

### 3. Configure

```bash
cp .env.example .env
```

Fill in `.env` with your Spotify Client ID/Secret and setlist.fm API key.

### 4. Install & run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8888, log in with Spotify (first run only - the token
is cached in `.cache`), then paste a setlist.fm URL, e.g.:

```
https://www.setlist.fm/setlist/evanescence/2026/first-direct-bank-arena-leeds-england-434cc7e7.html
```

Each submission creates a brand new playlist - re-running against the same
URL makes a second, independent playlist rather than updating the first.
