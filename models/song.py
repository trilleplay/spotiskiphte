from peewee import CharField, ForeignKeyField, AutoField
from models.base_model import BaseModel
from models.user import User


class Song(BaseModel):
    id = AutoField(primary_key=True)
    spotify_track_id = CharField()
    user = ForeignKeyField(User, backref="songs")
    term = CharField(max_length=10)