from pluggy import HookspecMarker

hookspec = HookspecMarker("datasette")


@hookspec
def datasette_comments_mentioned(datasette, author_actor, target_actor):
    "Description of your hook."
