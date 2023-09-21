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

pm.add_hookspecs(hookspecs)

SCHEMA = (Path(__file__).parent / "schema.sql").read_text()


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


class Routes:
    async def thread_comments(scope, receive, datasette, request):
        # TODO make sure actor can see the thread target (db, table, etc.)
        thread_id = request.url_vars["thread_id"]

        results = await datasette.get_internal_database().execute(
            """
              select
                id,
                author_actor_id,
                created_at,
                contents
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
        return Response.json({"ok": True, "data": rows})

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

    async def debug_view(scope, receive, datasette, request):
        return Response.html(await datasette.render_template("debug.html"))

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
              *
            FROM threads_with_tags
            LEFT JOIN datasette_comments_threads ON datasette_comments_threads.id = threads_with_tags.thread_id
            WHERE NOT marked_resolved


        """,
            {"tag": tag},
        )
        return Response.json([dict(row) for row in results.rows])


@hookimpl
def register_routes():
    return [
        (r"^/-/datasette-comments/thread/new$", Routes.thread_new),
        (
            r"^/-/datasette-comments/thread/comments/(?P<thread_id>.*)$",
            Routes.thread_comments,
        ),
        (r"^/-/datasette-comments/thread/comment/add$", Routes.comment_add),
        (r"^/-/datasette-comments/threads/table_view$", Routes.table_view_threads),
        (r"^/-/datasette-comments/threads/mark_resolved$", Routes.thread_mark_resolved),
        (r"^/-/datasette-comments/debug$", Routes.debug_view),
        (r"^/-/datasette-comments/tags/(?P<tag>.*)$", Routes.tag_view),
    ]


@hookimpl
async def startup(datasette):
    await datasette.get_internal_database().execute_write_script(SCHEMA)


@hookimpl
def register_permissions(datasette):
    return [
        Permission(
            name="comments-admin",
            abbr=None,
            description="View the admin page for datasette-coments.",
            takes_database=False,
            takes_resource=False,
            default=False,
        ),
        Permission(
            name="comments-create",
            abbr=None,
            description="Ability to create a short link,",
            takes_database=False,
            takes_resource=False,
            default=False,
        ),
    ]


@hookimpl
def permission_allowed(actor, action):
    pass


@hookimpl
def menu_links(datasette, actor):
    async def inner():
        if await datasette.permission_allowed(actor, "comments-admin", default=False):
            return [
                {
                    "href": datasette.urls.path("/-/datasette-comments/admin"),
                    "label": "datasette-comments Admin Page",
                },
            ]

    return inner


@hookimpl
async def extra_body_script(
    template, database, table, columns, view_name, request, datasette
):
    # TODO only include if actor can make comments
    if view_name in ("index", "database", "table", "row"):
        meta = json.dumps(
            {
                "view_name": view_name,
                "database": database,
                "table": table,
            }
        )
        return f"window.DATASETTE_COMMENTS_META = {meta}"


@hookimpl
def extra_js_urls(template, database, table, columns, view_name, request, datasette):
    return [
        # TODO only include if actor can make comments
        datasette.urls.path(
            "/-/static-plugins/datasette-comments/content_script.min.js"
        )
    ]


@hookimpl
def extra_css_urls(template, database, table, columns, view_name, request, datasette):
    return [datasette.urls.path("/-/static-plugins/datasette-comments/style.css")]
