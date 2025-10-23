import json
from pathlib import Path
from dataclasses import asdict
from datasette import hookimpl, Permission
from datasette.plugins import pm
from sqlite_utils import Database
from . import hookspecs
from .routes import (
    Routes,
    author_from_request,
    PERMISSION_ACCESS_NAME,
    PERMISSION_READONLY_NAME,
)
from .internal_migrations import internal_migrations
from datasette.permissions import Action
from datasette.resources import TableResource

pm.add_hookspecs(hookspecs)

SCHEMA = (Path(__file__).parent / "schema.sql").read_text()


@hookimpl
def register_permissions(datasette):
    return [
        Permission(
            name=PERMISSION_ACCESS_NAME,
            abbr=None,
            description="Can write and create datasette-comments threads, comments and reactions.",
            takes_database=False,
            takes_resource=False,
            default=False,
        ),
        Permission(
            name=PERMISSION_READONLY_NAME,
            abbr=None,
            description="Can read datasette-comments threads, comments and reactions.",
            takes_database=False,
            takes_resource=False,
            default=False,
        ),
    ]


@hookimpl
def menu_links(datasette, actor):
    async def inner():
        if await datasette.permission_allowed(
            actor, PERMISSION_ACCESS_NAME, default=False
        ) or await datasette.permission_allowed(
            actor, PERMISSION_READONLY_NAME, default=False
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
        (r"^/-/datasette-comments/api/thread/new$", Routes.api_thread_new),
        (
            r"^/-/datasette-comments/api/thread/comments/(?P<thread_id>.*)$",
            Routes.api_thread_comments,
        ),
        (r"^/-/datasette-comments/api/thread/comment/add$", Routes.api_comment_new),
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
        (r"^/-/datasette-comments/activity$", Routes.activity_view),
        (r"^/-/datasette-comments/api/activity_search$", Routes.activity_search),
    ]


@hookimpl
async def startup(datasette):
    def migrate(connection):
        db = Database(connection)
        internal_migrations.apply(db)

    await datasette.get_internal_database().execute_write_fn(migrate)


SUPPORTED_VIEWS = ("index", "database", "table", "row")


async def should_inject_content_script2(datasette, database, table, actor):
    return await datasette.allowed(
        action=VIEW_COMMENTS_ACTION.name, 
        resource=TableResource(database=database, table=table), 
        actor=actor
    )


async def should_inject_content_script(datasette, request, view_name):
    if not request:
        return False
    if await datasette.permission_allowed(
        request.actor, PERMISSION_ACCESS_NAME, default=False
    ) or await datasette.permission_allowed(
        request.actor, PERMISSION_READONLY_NAME, default=False
    ):
        return view_name in SUPPORTED_VIEWS
    return False


@hookimpl
async def extra_body_script(
    template, database, table, columns, view_name, request, datasette
):
    if await should_inject_content_script2(datasette, database, table, request.actor):
        # if await should_inject_content_script(datasette, request, view_name):
        author = await author_from_request(datasette, request)
        meta = json.dumps(
            {
                "view_name": view_name,
                "database": database,
                "table": table,
                "author": asdict(author),
                "readonly_viewer": await datasette.permission_allowed(
                    request.actor, PERMISSION_READONLY_NAME, default=False
                ),
            }
        )
        return f"window.DATASETTE_COMMENTS_META = {meta}"
    return ""


@hookimpl
def extra_js_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if await should_inject_content_script2(datasette, database, table, request.actor):
            return [
                datasette.urls.path(
                    "/-/static-plugins/datasette-comments/content_script/index.min.js"
                )
            ]
        return []

    return inner


@hookimpl
def extra_css_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if await should_inject_content_script2(datasette, database, table, request.actor):
            return [
                datasette.urls.path(
                    "/-/static-plugins/datasette-comments/content_script/index.min.css"
                )
            ]
        return []

    return inner

VIEW_COMMENTS_ACTION = Action(
    name="view-comments",
    abbr=None,
    description="Ability to view comments on a table",
    takes_parent=True,
    takes_child=False,
    resource_class=TableResource,
)

ADD_COMMENTS_ACTION = Action(
    name="add-comments",
    abbr=None,
    description="Ability to add comments to a table",
    takes_parent=True,
    takes_child=True,
    resource_class=TableResource,
)

@hookimpl
def register_actions(datasette):
    return [
        VIEW_COMMENTS_ACTION,
        ADD_COMMENTS_ACTION,
    ]
