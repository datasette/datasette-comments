from typing import List
from ulid import ULID
from . import comment_parser
from .page_data import Author
import json

from datasette_user_profiles.routes.pages import get_profile


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


async def author_from_profile(datasette, actor_id) -> Author:
    """Build an Author from datasette-user-profiles data."""
    profile = await get_profile(datasette, actor_id)
    photo_url = f"/-/profile/pic/{actor_id}" if profile.has_photo else None
    return Author(
        actor_id=actor_id,
        name=profile.display_name or actor_id,
        profile_photo_url=photo_url,
        username=actor_id,
    )


async def authors_from_actor_ids(datasette, actor_ids) -> dict[str, Author]:
    """Build Author objects for multiple actor IDs."""
    result = {}
    for actor_id in actor_ids:
        result[actor_id] = await author_from_profile(datasette, actor_id)
    return result


async def author_from_request(datasette, request) -> Author:
    actor_id = (request.actor or {}).get("id")
    if not actor_id:
        return Author(actor_id="", name="", profile_photo_url=None, username=None)
    return await author_from_profile(datasette, actor_id)


# figured this would help with performance, to not hit label_column_for_table all the time?
cached_label_columns = {}


# wanted to use lru_cache here, but doesn't work with async
async def get_label_column(datasette, db: str, table: str):
    key = f"{db}/{table}"
    lookup = cached_label_columns.get(key)
    if lookup:
        return lookup
    if db not in datasette.databases:
        return None
    try:
        result = await datasette.databases[db].label_column_for_table(table)
    except Exception:
        return None
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
