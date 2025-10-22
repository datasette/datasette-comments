from datasette import hookimpl
from datasette.utils.permissions import PluginSQL
from datasette_comments import ADD_COMMENTS_ACTION, VIEW_COMMENTS_ACTION
actors = {
    "1": {
        "id": "1",
        "username": "asg017",
        "name": "Alex Garcia",
        "email": "alexsebastian.garcia@gmail.com",
        # "profile_picture_url": "https://avatars.githubusercontent.com/u/15178711?v=4",
    },
    "2": {
        "id": "2",
        "username": "simonw",
        "name": "Simon Willison",
        "email": "swillison@gmail.com",
        # "profile_picture_url": "https://avatars.githubusercontent.com/u/9599?v=4",
    },
    "3": {"id": "3", "username": "readonly", "name": "I can read only"},
}

ACL_LITE_SCHEMA = """
CREATE TABLE all
"""


@hookimpl
def startup(datasette):
    internal_db = datasette.get_internal_database()
    print(internal_db)
    
@hookimpl
def actor_from_request(datasette, request):
    actor_id = request.cookies.get("actor")
    for key in actors:
        if key == actor_id:
            return actors[key]


@hookimpl
def actors_from_ids(datasette, actor_ids):
    return actors


@hookimpl
def datasette_comments_mentioned(datasette):
    return "Response from this plugin hook"


@hookimpl
def datasette_comments_users():
    async def inner():
        return list(actors.values())

    return inner


@hookimpl
def permission_resources_sql(datasette, actor, action):
    print(actor)
    if action != VIEW_COMMENTS_ACTION.name:
        return None
    if not actor:# or actor.get("id") != "root":
        return None

    return PluginSQL(
        source="all_allow",
        sql="""
            SELECT
                'tmp'                      AS parent,
                't'                        AS child,
                1                          AS allow,
                'anyone can view comments' AS reason
        """,
        params={},
    )