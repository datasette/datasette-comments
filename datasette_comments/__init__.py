import json
from datasette import hookimpl
from datasette.plugins import pm
from datasette.resources import TableResource
from sqlite_utils import Database
from . import hookspecs
from .actions import VIEW_COMMENTS_ACTION, ADD_COMMENTS_ACTION
from . import routes as Routes
from .internal_migrations import internal_migrations

pm.add_hookspecs(hookspecs)


@hookimpl
def register_actions(datasette):
    return [
        VIEW_COMMENTS_ACTION,
        ADD_COMMENTS_ACTION,
    ]


@hookimpl
def menu_links(datasette, actor):
    async def inner():
        # TODO: only actors with permission to view any comments
        if True:
            return [
                {
                    "href": datasette.urls.path("/-/datasette-comments/activity"),
                    "label": "Comments",
                },
            ]

    return inner


@hookimpl
def register_routes():
    # Use the route decorator registry from routes module
    return Routes.get_routes()


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
        actor=actor,
    )


@hookimpl
async def extra_body_script(
    template, database, table, columns, view_name, request, datasette
):
    if await should_inject_content_script2(datasette, database, table, request.actor):
        author = await Routes.author_from_request(datasette, request)
        meta = json.dumps(
            {
                "view_name": view_name,
                "database": database,
                "table": table,
                "author": author.model_dump(),
                "readonly_viewer": "TODO",
            }
        )
        return f"window.DATASETTE_COMMENTS_META = {meta}"
    return ""


@hookimpl
def extra_js_urls(template, database, table, columns, view_name, request, datasette):
    async def inner():
        if await should_inject_content_script2(
            datasette, database, table, request.actor
        ):
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
        if await should_inject_content_script2(
            datasette, database, table, request.actor
        ):
            return [
                datasette.urls.path(
                    "/-/static-plugins/datasette-comments/content_script/index.min.css"
                )
            ]
        return []

    return inner
