from peewee import CharField, ForeignKeyField, AutoField
from models.base_model import BaseModel
from models.group import Group


class User(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField(max_length=30)
    spotify_username = CharField(unique=True)
    group = ForeignKeyField(Group, backref="members")
