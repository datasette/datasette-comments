from pydantic import BaseModel, Field
from typing import List, Union, Annotated, Literal, Optional

from datasette_comments.comment_parser import RenderNode


class ApiThreadNewResponse(BaseModel):
    ok: bool
    thread_id: str


class ApiCommentNewParams(BaseModel):
    thread_id: str
    contents: str


class Reaction(BaseModel):
    reactor_actor_id: str
    reaction: str


class Author(BaseModel):
    # the actor.id value for the author
    actor_id: str

    # Sourced from actor object key "name"
    name: str

    # Sourced from actor object key "profile_photo_url"
    # OR the gravatar URL from key "email", if enable_gravatar
    # is on.
    profile_photo_url: Optional[str]

    # the username is used for at-mentions. Should be unique to other actors
    username: Optional[str]


class ApiThreadCommentsResponseItem(BaseModel):
    id: str
    author: Author
    contents: str
    created_at: str
    created_duration_seconds: float
    render_nodes: List[RenderNode]
    reactions: List[dict]


class ApiThreadCommentsResponse(BaseModel):
    ok: Literal[True]
    thread_id: str
    comments: List[ApiThreadCommentsResponseItem]


# Subclasses for new thread parameters
class _ApiThreadNewParamsBase(BaseModel):
    comment: str = Field(..., description="The initial comment content for the thread")


class ApiThreadNewParamsDatabase(_ApiThreadNewParamsBase):
    """Create a thread on a database"""

    type: Literal["database"] = "database"
    database: str = Field(..., description="The database name")


class ApiThreadNewParamsTable(_ApiThreadNewParamsBase):
    """Create a thread on a table"""

    type: Literal["table"] = "table"
    database: str = Field(..., description="The database name")
    table: str = Field(..., description="The table name")


class ApiThreadNewParamsRow(_ApiThreadNewParamsBase):
    """Create a thread on a row"""

    type: Literal["row"] = "row"
    database: str = Field(..., description="The database name")
    table: str = Field(..., description="The table name")
    rowids: str = Field(..., description="Tilde-encoded comma-separated row IDs")


class ApiThreadNewParamsColumn(_ApiThreadNewParamsBase):
    """Create a thread on a column"""

    type: Literal["column"] = "column"
    database: str = Field(..., description="The database name")
    table: str = Field(..., description="The table name")
    column: str = Field(..., description="The column name")


class ApiThreadNewParamsValue(_ApiThreadNewParamsBase):
    """Create a thread on a specific value"""

    type: Literal["value"] = "value"
    database: str = Field(..., description="The database name")
    table: str = Field(..., description="The table name")
    column: str = Field(..., description="The column name")
    rowids: str = Field(..., description="Tilde-encoded comma-separated row IDs")


# Discriminated union of all target types
ApiThreadNewParams = Annotated[
    Union[
        ApiThreadNewParamsDatabase,
        ApiThreadNewParamsTable,
        ApiThreadNewParamsRow,
        ApiThreadNewParamsColumn,
        ApiThreadNewParamsValue,
    ],
    Field(discriminator="type"),
]


class ApiRowViewThreadsParams(BaseModel):
    """Parameters for retrieving threads on a row view"""

    database: str = Field(..., description="The database name")
    table: str = Field(..., description="The table name")
    rowids: str = Field(
        ..., description="Tilde-encoded comma-separated row IDs for the row"
    )


class ApiRowViewThreadsResponse(BaseModel):
    """Response for row view threads endpoint"""

    ok: Literal[True]
    data: dict = Field(
        ..., description="Contains 'row_threads' list with thread IDs"
    )


class ApiTableViewThreadsParams(BaseModel):
    """Parameters for retrieving threads on a table view"""

    database: str = Field(..., description="The database name")
    table: str = Field(..., description="The table name")
    rowids: List[str] = Field(
        ..., description="List of tilde-encoded comma-separated row IDs for each row in the view"
    )


class TableViewRowThreadItem(BaseModel):
    """A row thread item in table view response"""

    id: str = Field(..., description="The thread ID")
    rowids: str = Field(
        ..., description="Slash-separated tilde-encoded row IDs for the thread"
    )


class TableViewThreadItem(BaseModel):
    """A table thread item in table view response"""

    id: str = Field(..., description="The thread ID")


class ApiTableViewThreadsData(BaseModel):
    """Data structure for table view threads response"""

    table_threads: List[TableViewThreadItem] = Field(
        ..., description="Threads attached to the table itself"
    )
    column_threads: List[dict] = Field(
        ..., description="Threads attached to columns (not yet implemented)"
    )
    row_threads: List[TableViewRowThreadItem] = Field(
        ..., description="Threads attached to specific rows"
    )
    value_threads: List[dict] = Field(
        ..., description="Threads attached to specific values (not yet implemented)"
    )


class ApiTableViewThreadsResponse(BaseModel):
    """Response for table view threads endpoint"""

    ok: Literal[True]
    data: ApiTableViewThreadsData
class CommentReactionItem(BaseModel):
    """A reaction item for a comment"""

    reactor_actor_id: str = Field(..., description="The actor ID who reacted")
    reaction: str = Field(..., description="The reaction emoji or string")


class ApiCommentReactionsResponse(BaseModel):
    """Response for comment reactions endpoint"""

    ok: Literal[True]
    reactions: List[CommentReactionItem] = Field(
        ..., description="List of reactions on the comment"
    )


class ApiReactionAddParams(BaseModel):
    """Parameters for adding a reaction to a comment"""

    comment_id: str = Field(..., description="The comment ID to add reaction to")
    reaction: str = Field(..., description="The reaction emoji or string")


class ApiReactionAddResponse(BaseModel):
    """Response for adding a reaction"""

    ok: Literal[True]


class ApiReactionRemoveParams(BaseModel):
    """Parameters for removing a reaction from a comment"""

    comment_id: str = Field(..., description="The comment ID to remove reaction from")
    reaction: str = Field(..., description="The reaction emoji or string to remove")


class ApiReactionRemoveResponse(BaseModel):
    """Response for removing a reaction"""

    ok: Literal[True]
