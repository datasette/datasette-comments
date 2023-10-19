from typing import Any, List
from datasette import hookimpl, Response, Permission, Forbidden
from datasette.utils import tilde_decode, tilde_encode
from datasette.plugins import pm
from pathlib import Path
from . import hookspecs
from . import comment_parser
from datasette.plugins import pm
from ulid import ULID
import json
from .internal_migrations import internal_migrations
from sqlite_utils import Database
from functools import wraps
import hashlib

pm.add_hookspecs(hookspecs)

SCHEMA = (Path(__file__).parent / "schema.sql").read_text()

PERMISSION_ACCESS_NAME = "datasette-comments-access"


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

# decorator for routes, to ensure the proper permissions are checked
def check_permission():
    def decorator(func):
        @wraps(func)
        async def wrapper(scope, receive, datasette, request):
            result = await datasette.permission_allowed(
                request.actor, PERMISSION_ACCESS_NAME, default=False
            )
            if not result:
                raise Forbidden(f"Permission denied for datasette-comments")
            return await func(scope, receive, datasette, request)

        return wrapper

    return decorator


class Routes:
    @check_permission()
    async def thread_comments(scope, receive, datasette, request):
        # TODO make sure actor can see the thread target (db, table, etc.)
        thread_id = request.url_vars["thread_id"]

        results = await datasette.get_internal_database().execute(
            """
              select
                id,
                author_actor_id,
                created_at,
                (strftime('%s', 'now') - strftime('%s', created_at)) as created_duration_seconds,
                contents,
                (
                  select json_group_array(
                    json_object(
                      'reactor_actor_id', reactor_actor_id,
                      'reaction', reaction
                    )
                  )
                  from datasette_comments_reactions
                  where comment_id == datasette_comments_comments.id
                ) as reactions
              from datasette_comments_comments
              where thread_id = ?
              order by created_at
            """,
            (thread_id,),
        )

        actor_ids = set()
        rows = []
        for row in results:
            actor_ids.add(row["author_actor_id"])
            rows.append(dict(row))
        actors = await datasette.actors_from_ids(list(actor_ids))
        for row in rows:
            actor = actors.get(row["author_actor_id"])
            row["author_profile_picture"] = actor.get("profile_picture_url")
            row["author_name"] = actor.get("name")

            results = comment_parser.parse(row["contents"])
            row["render_nodes"] = results.rendered
            row["reactions"] = json.loads(row["reactions"]) if row["reactions"] else []
        return Response.json({"ok": True, "data": rows})

    @check_permission()
    async def thread_mark_resolved(scope, receive, datasette, request):
        # TODO ensure only thread authors can resolve a thread?
        if request.method != "POST":
            return Response.text("", status=405)

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

    @check_permission()
    async def thread_new(scope, receive, datasette, request):
        if request.method != "POST":
            return Response.text("", status=405)

        actor_id = request.actor.get("id")

        data = json.loads((await request.post_body()).decode("utf8"))
        type = data.get("type")
        database = data.get("database")
        table = data.get("table")
        column = data.get("column")
        rowids = data.get("rowids")
        comment = data.get("comment")

        # validate the target is good, depending on type
        if type == "database":
            if database is None:
                return Response.json({"message": "TODO"}, status=400)
        elif type == "table":
            if any(item is None for item in (database, table)):
                return Response.json({"message": "TODO"}, status=400)
        elif type == "column":
            if any(item is None for item in (database, table, column)):
                return Response.json({"message": "TODO"}, status=400)
            raise Exception("TODO")
        elif type == "row":
            if any(item is None for item in (database, table, rowids)):
                return Response.json({"message": "TODO"}, status=400)
        elif type == "value":
            if any(item is None for item in (database, table, column, rowids)):
                raise Exception("TODO")
        else:
            raise Exception("TODO handle wrong type")

        # the urls input is a tilde-encoded string, so we split into indivudal primary keys here
        if rowids is not None:
            rowids = [tilde_decode(b) for b in rowids.split(",")]

        id = str(ULID()).lower()

        def db_thread_new(conn):
            cursor = conn.cursor()
            cursor.execute("begin")
            params = {
                "id": id,
                "creator_actor_id": actor_id,
                "target_type": type,
                "target_database": database,
                "target_table": table if type != "database" else None,
                "target_column": column if type in ("column", "row", "value") else None,
                "target_row_ids": json.dumps(rowids)
                if type in ("row", "value")
                else None,
            }

            cursor.execute(
                """
                  insert into datasette_comments_threads(
                    id,
                    creator_actor_id,
                    target_type,
                    target_database,
                    target_table,
                    target_column,
                    target_row_ids
                  )
                  values (
                    :id,
                    :creator_actor_id,
                    :target_type,
                    :target_database,
                    :target_table,
                    :target_column,
                    :target_row_ids
                  );
                """,
                params,
            )
            thread_id = cursor.execute(
                "select id from datasette_comments_threads where rowid = ?",
                (cursor.lastrowid,),
            ).fetchone()[0]

            cursor.execute(*(insert_comment(thread_id, actor_id, comment)))
            cursor.execute("commit")
            return thread_id

        try:
            thread_id = await datasette.get_internal_database().execute_write_fn(
                db_thread_new,
                block=True,
            )
            return Response.json({"ok": True, "thread_id": thread_id})
        except Exception as e:
            raise e
            return Response.json({"ok": False})

    @check_permission()
    async def comment_add(scope, receive, datasette, request):
        # TODO ensure actor has permission to view/comment the target

        if request.method != "POST":
            return Response.text("POST required", status=405)

        actor_id = request.actor.get("id")

        data = json.loads((await request.post_body()).decode("utf8"))
        thread_id = data.get("thread_id")
        contents = data.get("contents")

        await datasette.get_internal_database().execute_write(
            *(insert_comment(thread_id, actor_id, contents)),
            block=True,
        )

        return Response.json(
            {
                "ok": True,
            }
        )

    @check_permission()
    async def table_view_threads(scope, receive, datasette, request):
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

    @check_permission()
    async def reactions(scope, receive, datasette, request):
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

    @check_permission()
    async def reaction_add(scope, receive, datasette, request):
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

    @check_permission()
    async def reaction_remove(scope, receive, datasette, request):
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

    @check_permission()
    async def tag_view(scope, receive, datasette, request):
        tag = request.url_vars["tag"]
        results = await datasette.get_internal_database().execute(
            """
            WITH threads_with_tags AS (
              SELECT distinct thread_id
              FROM datasette_comments_comments
              WHERE (
                SELECT 1
                FROM json_each(hashtags)
                WHERE value = :tag
              )
            )
            SELECT
              thread_id,
              target_type,
              target_database,
              target_table,
              target_row_ids,
              target_column,
              marked_resolved
            FROM threads_with_tags
            LEFT JOIN datasette_comments_threads ON datasette_comments_threads.id = threads_with_tags.thread_id
            WHERE NOT marked_resolved


        """,
            {"tag": tag},
        )
        data = [dict(row) for row in results.rows]
        actor_id, profile_photo_url = await author_from_request(datasette, request)
        return Response.html(
            await datasette.render_template(
                "tag_view.html",
                {
                    "data": data,
                    "actor_id": actor_id,
                    "profile_photo_url": profile_photo_url,
                    "tag": tag,
                },
            )
        )
    @check_permission()
    async def activity_view(scope, receive, datasette, request):
        results = await datasette.get_internal_database().execute(
            """
              SELECT
                comments.author_actor_id,
                comments.contents,
                comments.created_at,
                threads.target_type,
                threads.target_database,
                threads.target_table,
                threads.target_row_ids,
                threads.target_column
              FROM datasette_comments_comments AS comments
              LEFT JOIN datasette_comments_threads AS threads ON threads.id = comments.thread_id
              WHERE NOT threads.marked_resolved
              ORDER BY comments.created_at DESC
              LIMIT 100;
        """,
        )
        data = [dict(row) for row in results.rows]
        actor_id, profile_photo_url = await author_from_request(datasette, request)

        actor_ids = set(row["author_actor_id"] for row in data)
        actors = await datasette.actors_from_ids(actor_ids)
        for row in data:
            row["author_actor"] = actors.get(row["author_actor_id"])

        return Response.html(
            await datasette.render_template(
                "activity_view.html",
                {
                    "data": data,
                    "actor_id": actor_id,
                    "profile_photo_url": profile_photo_url,
                },
            )
        )


@hookimpl
def register_permissions(datasette):
    return [
        Permission(
            name=PERMISSION_ACCESS_NAME,
            abbr=None,
            description="Can access datasette-comments features.",
            takes_database=False,
            takes_resource=False,
            default=False,
        )
    ]


@hookimpl
def register_routes():
    return [
        # API thread/comment operations
        (r"^/-/datasette-comments/api/thread/new$", Routes.thread_new),
        (
            r"^/-/datasette-comments/api/thread/comments/(?P<thread_id>.*)$",
            Routes.thread_comments,
        ),
        (r"^/-/datasette-comments/api/thread/comment/add$", Routes.comment_add),
        (r"^/-/datasette-comments/api/threads/table_view$", Routes.table_view_threads),
        (
            r"^/-/datasette-comments/api/threads/mark_resolved$",
            Routes.thread_mark_resolved,
        ),
        # API reactions
        (r"^/-/datasette-comments/api/reaction/add$", Routes.reaction_add),
        (r"^/-/datasette-comments/api/reaction/remove$", Routes.reaction_remove),
        (r"^/-/datasette-comments/api/reactions/(?P<comment_id>.*)$", Routes.reactions),
        # views
        (r"^/-/datasette-comments/tags/(?P<tag>.*)$", Routes.tag_view),
        (r"^/-/datasette-comments/activity$", Routes.activity_view),
    ]


@hookimpl
async def startup(datasette):
    def migrate(connection):
        db = Database(connection)
        internal_migrations.apply(db)

    await datasette.get_internal_database().execute_write_fn(migrate)


@hookimpl
def register_permissions(datasette):
    return [
        Permission(
            name="comments-create",
            abbr=None,
            description="Ability to create a short link,",
            takes_database=False,
            takes_resource=False,
            default=False,
        ),
    ]


def gravtar_url(email:str):
    hash = hashlib.sha256(email.lower().encode()).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash}"

async def author_from_request(datasette, request):
    enable_gravatar = (datasette.plugin_config("datasette-comments") or {}).get("enable_gravatar")
    actor_id = (request.actor or {}).get("id")
    if actor_id:
        actors = await datasette.actors_from_ids([actor_id])
        actor = actors.get(actor_id) or {}
        profile_photo_url = actor.get("profile_picture_url")
        if profile_photo_url is None and enable_gravatar and actor.get("email"):
            profile_photo_url = gravtar_url(actor.get("email"))
    else:
        profile_photo_url = None
    return (actor_id, profile_photo_url)


SUPPORTED_VIEWS = ("index", "database", "table", "row")


@hookimpl
async def extra_body_script(
    template, database, table, columns, view_name, request, datasette
):
    if not request or not await datasette.permission_allowed(
        request.actor, PERMISSION_ACCESS_NAME, default=False
    ):
        return ""

    if view_name in SUPPORTED_VIEWS:
        actor_id, profile_photo_url = await author_from_request(datasette, request)
        meta = json.dumps(
            {
                "view_name": view_name,
                "database": database,
                "table": table,
                "actor_id": actor_id,
                "profile_photo_url": profile_photo_url,
            }
        )
        return f"window.DATASETTE_COMMENTS_META = {meta}"
    return ""


@hookimpl
def extra_js_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if not request or not await datasette.permission_allowed(
            request.actor, PERMISSION_ACCESS_NAME, default=False
        ):
            return []
        if view_name in SUPPORTED_VIEWS:
            return [
                # TODO only include if actor can make comments
                datasette.urls.path(
                    "/-/static-plugins/datasette-comments/content_script.min.js"
                )
            ]
        return []
    return inner


@hookimpl
def extra_css_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if not request or not await datasette.permission_allowed(
            request.actor, PERMISSION_ACCESS_NAME, default=False
        ):
            return []
        if view_name in SUPPORTED_VIEWS:
            return [datasette.urls.path("/-/static-plugins/datasette-comments/style.css")]
        return []

    return inner
