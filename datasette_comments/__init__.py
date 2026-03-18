import os

from datasette import hookimpl
from datasette.permissions import Action
from datasette.plugins import pm
from pathlib import Path, PurePosixPath
from . import hookspecs
from .internal_migrations import internal_migrations
from sqlite_utils import Database
import json

from datasette_vite import vite_entry

from .router import PERMISSION_ACCESS_NAME, PERMISSION_READONLY_NAME
from .internal_db import author_from_request

# Ensure route decorators fire
from .routes import api, pages  # noqa: F401
from .router import router

_ = (api, pages)

pm.add_hookspecs(hookspecs)

SCHEMA = (Path(__file__).parent / "schema.sql").read_text()

VITE_DEV_PATH = os.environ.get("DATASETTE_COMMENTS_VITE_DEV")

# Load Vite manifest once at import time (production only)
_manifest = {}
_manifest_path = Path(__file__).parent / "manifest.json"
if _manifest_path.exists():
    _manifest = json.loads(_manifest_path.read_text())


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


CONTENT_SCRIPT_ENTRYPOINT = "src/content_script/index.tsx"


@hookimpl
def extra_css_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if not await should_inject_content_script(datasette, request, view_name):
            return []
        if VITE_DEV_PATH:
            return []
        chunk = _manifest.get(CONTENT_SCRIPT_ENTRYPOINT, {})
        return [
            datasette.urls.static_plugins(
                "datasette_comments",
                str(PurePosixPath(css).relative_to("static")),
            )
            for css in chunk.get("css", [])
        ]

    return inner


@hookimpl
def extra_js_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if not await should_inject_content_script(datasette, request, view_name):
            return []
        if VITE_DEV_PATH:
            return [
                {"url": f"{VITE_DEV_PATH}@vite/client", "module": True},
                {
                    "url": f"{VITE_DEV_PATH}{CONTENT_SCRIPT_ENTRYPOINT}",
                    "module": True,
                },
            ]
        chunk = _manifest.get(CONTENT_SCRIPT_ENTRYPOINT, {})
        file = chunk.get("file", "")
        if file:
            return [
                {
                    "url": datasette.urls.static_plugins(
                        "datasette_comments",
                        str(PurePosixPath(file).relative_to("static")),
                    ),
                    "module": True,
                }
            ]
        return []

    return inner
