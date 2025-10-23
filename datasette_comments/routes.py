from typing import List
from datasette import Response, Forbidden
from datasette.plugins import pm
from datasette.utils import await_me_maybe, tilde_decode, tilde_encode
from functools import wraps
from ulid import ULID
import hashlib
import json
from pydantic import TypeAdapter, ValidationError

from datasette_comments.actions import VIEW_COMMENTS_ACTION
from datasette_comments.internal_database import InternalDB
from . import comment_parser
from .contract import (
    ApiCommentNewParams,
    ApiThreadCommentsResponse,
    ApiThreadCommentsResponseItem,
    ApiThreadNewResponse,
    ApiThreadNewParams,
    Author,
)

# figured this would help with performance, to not hit label_column_for_table all the time?
cached_label_columns = {}


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


# wanted to use lru_cache here, but doesn't work with async
async def get_label_column(datasette, db: str, table: str):
    key = f"{db}/{table}"
    lookup = cached_label_columns.get(key)
    if lookup:
        return lookup
    result = await datasette.databases[db].label_column_for_table(table)
    cached_label_columns[key] = result
    return result


def gravtar_url(email: str):
    hash = hashlib.sha256(email.lower().encode()).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash}"


def author_from_actor(datasette, actors, actor_id) -> Author:
    enable_gravatar = (datasette.plugin_config("datasette-comments") or {}).get(
        "enable_gravatar"
    )
    actor = actors.get(actor_id)

    if actor is None:
        return Author(actor_id=actor_id, name="", profile_photo_url=None, username=None)

    name = actor.get("name") or ""
    profile_photo_url = actor.get("profile_picture_url")
    if profile_photo_url is None and enable_gravatar and actor.get("email"):
        profile_photo_url = gravtar_url(actor.get("email"))

    return Author(
        actor_id=actor_id,
        name=name,
        profile_photo_url=profile_photo_url,
        username=actor.get("username"),
    )


async def author_from_id(datasette, actor_id) -> Author:
    actors = await datasette.actors_from_ids([actor_id])
    # use the first key instead of actor_id, since it may be implicitly cast as a string
    # by some plugins (datasette-remote-actors)
    return author_from_actor(datasette, actors, actor_id)


async def author_from_request(datasette, request) -> Author:
    return await author_from_id(datasette, (request.actor or {}).get("id"))


async def actor_can_view_thread(datasette, actor, thread_id: str) -> bool:
    """Check if the given actor can view the given thread"""
    internal_db = InternalDB(datasette.get_internal_database())
    thread = await internal_db.get_thread_by_id(thread_id)

    allowed_actor_threads, params = await datasette.allowed_resources_sql(
        actor=actor, action=VIEW_COMMENTS_ACTION.name
    )
    print(allowed_actor_threads)
    sql = f"""
    WITH actor_allowed_tables(database_name, table_name) AS (
      {allowed_actor_threads}
    )
    SELECT 1
    FROM actor_allowed_tables
    WHERE database_name = :database_name
      AND table_name = :table_name
    LIMIT 1
    """
    params.update(
        {
            "database_name": thread.target_database,
            "table_name": thread.target_table,
        }
    )
    results = await datasette.get_internal_database().execute(sql, params)
    return len(results.rows) > 0


class Routes:
    @staticmethod
    async def api_thread_comments(datasette, request):
        """Retrieves all comments for a given thread"""
        # TODO make sure actor can see the thread target (db, table, etc.)
        thread_id = request.url_vars["thread_id"]

        if not await actor_can_view_thread(datasette, request.actor, thread_id):
            raise Forbidden("Actor cannot view this thread")

        items: List[ApiThreadCommentsResponseItem] = []
        internal_db = InternalDB(datasette.get_internal_database())
        comments = await internal_db.get_thread_comments(thread_id)

        actor_ids = set([comment.author_actor_id for comment in comments])
        actors = await datasette.actors_from_ids(list(actor_ids))

        for comment in comments:
            author = author_from_actor(datasette, actors, comment.author_actor_id)
            items.append(
                ApiThreadCommentsResponseItem(
                    id=comment.id,
                    author=author,
                    contents=comment.contents,
                    created_at=comment.created_at,
                    created_duration_seconds=comment.created_duration_seconds,
                    render_nodes=comment_parser.parse(comment.contents).rendered,
                    reactions=comment.reactions,
                )
            )

        return Response.json(
            ApiThreadCommentsResponse(
                ok=True, thread_id=thread_id, comments=items
            ).model_dump()
        )

    async def thread_mark_resolved(scope, receive, datasette, request):
        """Mark a thread as 'resolved'"""
        if request.method != "POST":
            return Response.text("", status=405)

        # TODO ensure only thread authors can resolve a thread?
        actor_id = request.actor.get("id")

        data = json.loads((await request.post_body()).decode("utf8"))
        thread_id = data.get("thread_id")
        await datasette.get_internal_database().execute_write(
            """
                UPDATE datasette_comments_threads
                SET resolved_at = datetime('now')
                WHERE id = ?
            """,
            (thread_id,),
            block=True,
        )

        return Response.json({"ok": True})

    async def api_thread_new(scope, receive, datasette, request):
        """Create a new thread on a 'target'"""
        if request.method != "POST":
            return Response.text("", status=405)

        actor_id = request.actor.get("id")

        try:
            body_data = json.loads((await request.post_body()).decode("utf8"))
            adapter = TypeAdapter(ApiThreadNewParams)
            params = adapter.validate_python(body_data)
        except ValidationError as e:
            # Extract the first error message to maintain similar error format
            errors = e.errors()
            if errors:
                first_error = errors[0]
                field = (
                    first_error.get("loc", [""])[0] if first_error.get("loc") else ""
                )
                msg = first_error.get("msg", "Validation error")

                # Map Pydantic errors to original error messages
                type_val = body_data.get("type", "")
                if field == "table":
                    if type_val == "table":
                        return Response.json(
                            {
                                "message": "target type table requires 'database' and 'table' fields"
                            },
                            status=400,
                        )
                    elif type_val == "row":
                        return Response.json(
                            {
                                "message": "target type database requires 'database', 'table', and 'rowids' fields"
                            },
                            status=400,
                        )
                    elif type_val == "column":
                        return Response.json(
                            {
                                "message": "target type column requires 'database', 'table', and 'column' fields"
                            },
                            status=400,
                        )
                elif field == "database":
                    return Response.json(
                        {"message": "target type database requires 'database' field"},
                        status=400,
                    )
                elif field == "rowids":
                    if type_val == "row":
                        return Response.json(
                            {
                                "message": "target type database requires 'database', 'table', and 'rowids' fields"
                            },
                            status=400,
                        )
                elif field == "column":
                    if type_val == "column":
                        return Response.json(
                            {
                                "message": "target type column requires 'database', 'table', and 'column' fields"
                            },
                            status=400,
                        )

                # Fallback to generic error
                return Response.json({"message": msg}, status=400)
            return Response.json({"message": "Invalid request body"}, status=400)
        except json.JSONDecodeError:
            return Response.json({"message": "Invalid JSON"}, status=400)

        internal_db = InternalDB(datasette.get_internal_database())
        thread_id = await internal_db.create_new_thread(actor_id, params)
        return Response.json(
            ApiThreadNewResponse(ok=True, thread_id=thread_id).model_dump()
        )

    async def api_comment_new(scope, receive, datasette, request):
        """Add a comment to a pre-existing thread"""
        # TODO ensure actor has permission to view/comment the target

        if request.method != "POST":
            return Response.text("POST required", status=405)

        actor_id = request.actor.get("id")
        try:
            params: ApiCommentNewParams = ApiCommentNewParams.model_validate_json(
                await request.post_body()
            )
        except ValueError:
            return Response.json({"ok": False}, status=400)

        internal_id = InternalDB(datasette.get_internal_database())
        await internal_id.insert_comment(params.thread_id, actor_id, params.contents)
        return Response.json(
            {
                "ok": True,
            }
        )

    async def table_view_threads(scope, receive, datasette, request):
        """Retrieve all threads for a table view"""
        # TODO ensure actor has permission to view the table

        if request.method != "POST":
            return Response.text("POST required", status=405)

        data = json.loads((await request.post_body()).decode("utf8"))
        database = data.get("database")
        table = data.get("table")
        rowids_encoded: List[str] = data.get("rowids")
        rowids: List[List[str]] = []
        for rowid_encoded in rowids_encoded:
            parts = [tilde_decode(b) for b in rowid_encoded.split(",")]
            rowids.append(parts)

        response = await datasette.get_internal_database().execute(
            """
              select id
              from datasette_comments_threads
              where target_type == 'table'
                and target_database == ?1
                and target_table == ?2
                and not marked_resolved
           """,
            (database, table),
        )
        table_threads = [dict(row) for row in response.rows]

        response = await datasette.get_internal_database().execute(
            """
              select
                id,
                target_row_ids
              from datasette_comments_threads
              where target_type == 'row'
                and target_database == ?1
                and target_table == ?2
                and target_row_ids in (
                  select value
                  from json_each(?3)
                )
                and not marked_resolved
           """,
            (database, table, json.dumps(rowids)),
        )
        row_threads = [
            {
                "id": row["id"],
                "rowids": "/".join(
                    map(lambda x: tilde_encode(x), json.loads(row["target_row_ids"]))
                ),
            }
            for row in response.rows
        ]

        return Response.json(
            {
                "ok": True,
                "data": {
                    "table_threads": table_threads,
                    "column_threads": [],
                    "row_threads": row_threads,
                    "value_threads": [],
                },
            }
        )

    async def row_view_threads(scope, receive, datasette, request):
        """Retrieve all threads for a row view"""
        # TODO ensure actor has permission to view the row

        if request.method != "POST":
            return Response.text("POST required", status=405)

        data = json.loads((await request.post_body()).decode("utf8"))
        database = data.get("database")
        table = data.get("table")
        rowids_encoded: str = data.get("rowids")
        rowids = [tilde_decode(b) for b in rowids_encoded.split(",")]

        response = await datasette.get_internal_database().execute(
            """
              select
                id
              from datasette_comments_threads
              where target_type == 'row'
                and target_database == ?1
                and target_table == ?2
                and target_row_ids = ?3
                and not marked_resolved
           """,
            (database, table, json.dumps(rowids)),
        )
        row_threads = [row["id"] for row in response.rows]

        return Response.json(
            {
                "ok": True,
                "data": {
                    "row_threads": row_threads,
                },
            }
        )

    async def reactions(scope, receive, datasette, request):
        """Retrieve reactions data for a specific comment"""
        # TODO permissions
        comment_id = request.url_vars["comment_id"]

        results = await datasette.get_internal_database().execute(
            """
              SELECT
                reactor_actor_id,
                reaction
              FROM datasette_comments_reactions
              WHERE comment_id == :comment_id
            """,
            {"comment_id": comment_id},
        )
        return Response.json([dict(row) for row in results.rows])

    async def reaction_add(scope, receive, datasette, request):
        """Add a reaction to a specific comment"""
        # TODO permissions
        if request.method != "POST":
            return Response.text("POST required", status=405)

        data = json.loads((await request.post_body()).decode("utf8"))

        id = str(ULID()).lower()
        comment_id = data.get("comment_id")
        reactor_actor_id = request.actor.get("id")
        reaction = data.get("reaction")

        # TODO better error messages
        if any(value is None for value in (comment_id, reactor_actor_id, reaction)):
            return Response.json({}, status=400)

        await datasette.get_internal_database().execute_write(
            """
              INSERT INTO datasette_comments_reactions(
                id,
                comment_id,
                reactor_actor_id,
                reaction
              )
              VALUES (
                :id,
                :comment_id,
                :reactor_actor_id,
                :reaction
              )
            """,
            {
                "id": id,
                "comment_id": comment_id,
                "reactor_actor_id": reactor_actor_id,
                "reaction": reaction,
            },
            block=True,
        )
        return Response.json({"ok": True})

    async def reaction_remove(scope, receive, datasette, request):
        """Remove a reaction"""
        # TODO permissions
        if request.method != "POST":
            return Response.text("POST required", status=405)

        data = json.loads((await request.post_body()).decode("utf8"))

        comment_id = data.get("comment_id")
        reactor_actor_id = request.actor.get("id")
        reaction = data.get("reaction")

        # TODO better error messages
        if any(value is None for value in (comment_id, reactor_actor_id, reaction)):
            return Response.json({}, status=400)

        await datasette.get_internal_database().execute_write(
            """
              DELETE FROM datasette_comments_reactions
              WHERE comment_id = :comment_id
                AND reactor_actor_id = :reactor_actor_id
                AND reaction = :reaction
            """,
            {
                "comment_id": comment_id,
                "reactor_actor_id": reactor_actor_id,
                "reaction": reaction,
            },
            block=True,
        )
        return Response.json({"ok": True})

    async def activity_view(scope, receive, datasette, request):
        """The HTML Activity page view"""
        return Response.html(
            await datasette.render_template(
                "activity_view.html",
                request=request,
            )
        )

    async def autocomplete_mentions(scope, receive, datasette, request):
        """Return a list of users that can be at-mentioned, for a autcomplete list"""
        prefix = request.args.get("prefix")
        suggestions = []
        for users in pm.hook.datasette_comments_users(datasette=datasette):
            for user in await await_me_maybe(users):
                username = user.get("username")
                if username and username.startswith(prefix):
                    suggestions.append(
                        {
                            "username": user.get("username"),
                            "author": (
                                await author_from_id(datasette, user.get("id"))
                            ).model_dump(),
                        }
                    )
        return Response.json({"suggestions": suggestions})

    async def activity_search(scope, receive, datasette, request):
        """Search endpoint for the acitivity page."""
        search_comments = request.args.get("searchComments")
        author = request.args.get("author")
        database = request.args.get("database")
        table = request.args.get("table")
        is_resolved = request.args.get("isResolved") == "1"
        contains_tag = request.args.getlist("containsTag")

        WHERE = "1"
        params = []

        # when provided, searchComments adds a `LIKE '%query%'` constraint
        if search_comments:
            WHERE += " AND comments.contents LIKE printf('%%%s%%', ?)"
            params.append(search_comments)

        if author:
            # author is the "username", need to resolve the actor_id from it
            for users in pm.hook.datasette_comments_users(datasette=datasette):
                for user in await await_me_maybe(users):
                    if user.get("username") == author:
                        WHERE += " AND comments.author_actor_id = ?"
                        params.append(user.get("id"))
                        break
        if database:
            WHERE += " AND threads.target_database = ?"
            params.append(database)

        if table:
            WHERE += " AND threads.target_table = ?"
            params.append(table)

        WHERE += f" AND {'' if is_resolved else 'NOT'} threads.marked_resolved"

        for tag in contains_tag:
            if not tag:
                continue
            WHERE += " AND ? in (select value from json_each(comments.hashtags))"
            params.append(tag)

        allowed_actor_tables, p = await datasette.allowed_resources_sql(
            actor=request.actor, action="view-comments"
        )
        sql = f"""
        WITH actor_tables(database_name, table_name, reason) AS (
          {allowed_actor_tables}
        ),
        final as (
          SELECT
            comments.author_actor_id,
            comments.contents,
            comments.created_at,
            (strftime('%s', 'now') - strftime('%s', comments.created_at)) as created_duration_seconds,
            threads.target_type,
            threads.target_database,
            threads.target_table,
            threads.target_row_ids,
            threads.target_column
          FROM datasette_comments_comments AS comments
          LEFT JOIN datasette_comments_threads AS threads ON threads.id = comments.thread_id
          LEFT JOIN actor_tables ON threads.target_database = actor_tables.database_name
            AND threads.target_table = actor_tables.table_name
          WHERE 
            threads.target_type = 'row'
            AND actor_tables.database_name IS NOT NULL
            AND actor_tables.table_name IS NOT NULL
            AND {WHERE}
          ORDER BY comments.created_at DESC
          LIMIT 100
        )
        select * from final;
        """
        results = await datasette.get_internal_database().execute(sql, params)
        data = [dict(row) for row in results.rows]
        author = await author_from_request(datasette, request)

        actor_ids = set(row["author_actor_id"] for row in data)
        actors = await datasette.actors_from_ids(actor_ids)

        # augment the rows with extra metadata
        for row in data:
            author = author_from_actor(datasette, actors, row["author_actor_id"])
            row["author"] = author.model_dump()

            # if there's a "label column" for the table, then resolve the "label" for the row
            label_column = await get_label_column(
                datasette, row["target_database"], row["target_table"]
            )
            if label_column:
                try:
                    rowids = json.loads(row["target_row_ids"])
                except Exception:
                    row["target_label"] = None
                    continue

                target_label = await get_label_for_row(
                    datasette.databases[row["target_database"]],
                    row["target_table"],
                    label_column,
                    rowids,
                )
                row["target_label"] = target_label
            else:
                row["target_label"] = None

        return Response.json({"data": data})
