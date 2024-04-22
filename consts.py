from os import environ

CLIENT_ID = environ["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = environ["SPOTIFY_CLIENT_SECRET"]
CALLBACK_URL = environ["CALLBACK_URL"]
SECRET_KEY = environ["WEB_SECRET"]
DATABASE_CONNECTION_URL = environ["DATABASE_URL"]
PORT = int(environ["PORT"])