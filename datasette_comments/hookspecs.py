from pluggy import HookspecMarker

hookspec = HookspecMarker("datasette")


@hookspec
def _datasette_comments_mentioned(datasette, author_actor, target_actor):
    """
    TODO: not used yet, still need to figure out an API.

    "callback" should provide:
     - Author of the comment
     - Who was mentioned
     - Contents of the comment
     - The database/table the comment appears on
     - The thread id?
    """


@hookspec
def datasette_comments_users(datasette):
    """
    List of users that can be authors or mentioned in comments.

    Every item should contain a dict with the following keys:

      - id: A unique ID of the user, same as the actor ID.
      - username: A unique string that is used in searches and @ mentions.
      - name: A string of the user's natural name.
      - profile_photo_url: Optional URL to the user's profile pic.
      - email: Optional email used for gravatar profile photo, if enabled.
    """
