from peewee import Model
from playhouse.db_url import connect
from consts import DATABASE_CONNECTION_URL

db = connect(DATABASE_CONNECTION_URL)


class BaseModel(Model):
    class Meta:
        database = db
