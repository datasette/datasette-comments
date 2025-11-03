from datasette.permissions import Action
from datasette.resources import TableResource

VIEW_COMMENTS_ACTION = Action(
    name="view-comments",
    abbr=None,
    description="Ability to view comments on a table",
    resource_class=TableResource,
)

ADD_COMMENTS_ACTION = Action(
    name="add-comments",
    abbr=None,
    description="Ability to add comments to a table",
    resource_class=TableResource,
)
