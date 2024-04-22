from models.base_model import BaseModel
from peewee import IntegerField, AutoField


class Group(BaseModel):
    id = AutoField(primary_key=True)
    group_number = IntegerField(unique=True)
