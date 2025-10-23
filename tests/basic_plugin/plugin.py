from datasette import hookimpl
from datasette.utils.permissions import PluginSQL
from datasette_comments import ADD_COMMENTS_ACTION, VIEW_COMMENTS_ACTION


def pfp(letter, fg="white", bg="black"):
    return f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32'%3E%3Ccircle cx='16' cy='16' r='16' fill='{bg}'%3E%3C/circle%3E%3Ctext fill='{fg}' x='16' y='16' text-anchor='middle' dominant-baseline='middle'%3E{letter}%3C/text%3E%3C/svg%3E"


actors = {
    ###### DAILY PLANET ######
    "clark": {
        "id": "clark",
        "name": "Clark Kent",
        "newsroom": "daily-planet",
        "profile_picture_url": pfp("C", bg="blue"),
    },
    "lois": {
        "id": "lois",
        "name": "Lois Lane",
        "newsroom": "daily-planet",
        "profile_picture_url": pfp("L", bg="red"),
    },
    "jimmy": {
        "id": "jimmy",
        "name": "Jimmy Olsen",
        "newsroom": "daily-planet",
        "profile_picture_url": pfp("J", bg="orange"),
    },
    ###### GOTHAM GAZETTE ######
    "bruce": {
        "id": "bruce",
        "name": "Bruce Wayne",
        "newsroom": "gotham-gazette",
        "profile_picture_url": pfp("B", bg="black"),
    },
    "alfred": {
        "id": "alfred",
        "name": "Alfred Pennyworth",
        "newsroom": "gotham-gazette",
        "profile_picture_url": pfp("A", bg="gray"),
    },
    "selina": {
        "id": "selina",
        "name": "Selina Kyle",
        "newsroom": "gotham-gazette",
        "profile_picture_url": pfp("S", bg="purple"),
    },
}


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
def extra_js_urls(template, database, table, columns, view_name, request, datasette):
    return ["/assets/widget.js"]


DAILY_PLANET_ACCESS_METROPOLIS_RULE = PluginSQL(
    source="daily_planet_access_metropolis",
    sql="""
              SELECT 
                database_name AS parent, 
                table_name AS child, 
                1 AS allow, 
                'TODO' AS reason 
              FROM catalog_tables
              WHERE database_name = 'metropolis' 
              """,
    params={},
)

GOTHAM_GAZETTE_ACCESS_GOTHAM_RULE = PluginSQL(
    source="gotham_gazette_access_gotham",
    sql="""
  SELECT 
    database_name AS parent, 
    table_name AS child, 
    1 AS allow, 
    'TODO' AS reason 
  FROM catalog_tables
  WHERE database_name = 'gotham' 
  """,
    params={},
)


@hookimpl
def permission_resources_sql(datasette, actor, action):
    rules = []
    if action == VIEW_COMMENTS_ACTION.name:
        if actor["newsroom"] == "daily-planet":
            rules.append(DAILY_PLANET_ACCESS_METROPOLIS_RULE)

        elif actor["newsroom"] == "gotham-gazette":
            rules.append(GOTHAM_GAZETTE_ACCESS_GOTHAM_RULE)
    elif action == ADD_COMMENTS_ACTION.name:
        if actor["newsroom"] == "daily-planet":
            rules.append(DAILY_PLANET_ACCESS_METROPOLIS_RULE)

        elif actor["newsroom"] == "gotham-gazette":
            rules.append(GOTHAM_GAZETTE_ACCESS_GOTHAM_RULE)
    return rules
