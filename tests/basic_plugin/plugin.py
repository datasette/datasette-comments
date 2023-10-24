from datasette import hookimpl

actors = {
    "1": {
        "id": "1",
        "username": "asg017",
        "name": "Alex Garcia",
        #"email": "alexsebastian.garcia@gmail.com"
        #"profile_picture_url": "https://avatars.githubusercontent.com/u/15178711?v=4",
    },
    "2": {
        "id": "2",
        "username": "simonw",
        "name": "Simon Willison",
        "email": "swillison@gmail.com",
        #"profile_picture_url": "https://avatars.githubusercontent.com/u/9599?v=4",
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
