import os

from datasette import hookimpl
from datasette.permissions import Action
from datasette.plugins import pm
from pathlib import Path
from . import hookspecs
from .internal_migrations import internal_migrations
from sqlite_utils import Database
import json

from datasette_vite import vite_entry, vite_js_urls, vite_css_urls

try:
    from datasette_sidebar.hookspecs import SidebarApp

    _has_sidebar = True
except ImportError:
    _has_sidebar = False

from .router import PERMISSION_ACCESS_NAME, PERMISSION_READONLY_NAME
from .internal_db import author_from_request

# Ensure route decorators fire
from .routes import api, pages  # noqa: F401
from .router import router

_ = (api, pages)

pm.add_hookspecs(hookspecs)

SCHEMA = (Path(__file__).parent / "schema.sql").read_text()

VITE_DEV_PATH = os.environ.get("DATASETTE_COMMENTS_VITE_DEV")


@hookimpl
def extra_template_vars(datasette):
    entry = vite_entry(
        datasette=datasette,
        plugin_package="datasette_comments",
        vite_dev_path=VITE_DEV_PATH,
    )
    return {"datasette_comments_vite_entry": entry}


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


if _has_sidebar:

    @hookimpl
    def datasette_sidebar_apps(datasette):
        return [
            SidebarApp(
                label="Comments",
                description="Comment threads and activity",
                href="/-/datasette-comments/activity",
                icon='<svg viewBox="0 -960 960 960" fill="currentColor"><path d="M80-80v-720q0-33 23.5-56.5T160-880h640q33 0 56.5 23.5T880-800v480q0 33-23.5 56.5T800-240H240L80-80Zm126-240h594v-480H160v525l46-45Zm-46 0v-480 480Z"/></svg>',
                color="#276890",
            ),
        ]


@hookimpl
def menu_links(datasette, actor):
    async def inner():
        if await datasette.allowed(
            action=PERMISSION_ACCESS_NAME, actor=actor
        ) or await datasette.allowed(action=PERMISSION_READONLY_NAME, actor=actor):
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
    ) or await datasette.allowed(action=PERMISSION_READONLY_NAME, actor=request.actor):
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


CONTENT_SCRIPT_ENTRYPOINT = "src/content_script/index.tsx"


@hookimpl
def extra_css_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if not await should_inject_content_script(datasette, request, view_name):
            return []
        return vite_css_urls(
            datasette=datasette,
            entrypoint=CONTENT_SCRIPT_ENTRYPOINT,
            plugin_package="datasette_comments",
            vite_dev_path=VITE_DEV_PATH,
        )

    return inner


@hookimpl
def extra_js_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if not await should_inject_content_script(datasette, request, view_name):
            return []
        return vite_js_urls(
            datasette=datasette,
            entrypoint=CONTENT_SCRIPT_ENTRYPOINT,
            plugin_package="datasette_comments",
            vite_dev_path=VITE_DEV_PATH,
        )

    return inner
