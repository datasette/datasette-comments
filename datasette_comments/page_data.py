from pydantic import BaseModel
from typing import List, Optional


class Author(BaseModel):
    actor_id: str
    name: Optional[str] = None
    profile_photo_url: Optional[str] = None
    username: Optional[str] = None


class ContentScriptPageData(BaseModel):
    view_name: str
    database: Optional[str] = None
    table: Optional[str] = None
    author: Author
    readonly_viewer: bool


# Request models


class ThreadNewRequest(BaseModel):
    type: str
    database: Optional[str] = None
    table: Optional[str] = None
    column: Optional[str] = None
    rowids: Optional[str] = None
    comment: str


class CommentAddRequest(BaseModel):
    thread_id: str
    contents: str


class ThreadMarkResolvedRequest(BaseModel):
    thread_id: str


class TableViewThreadsRequest(BaseModel):
    database: str
    table: str
    rowids: List[str]


class RowViewThreadsRequest(BaseModel):
    database: str
    table: str
    rowids: str


class ReactionRequest(BaseModel):
    comment_id: str
    reaction: str


# Response models


class RenderNode(BaseModel):
    node_type: str
    value: str


class ReactionData(BaseModel):
    reactor_actor_id: str
    reaction: str


class CommentData(BaseModel):
    id: str
    author: Author
    contents: str
    created_at: str
    created_duration_seconds: int
    render_nodes: List[RenderNode]
    reactions: List[ReactionData]


class ThreadNewResponse(BaseModel):
    ok: bool
    thread_id: Optional[str] = None


class OkResponse(BaseModel):
    ok: bool


class ThreadCommentsResponse(BaseModel):
    ok: bool
    data: List[CommentData]


class TableThreadItem(BaseModel):
    id: str


class RowThreadItem(BaseModel):
    id: str
    rowids: str


class TableViewThreadsData(BaseModel):
    table_threads: List[TableThreadItem]
    column_threads: list
    row_threads: List[RowThreadItem]
    value_threads: list


class TableViewThreadsResponse(BaseModel):
    ok: bool
    data: TableViewThreadsData


class RowViewThreadsData(BaseModel):
    row_threads: List[str]


class RowViewThreadsResponse(BaseModel):
    ok: bool
    data: RowViewThreadsData


class MentionSuggestion(BaseModel):
    username: str
    author: Author


class AutocompleteMentionsResponse(BaseModel):
    suggestions: List[MentionSuggestion]


class ActivitySearchResult(BaseModel):
    author_actor_id: str
    author: Author
    contents: str
    created_at: str
    created_duration_seconds: int
    target_type: str
    target_database: Optional[str] = None
    target_table: Optional[str] = None
    target_row_ids: Optional[str] = None
    target_column: Optional[str] = None
    target_label: Optional[str] = None


class ActivitySearchResponse(BaseModel):
    data: List[ActivitySearchResult]


class ProfileActivityItem(BaseModel):
    type: str  # "comment" or "reaction"
    created_at: str
    created_duration_seconds: int
    target_type: str
    target_database: Optional[str] = None
    target_table: Optional[str] = None
    target_row_ids: Optional[str] = None
    target_column: Optional[str] = None
    target_label: Optional[str] = None
    # comment fields
    author_actor_id: Optional[str] = None
    author: Optional[Author] = None
    contents: Optional[str] = None
    # reaction fields
    reaction: Optional[str] = None
    comment_author_actor_id: Optional[str] = None
    comment_author: Optional[Author] = None
    comment_contents: Optional[str] = None


class ProfileActivityResponse(BaseModel):
    data: List[ProfileActivityItem]


__exports__ = [
    Author,
    ContentScriptPageData,
    ThreadNewRequest,
    CommentAddRequest,
    ThreadMarkResolvedRequest,
    TableViewThreadsRequest,
    RowViewThreadsRequest,
    ReactionRequest,
    CommentData,
    ThreadNewResponse,
    OkResponse,
    ThreadCommentsResponse,
    TableViewThreadsResponse,
    RowViewThreadsResponse,
    AutocompleteMentionsResponse,
    ActivitySearchResponse,
]
