from pydantic import BaseModel, Field
from typing import Union, Annotated, Literal

class ApiThreadNewResponse(BaseModel):
    ok: bool
    thread_id: str


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
