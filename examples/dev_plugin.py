from datasette import hookimpl
from datasette_debug_gotham import ACTORS


@hookimpl
def datasette_comments_users():
    async def inner():
        return [
            {**actor, "username": actor_id}
            for actor_id, actor in ACTORS.items()
        ]

    return inner
