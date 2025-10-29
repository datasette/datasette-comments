from typing import List
from datasette.database import Database
from .contract import (
    ApiThreadNewParams,
    ApiThreadNewParamsTable,
    ApiThreadNewParamsRow,
    ApiThreadNewParamsColumn,
    ApiThreadNewParamsValue,
)
from ulid import ULID
import json
from . import comment_parser
from dataclasses import dataclass


@dataclass
class ThreadCommentRow:
    id: str
    author_actor_id: str
    created_at: str
    created_duration_seconds: float
    contents: str
    reactions: list[dict]


@dataclass
class ThreadRow:
    id: str
    creator_actor_id: str
    target_type: str
    target_database: str
    target_table: str | None
    target_column: str | None
    target_row_ids: List[str] | None


@dataclass
class TableViewRowThread:
    id: str
    target_row_ids: List[str]


@dataclass
class CommentReaction:
    reactor_actor_id: str
    reaction: str


class InternalDB:
    def __init__(self, internal_db: Database):
        self.db = internal_db

    async def get_thread_by_id(self, thread_id: str) -> ThreadRow:
        SQL = """
          select
            id,
            creator_actor_id,
            target_type,
            target_database,
            target_table,
            target_column,
            target_row_ids
          from datasette_comments_threads
          where id = ?
        """
        result = await self.db.execute(SQL, (thread_id,))
        row = result.first()
        if row is None:
            raise ValueError("Thread not found")

        target_row_ids = (
            json.loads(row["target_row_ids"]) if row["target_row_ids"] else None
        )

        return ThreadRow(
            id=row["id"],
            creator_actor_id=row["creator_actor_id"],
            target_type=row["target_type"],
            target_database=row["target_database"],
            target_table=row["target_table"],
            target_column=row["target_column"],
            target_row_ids=target_row_ids,
        )

    def insert_comment_impl(
        self, cursor, thread_id: str, author_actor_id: str, contents: str
    ):
        id = str(ULID()).lower()
        parsed = comment_parser.parse(contents)
        mentions = list(set(mention.value[1:] for mention in parsed.mentions))
        hashtags = list(set(mention.value[1:] for mention in parsed.tags))

        SQL = """
          INSERT INTO datasette_comments_comments(
            id,
            thread_id,
            author_actor_id,
            contents,
            mentions,
            hashtags,
            past_revisions
          )
          VALUES (
            :id,
            :thread_id,
            :author_actor_id,
            :contents,
            :mentions,
            :hashtags,
            json_array()
          )
      """
        params = {
            "id": id,
            "thread_id": thread_id,
            "author_actor_id": author_actor_id,
            "contents": contents,
            "mentions": json.dumps(mentions),
            "hashtags": json.dumps(hashtags),
        }

        cursor.execute(SQL, params)

    async def insert_comment(self, thread_id: str, actor_id: str, contents: str):
        def write(cursor):
            self.insert_comment_impl(cursor, thread_id, actor_id, contents)

        await self.db.execute_write_fn(
            write,
            block=True,
        )

    async def get_thread_comments(self, thread_id: str) -> List[ThreadCommentRow]:
        SQL = """
          select
            id,
            author_actor_id,
            created_at,
            (strftime('%s', 'now') - strftime('%s', created_at)) as created_duration_seconds,
            contents,
            (
              select json_group_array(
                json_object(
                  'reactor_actor_id', reactor_actor_id,
                  'reaction', reaction
                )
              )
              from datasette_comments_reactions
              where comment_id == datasette_comments_comments.id
            ) as reactions
          from datasette_comments_comments
          where thread_id = ?
          order by created_at
        """
        rows = []

        results = await self.db.execute(SQL, (thread_id,))
        for row in results:
            reactions = json.loads(row["reactions"]) if row["reactions"] else []
            rows.append(
                ThreadCommentRow(
                    id=row["id"],
                    author_actor_id=row["author_actor_id"],
                    created_at=row["created_at"],
                    created_duration_seconds=row["created_duration_seconds"],
                    contents=row["contents"],
                    reactions=reactions,
                )
            )
        return rows

    async def create_new_thread(
        self, actor_id: str, new_thread_params: ApiThreadNewParams
    ) -> str:
        thread_id = str(ULID()).lower()

        def db_thread_new(conn):
            target_database = new_thread_params.database
            target_table = None
            target_column = None
            target_row_ids = None
            type = new_thread_params.type

            if isinstance(new_thread_params, ApiThreadNewParamsTable):
                target_table = new_thread_params.table
            elif isinstance(new_thread_params, ApiThreadNewParamsRow):
                target_table = new_thread_params.table
                target_row_ids = new_thread_params.rowids
            elif isinstance(new_thread_params, ApiThreadNewParamsColumn):
                target_table = new_thread_params.table
                target_column = new_thread_params.column
            elif isinstance(new_thread_params, ApiThreadNewParamsValue):
                target_table = new_thread_params.table
                target_column = new_thread_params.column
                target_row_ids = new_thread_params.rowids

            cursor = conn.cursor()
            cursor.execute("begin")
            params = {
                "id": thread_id,
                "creator_actor_id": actor_id,
                "target_type": type,
                "target_database": target_database,
                "target_table": target_table,
                "target_column": target_column,
                "target_row_ids": json.dumps(target_row_ids)
                if target_row_ids
                else None,
            }

            cursor.execute(
                """
                  insert into datasette_comments_threads(
                    id,
                    creator_actor_id,
                    target_type,
                    target_database,
                    target_table,
                    target_column,
                    target_row_ids
                  )
                  values (
                    :id,
                    :creator_actor_id,
                    :target_type,
                    :target_database,
                    :target_table,
                    :target_column,
                    :target_row_ids
                  );
                """,
                params,
            )

            self.insert_comment_impl(
                cursor, thread_id, actor_id, new_thread_params.comment
            )
            cursor.execute("commit")

        await self.db.execute_write_fn(db_thread_new)
        return thread_id

    async def get_row_view_threads(
        self, database: str, table: str, rowids: List[str]
    ) -> List[str]:
        """Get all thread IDs for a specific row view"""
        SQL = """
          SELECT id
          FROM datasette_comments_threads
          WHERE target_type = 'row'
            AND target_database = ?
            AND target_table = ?
            AND target_row_ids = ?
            AND NOT marked_resolved
        """
        results = await self.db.execute(SQL, (database, table, json.dumps(rowids)))
        return [row["id"] for row in results.rows]

    async def get_table_view_row_threads(
        self, database: str, table: str, rowids: List[List[str]]
    ) -> List[TableViewRowThread]:
        """Get all row threads for a table view (multiple rows)"""
        SQL = """
          SELECT
            id,
            target_row_ids
          FROM datasette_comments_threads
          WHERE target_type = 'row'
            AND target_database = ?
            AND target_table = ?
            AND target_row_ids IN (
              SELECT value
              FROM json_each(?)
            )
            AND NOT marked_resolved
        """
        results = await self.db.execute(SQL, (database, table, json.dumps(rowids)))
        return [
            TableViewRowThread(
                id=row["id"],
                target_row_ids=json.loads(row["target_row_ids"])
            )
            for row in results.rows
        ]

    async def comment_reactions(self, comment_id: str) -> List[CommentReaction]:
        """Get all reactions for a specific comment"""
        SQL = """
          SELECT
            reactor_actor_id,
            reaction
          FROM datasette_comments_reactions
          WHERE comment_id = ?
        """
        results = await self.db.execute(SQL, (comment_id,))
        return [
            CommentReaction(
                reactor_actor_id=row["reactor_actor_id"],
                reaction=row["reaction"]
            )
            for row in results.rows
        ]

    async def add_comment_reaction(
        self, comment_id: str, reactor_actor_id: str, reaction: str
    ):
        """Add a reaction to a comment"""
        id = str(ULID()).lower()
        SQL = """
          INSERT INTO datasette_comments_reactions(
            id,
            comment_id,
            reactor_actor_id,
            reaction
          )
          VALUES (
            :id,
            :comment_id,
            :reactor_actor_id,
            :reaction
          )
        """
        await self.db.execute_write(
            SQL,
            {
                "id": id,
                "comment_id": comment_id,
                "reactor_actor_id": reactor_actor_id,
                "reaction": reaction,
            },
            block=True,
        )
