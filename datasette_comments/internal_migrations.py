from sqlite_utils import Database
from sqlite_migrate import Migrations
from pathlib import Path

internal_migrations = Migrations("datasette-comments.internal")

SCHEMA = (Path(__file__).parent / "schema.sql").read_text()


@internal_migrations()
def m001_initial(db: Database):
    db.executescript(SCHEMA)
