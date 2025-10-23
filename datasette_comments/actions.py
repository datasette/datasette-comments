from datasette.permissions import Action
from datasette.resources import TableResource

VIEW_COMMENTS_ACTION = Action(
    name="view-comments",
    abbr=None,
    description="Ability to view comments on a table",
    takes_parent=True,
    takes_child=False,
    resource_class=TableResource,
)

ADD_COMMENTS_ACTION = Action(
    name="add-comments",
    abbr=None,
    description="Ability to add comments to a table",
    takes_parent=True,
    takes_child=True,
    resource_class=TableResource,
)
