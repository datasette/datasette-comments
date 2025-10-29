from typing import List
from datasette.database import Database
from .contract import (
    ApiActivitySearchParams,
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


@dataclass
class ActivitySearchRow:
    author_actor_id: str
    contents: str
    created_at: str
    created_duration_seconds: float
    target_type: str
    target_database: str
    target_table: str
    target_row_ids: str
    target_column: str | None


def _activity_search_where(
    search_params: ApiActivitySearchParams,
    author_actor_id_map: dict[str, str] | None = None,
) -> tuple[str, list]:
    """Build WHERE clause and params for activity search.
    
    Args:
        search_params: The search parameters from the API
        author_actor_id_map: Optional dict mapping username -> actor_id
        
    Returns:
        Tuple of (WHERE clause string, list of params)
    """
    WHERE = "1"
    params = []

    # when provided, searchComments adds a `LIKE '%query%'` constraint
    if search_params.searchComments:
        WHERE += " AND comments.contents LIKE printf('%%%s%%', ?)"
        params.append(search_params.searchComments)

    if search_params.author and author_actor_id_map:
        actor_id = author_actor_id_map.get(search_params.author)
        if actor_id:
            WHERE += " AND comments.author_actor_id = ?"
            params.append(actor_id)

    if search_params.database:
        WHERE += " AND threads.target_database = ?"
        params.append(search_params.database)

    if search_params.table:
        WHERE += " AND threads.target_table = ?"
        params.append(search_params.table)

    # Handle isResolved: None means no filter, True means resolved, False means unresolved
    if search_params.isResolved is not None:
        WHERE += f" AND {'' if search_params.isResolved else 'NOT'} threads.marked_resolved"

    if search_params.containsTag:
        for tag in search_params.containsTag:
            if not tag:
                continue
            WHERE += " AND ? in (select value from json_each(comments.hashtags))"
            params.append(tag)

    return WHERE, params


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

    async def remove_comment_reaction(
        self, comment_id: str, reactor_actor_id: str, reaction: str
    ):
        """Remove a reaction from a comment"""
        SQL = """
          DELETE FROM datasette_comments_reactions
          WHERE comment_id = :comment_id
            AND reactor_actor_id = :reactor_actor_id
            AND reaction = :reaction
        """
        await self.db.execute_write(
            SQL,
            {
                "comment_id": comment_id,
                "reactor_actor_id": reactor_actor_id,
                "reaction": reaction,
            },
            block=True,
        )

    async def activity_search(
        self,
        allowed_actor_tables_sql: str,
        allowed_actor_params: dict,
        search_params: ApiActivitySearchParams,
        author_actor_id_map: dict[str, str] | None = None,
    ) -> list[ActivitySearchRow]:
        """Search for activity based on the given parameters.
        
        Args:
            allowed_actor_tables_sql: SQL CTE for allowed tables
            allowed_actor_params: Parameters for the allowed tables SQL
            search_params: The search parameters
            author_actor_id_map: Optional dict mapping username -> actor_id
            
        Returns:
            List of ActivitySearchRow results
        """
        WHERE, where_params = _activity_search_where(search_params, author_actor_id_map)
        
        sql = f"""
        WITH actor_tables(database_name, table_name, reason) AS (
          {allowed_actor_tables_sql}
        ),
        final as (
          SELECT
            comments.author_actor_id,
            comments.contents,
            comments.created_at,
            (strftime('%s', 'now') - strftime('%s', comments.created_at)) as created_duration_seconds,
            threads.target_type,
            threads.target_database,
            threads.target_table,
            threads.target_row_ids,
            threads.target_column
          FROM datasette_comments_comments AS comments
          LEFT JOIN datasette_comments_threads AS threads ON threads.id = comments.thread_id
          LEFT JOIN actor_tables ON threads.target_database = actor_tables.database_name
            AND threads.target_table = actor_tables.table_name
          WHERE 
            threads.target_type = 'row'
            AND actor_tables.database_name IS NOT NULL
            AND actor_tables.table_name IS NOT NULL
            AND {WHERE}
          ORDER BY comments.created_at DESC
          LIMIT 100
        )
        select * from final;
        """
        
        # Combine the allowed_actor_params with where_params
        # TODO: isn't allowed_actor_params a dict, and where_params a list?
        # cant mix named and unnamed params like this
        all_params = list(allowed_actor_params) + where_params
        
        results = await self.db.execute(sql, all_params)
        
        return [
            ActivitySearchRow(
                author_actor_id=row["author_actor_id"],
                contents=row["contents"],
                created_at=row["created_at"],
                created_duration_seconds=row["created_duration_seconds"],
                target_type=row["target_type"],
                target_database=row["target_database"],
                target_table=row["target_table"],
                target_row_ids=row["target_row_ids"],
                target_column=row["target_column"],
            )
            for row in results.rows
        ]
