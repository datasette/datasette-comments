from typing import List, Optional
from datasette import hookimpl, Response, Permission, Forbidden
from datasette.utils import tilde_decode, tilde_encode
from datasette.plugins import pm
from pathlib import Path
from . import hookspecs
from . import comment_parser
from ulid import ULID
import json
from .internal_migrations import internal_migrations
from sqlite_utils import Database
from functools import wraps
import hashlib
from dataclasses import dataclass, asdict

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
                raise Forbidden("Permission denied for datasette-comments")
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
            author = author_from_actor(datasette, actors, row["author_actor_id"])
            row["author"] = asdict(author)

            results = comment_parser.parse(row["contents"])
            row["render_nodes"] = results.rendered
            row["reactions"] = json.loads(row["reactions"]) if row["reactions"] else []
        return Response.json({"ok": True, "data": rows})

    @check_permission()
    async def thread_mark_resolved(scope, receive, datasette, request):
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
                return Response.json(
                    {"message": "target type database requires 'database' field"},
                    status=400,
                )
        elif type == "table":
            if any(item is None for item in (database, table)):
                return Response.json(
                    {
                        "message": "target type table requires 'database' and 'table' fields"
                    },
                    status=400,
                )
        elif type == "row":
            if any(item is None for item in (database, table, rowids)):
                return Response.json(
                    {
                        "message": "target type database requires 'database', 'table', and 'rowids' fields"
                    },
                    status=400,
                )
        elif type == "column":
            if any(item is None for item in (database, table, column)):
                return Response.json(
                    {
                        "message": "target type column requires 'database', 'table', and 'column' fields"
                    },
                    status=400,
                )
            raise Exception("TODO column type not implmented")
        elif type == "value":
            if any(item is None for item in (database, table, column, rowids)):
                raise Exception(
                    "target type value requires 'database', 'table', 'column', and 'rowids' fields"
                )
            raise Exception("TODO value type not implmented")
        else:
            raise Exception(f"target type '{type}' not supported")

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
    async def row_view_threads(scope, receive, datasette, request):
        # TODO ensure actor has permission to view the row

        if request.method != "POST":
            return Response.text("POST required", status=405)

        data = json.loads((await request.post_body()).decode("utf8"))
        database = data.get("database")
        table = data.get("table")
        rowids_encoded: str = data.get("rowids")
        rowids = [tilde_decode(b) for b in rowids_encoded.split(",")]
        print(database, table, rowids, json.dumps(rowids))

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
        author = await author_from_request(datasette, request)
        return Response.html(
            await datasette.render_template(
                "tag_view.html",
                {
                    "data": data,
                    "author": asdict(author),
                    "tag": tag,
                },
                request=request,
            )
        )

    @check_permission()
    async def activity_view(scope, receive, datasette, request):
        return Response.html(
            await datasette.render_template(
                "activity_view.html",
                request=request,
            )
        )

    @check_permission()
    async def autocomplete_mentions(scope, receive, datasette, request):
        prefix = request.args.get("prefix")
        suggestions = []
        for users in pm.hook.datasette_comments_users():
            for user in users:
                username = user.get("username")
                if username and username.startswith(prefix):
                    suggestions.append(
                        {
                            "username": user.get("username"),
                            "author": asdict(
                                await author_from_id(datasette, user.get("id"))
                            ),
                        }
                    )
        return Response.json({"suggestions": suggestions})

    @check_permission()
    async def activity_search(scope, receive, datasette, request):
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
            for users in pm.hook.datasette_comments_users():
                for user in users:
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

        sql = f"""
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
              WHERE {WHERE}
              ORDER BY comments.created_at DESC
              LIMIT 100;
        """
        results = await datasette.get_internal_database().execute(sql, params)
        data = [dict(row) for row in results.rows]
        author = await author_from_request(datasette, request)

        actor_ids = set(row["author_actor_id"] for row in data)
        actors = await datasette.actors_from_ids(actor_ids)

        # augment the rows with extra metadata
        for row in data:
            author = author_from_actor(datasette, actors, row["author_actor_id"])
            row["author"] = asdict(author)

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
def menu_links(datasette, actor):
    async def inner():
        if await datasette.permission_allowed(
            actor, PERMISSION_ACCESS_NAME, default=False
        ):
            return [
                {
                    "href": datasette.urls.path("/-/datasette-comments/activity"),
                    "label": "Comments",
                },
            ]

    return inner


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
        (r"^/-/datasette-comments/api/threads/row_view$", Routes.row_view_threads),
        (
            r"^/-/datasette-comments/api/threads/mark_resolved$",
            Routes.thread_mark_resolved,
        ),
        # API reactions
        (r"^/-/datasette-comments/api/reaction/add$", Routes.reaction_add),
        (r"^/-/datasette-comments/api/reaction/remove$", Routes.reaction_remove),
        (r"^/-/datasette-comments/api/reactions/(?P<comment_id>.*)$", Routes.reactions),
        # autocomplete helper on drafts
        (
            r"^/-/datasette-comments/api/autocomplete/mentions$",
            Routes.autocomplete_mentions,
        ),
        # views
        (r"^/-/datasette-comments/tags/(?P<tag>.*)$", Routes.tag_view),
        (r"^/-/datasette-comments/activity$", Routes.activity_view),
        (r"^/-/datasette-comments/api/activity_search$", Routes.activity_search),
    ]


@hookimpl
async def startup(datasette):
    def migrate(connection):
        db = Database(connection)
        internal_migrations.apply(db)

    await datasette.get_internal_database().execute_write_fn(migrate)


def gravtar_url(email: str):
    hash = hashlib.sha256(email.lower().encode()).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash}"


@dataclass
class Author:
    # the actor.id value for the author
    actor_id: str

    # Sourced from actor object key "name"
    name: str

    # Sourced from actor object key "profile_photo_url"
    # OR the gravatar URL from key "email", if enable_gravatar
    # is on.
    profile_photo_url: Optional[str]

    # the username is used for at-mentions. Should be unique to other actors
    username: Optional[str]


def author_from_actor(datasette, actors, actor_id) -> Author:
    enable_gravatar = (datasette.plugin_config("datasette-comments") or {}).get(
        "enable_gravatar"
    )
    actor = actors.get(actor_id)

    if actor is None:
        return Author(actor_id, "", None, None)

    name = actor.get("name")
    profile_photo_url = actor.get("profile_picture_url")
    if profile_photo_url is None and enable_gravatar and actor.get("email"):
        profile_photo_url = gravtar_url(actor.get("email"))

    return Author(actor_id, name, profile_photo_url, actor.get("username"))


async def author_from_id(datasette, actor_id) -> Author:
    actors = await datasette.actors_from_ids([actor_id])
    return author_from_actor(datasette, actors, actor_id)


async def author_from_request(datasette, request) -> Author:
    return await author_from_id(datasette, (request.actor or {}).get("id"))


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
        author = await author_from_request(datasette, request)
        meta = json.dumps(
            {
                "view_name": view_name,
                "database": database,
                "table": table,
                "author": asdict(author),
            }
        )
        return f"window.DATASETTE_COMMENTS_META = {meta}"
    return ""


async def should_inject_content_script(datasette, request, view_name):
    if not request or not await datasette.permission_allowed(
        request.actor, PERMISSION_ACCESS_NAME, default=False
    ):
        return False
    return view_name in SUPPORTED_VIEWS


@hookimpl
def extra_js_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if should_inject_content_script(datasette, request, view_name):
            return [
                datasette.urls.path(
                    "/-/static-plugins/datasette-comments/content_script.min.js"
                )
            ]
        return []

    return inner


@hookimpl
def extra_css_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if should_inject_content_script(datasette, request, view_name):
            return [
                datasette.urls.path(
                    "/-/static-plugins/datasette-comments/content_script.min.css"
                )
            ]
        return []

    return inner
