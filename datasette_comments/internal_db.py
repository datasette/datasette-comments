from typing import List, Optional
from ulid import ULID
from . import comment_parser
from .page_data import Author
import json
import hashlib


def insert_comment(thread_id: str, author_actor_id: str, contents: str):
    id = str(ULID()).lower()
    parsed = comment_parser.parse(contents)
    mentions = list(set(mention.value[1:] for mention in parsed.mentions))
    hashtags = list(set(mention.value[1:] for mention in parsed.tags))

    SQL = """
        INSERT INTO datasette_comments_comments(
          id,
          thread_id,
          author_actor_id,
          contents,
          mentions,
          hashtags,
          past_revisions
        )
        VALUES (
          :id,
          :thread_id,
          :author_actor_id,
          :contents,
          :mentions,
          :hashtags,
          json_array()
        )
    """
    params = {
        "id": id,
        "thread_id": thread_id,
        "author_actor_id": author_actor_id,
        "contents": contents,
        "mentions": json.dumps(mentions),
        "hashtags": json.dumps(hashtags),
    }

    return (SQL, params)


def gravatar_url(email: str):
    hash = hashlib.sha256(email.lower().encode()).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash}"


def author_from_actor(datasette, actors, actor_id) -> Author:
    enable_gravatar = (datasette.plugin_config("datasette-comments") or {}).get(
        "enable_gravatar"
    )
    actor = actors.get(actor_id)

    if actor is None:
        return Author(actor_id=actor_id, name="", profile_photo_url=None, username=None)

    name = actor.get("name")
    profile_photo_url = actor.get("profile_picture_url")
    if profile_photo_url is None and enable_gravatar and actor.get("email"):
        profile_photo_url = gravatar_url(actor.get("email"))

    return Author(
        actor_id=actor_id,
        name=name,
        profile_photo_url=profile_photo_url,
        username=actor.get("username"),
    )


async def author_from_id(datasette, actor_id) -> Author:
    actors = await datasette.actors_from_ids([actor_id])
    return author_from_actor(datasette, actors, actor_id)


async def author_from_request(datasette, request) -> Author:
    return await author_from_id(datasette, (request.actor or {}).get("id"))


# figured this would help with performance, to not hit label_column_for_table all the time?
cached_label_columns = {}


# wanted to use lru_cache here, but doesn't work with async
async def get_label_column(datasette, db: str, table: str):
    key = f"{db}/{table}"
    lookup = cached_label_columns.get(key)
    if lookup:
        return lookup
    result = await datasette.databases[db].label_column_for_table(table)
    cached_label_columns[key] = result
    return result


# Based on https://github.com/simonw/datasette/blob/452a587e236ef642cbc6ae345b58767ea8420cb5/datasette/utils/__init__.py#L1209
async def get_label_for_row(db, table: str, label_column: str, rowids: List[str]):
    if len(rowids) == 0:
        return None
    pks = await db.primary_keys(table)
    if len(pks) == 0:
        return None
    wheres = [f'"{pk}"=:p{i}' for i, pk in enumerate(pks)]
    sql = f"select [{label_column}] from [{table}] where {' AND '.join(wheres)} limit 1"
    params = {}
    for i, pk_value in enumerate(rowids):
        params[f"p{i}"] = pk_value
    results = await db.execute(sql, params)
    row = results.first()
    if row is None:
        return None
    return row[label_column]
