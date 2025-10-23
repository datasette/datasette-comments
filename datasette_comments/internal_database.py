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


class InternalDB:
    def __init__(self, internal_db: Database):
        self.db = internal_db
    def insert_comment_impl(self, cursor, thread_id: str, author_actor_id: str, contents: str):
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
            
        await self.db.execute_write_fn(write, block=True,)
    
    async def create_new_thread(self, actor_id: str, new_thread_params: ApiThreadNewParams) -> str:
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
                "target_row_ids": json.dumps(target_row_ids) if target_row_ids else None,
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

            self.insert_comment_impl(cursor, thread_id, actor_id, new_thread_params.comment)
            cursor.execute("commit")
        
        await self.db.execute_write_fn(db_thread_new)
        return thread_id