import os

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, redirect, render_template, request, url_for

import spotify_client
from sources.setlistfm import SetlistFMError, fetch_setlist

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")


@app.route("/")
def index():
    auth_manager = spotify_client.get_auth_manager()
    if not spotify_client.is_authenticated(auth_manager):
        return render_template(
            "index.html", authenticated=False, auth_url=auth_manager.get_authorize_url()
        )
    return render_template("index.html", authenticated=True)


@app.route("/callback")
def callback():
    auth_manager = spotify_client.get_auth_manager()
    code = request.args.get("code")
    if code:
        auth_manager.get_access_token(code, as_dict=False)
    return redirect(url_for("index"))


@app.route("/create", methods=["POST"])
def create():
    auth_manager = spotify_client.get_auth_manager()
    if not spotify_client.is_authenticated(auth_manager):
        return redirect(url_for("index"))

    setlist_url = request.form.get("setlist_url", "").strip()
    if not setlist_url:
        return render_template("index.html", authenticated=True, error="Please paste a setlist.fm URL.")

    try:
        setlist = fetch_setlist(setlist_url)
    except SetlistFMError as e:
        return render_template("index.html", authenticated=True, error=str(e))

    if not setlist.songs:
        return render_template(
            "index.html", authenticated=True, error="No songs found in that setlist."
        )

    sp = spotify_client.get_client(auth_manager)
    playlist_url, matched, unmatched = spotify_client.create_playlist_from_tracks(
        sp,
        name=setlist.playlist_name,
        description=f"Auto-generated from {setlist.source_url}",
        songs=setlist.songs,
    )

    return render_template(
        "result.html",
        playlist_name=setlist.playlist_name,
        playlist_url=playlist_url,
        matched=matched,
        unmatched=unmatched,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8888, debug=True)
