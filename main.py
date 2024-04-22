from gevent import monkey
from gevent.pywsgi import WSGIServer
monkey.patch_all()

import os
import random

import gevent
from flask import Flask, redirect, session, request, render_template, abort
from requests_oauthlib import OAuth2Session
from time import sleep
from models.user import User

from consts import CLIENT_ID, CLIENT_SECRET, CALLBACK_URL, SECRET_KEY, PORT
from models.group import Group
from models.song import Song
from models.base_model import db

db.create_tables([Group, User, Song])

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

app = Flask(__name__)
app.secret_key = SECRET_KEY


def get_it_no_cap(user_session: OAuth2Session) -> dict:
    response = user_session.get("https://api.spotify.com/v1/me")
    if response.status_code == 429:
        if int(response.headers["Retry-After"]) > 40:
            raise Exception(f"Rate limit to big: {response.headers['Retry-After']}")
        sleep(int(response.headers["Retry-After"]) + 0.5)
        return get_it_no_cap(user_session)
    return response.json()


def token_updater(token):
    pass


def make_session(token=None, state=None):
    return OAuth2Session(
        client_id=CLIENT_ID,
        token=token,
        state=state,
        scope=["user-read-playback-state", "user-read-private",
               "user-read-email", "playlist-read-private", "user-top-read"],
        redirect_uri=CALLBACK_URL,
        auto_refresh_kwargs={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
        },
        auto_refresh_url="https://accounts.spotify.com/api/token",
        token_updater=token_updater)

@app.route("/join")
def join():
    return render_template("join.html")

@app.route('/authorize')
def authorize_spotify():
    if request.args.get("gr"):
        session["group"] = request.args.get("gr")
    else:
        abort(400, "No group")
    if request.args.get("uname"):
        session["uname"] = request.args.get("uname")
    else:
        abort(400, "No name")
    s = make_session()
    authorization_url, state = s.authorization_url("https://accounts.spotify.com/authorize")
    session["spotify_state"] = state
    return redirect(authorization_url)


@app.route('/auth/callback')
def spotify_callback():
    if request.values.get('error'):
        return render_template("error.html")
    try:
        token = make_session(state=session.get('oauth2_state')).fetch_token(
            "https://accounts.spotify.com/api/token",
            client_secret=CLIENT_SECRET,
            authorization_response=request.url)
    except Exception as e:
        print(e)
        return "Authorization failed, please try again."
    if session.get("group") is None or session["group"] == "":
        return "No group specified."
    identity = get_it_no_cap(make_session(token=token))
    check_for_or_create_user(identity, session.get("uname"), session.get("group"), make_session(token=token))
    if identity:
        return redirect("/done")


@app.route("/done")
def done():
    return render_template("done.html")


def check_for_or_create_user(identity, name, group, token):
    u = User.get_or_none(spotify_username=identity["id"])
    if u:
        abort(400, "Du har redan registrerat dig!")
        return
    if not group.isnumeric():
        abort(400, "Inte giltig grupp")
        return
    gr = int(group)
    group_db = Group.get_or_none(group_number=gr)
    if group_db is None:
        abort(400, f"{gr} är inte en giltig grupp.")
        return

    u = User.create(name=name, spotify_username=identity["id"], group=group_db)
    mb = MusicBackfill(token, u)
    gevent.Greenlet.spawn(mb.start_backfill)
    return u


class MusicBackfill:
    def __init__(self, session, user):
        self.s = session
        self.u = user

    def start_backfill(self):
        tracks = fetch_track_data_until_it_works_no_cap(self.s)
        for t in tracks:
            sp_id, term = t
            Song.create(spotify_track_id=sp_id, user=self.u, term=term)


def get_for_term_no_cap(user_session: OAuth2Session, term: str, retries: int = 20):
    if retries < 0:
        return []
    tracks = user_session.get(f"https://api.spotify.com/v1/me/top/tracks?time_range={term}")
    if tracks.status_code == 200:
        return tracks
    else:
        if tracks.status_code == 429:
            gevent.sleep(int(tracks.headers["Retry-After"]) + random.uniform(1, 3))
        return get_for_term_no_cap(user_session, term, retries-1)


def fetch_track_data_until_it_works_no_cap(user_session: OAuth2Session, retries: int = 7) -> list:
    if retries < 0:
        return []
    all_tracks = []
    tracks_short = get_for_term_no_cap(user_session, "short_term")
    tracks_medium = get_for_term_no_cap(user_session, "medium_term")
    tracks_long = get_for_term_no_cap(user_session, "long_term")
    for t in tracks_short.json().get("items", []):
        all_tracks.append((t["uri"], "short"))
    for t in tracks_medium.json().get("items", []):
        all_tracks.append((t["uri"], "medium"))
    for t in tracks_long.json().get("items", []):
        all_tracks.append((t["uri"], "long"))
    if len(all_tracks) == 0:
        return fetch_track_data_until_it_works_no_cap(user_session, retries-1)
    return all_tracks


if __name__ == "__main__":
    LISTEN = ('0.0.0.0', PORT)

    http_server = WSGIServer(LISTEN, app)
    http_server.serve_forever()
