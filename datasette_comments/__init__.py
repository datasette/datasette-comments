from datasette import hookimpl
from datasette.permissions import Action
from datasette.plugins import pm
from pathlib import Path
from . import hookspecs
from .internal_migrations import internal_migrations
from sqlite_utils import Database
import json

from .router import PERMISSION_ACCESS_NAME, PERMISSION_READONLY_NAME
from .internal_db import author_from_request

# Ensure route decorators fire
from .routes import api  # noqa: F401
from .routes import pages  # noqa: F401
from .router import router

pm.add_hookspecs(hookspecs)

SCHEMA = (Path(__file__).parent / "schema.sql").read_text()


@hookimpl
def register_actions(datasette):
    return [
        Action(
            name=PERMISSION_ACCESS_NAME,
            description=(
                "Can write and create datasette-comments threads, comments and reactions."
            ),
        ),
        Action(
            name=PERMISSION_READONLY_NAME,
            description="Can read datasette-comments threads, comments and reactions.",
        ),
    ]


@hookimpl
def menu_links(datasette, actor):
    async def inner():
        if await datasette.allowed(
            action=PERMISSION_ACCESS_NAME, actor=actor
        ) or await datasette.allowed(
            action=PERMISSION_READONLY_NAME, actor=actor
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
    return router.routes()


@hookimpl
async def startup(datasette):
    def migrate(connection):
        db = Database(connection)
        internal_migrations.apply(db)

    await datasette.get_internal_database().execute_write_fn(migrate)


SUPPORTED_VIEWS = ("index", "database", "table", "row")


async def should_inject_content_script(datasette, request, view_name):
    if not request:
        return False
    if await datasette.allowed(
        action=PERMISSION_ACCESS_NAME, actor=request.actor
    ) or await datasette.allowed(
        action=PERMISSION_READONLY_NAME, actor=request.actor
    ):
        return view_name in SUPPORTED_VIEWS
    return False


@hookimpl
async def extra_body_script(
    template, database, table, columns, view_name, request, datasette
):
    if await should_inject_content_script(datasette, request, view_name):
        author = await author_from_request(datasette, request)
        meta = json.dumps(
            {
                "view_name": view_name,
                "database": database,
                "table": table,
                "author": author.model_dump(),
                "readonly_viewer": await datasette.allowed(
                    action=PERMISSION_READONLY_NAME, actor=request.actor
                ),
            }
        )
        return f"window.DATASETTE_COMMENTS_META = {meta}"
    return ""


@hookimpl
def extra_js_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if await should_inject_content_script(datasette, request, view_name):
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
        if await should_inject_content_script(datasette, request, view_name):
            return [
                datasette.urls.path(
                    "/-/static-plugins/datasette-comments/content_script/index.min.css"
                )
            ]
        return []

    return inner
