CREATE TABLE IF NOT EXISTS datasette_comments_threads(
  --! Threads table for datasette-comments.
  --!
  --! Every row is a single thread, and always has a creator.
  --! A thread can target a specific database, table, column,
  --! row, or value.
  --!
  --! Threads can be marked "resolved" by users.

  --- ULID primary key for a thread
  id ULID PRIMARY KEY,

  --- Timestamp creation time of the thread.
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  --- Datasette actor ID for the creator of the thread
  creator_actor_id TEXT,

  --- "database", "table", "column", "row", or "value"
  target_type TEXT,

  --- TODO should this be a path to the DB or db name??
  target_database TEXT,

  --- Name of the table the comment is targeting.
  --- Only when target_type = "table" | "column" | "row" | "value"
  target_table TEXT,

  --- a JSON-serialized array of primary keys of the row the comment is targeting.
  --- Only when target_type == "row" | "value"
  target_row_ids JSON,

  --- Name of the column the comment is targeting.
  --- Only when target_type = "column" | "value"
  target_column TEXT,

  --- Whether the thread has been marked as resolved. Once created, the thread
  --- is automatically unresolved, and should only be marked resolved by
  --- the creator of the thread. TODO can anyone resolved a thread?
  marked_resolved BOOLEAN AS (resolved_at is not null),

  --- Timestamp of when the thread was last marked as resolved.
  resolved_at DATETIME
);

--- Make it easier to see which threads an actor has made
CREATE INDEX IF NOT EXISTS idx_datasette_comments_threads_creator_actor_id
  ON datasette_comments_threads(creator_actor_id);
--- Make it faster to filter out resolved threads
CREATE INDEX IF NOT EXISTS idx_datasette_comments_threads_marked_resolved
  ON datasette_comments_threads(marked_resolved);


CREATE TABLE IF NOT EXISTS datasette_comments_comments(
  --! Comments table for datasette-comments.
  --! Every row is a comment a user has left, and is always connected
  --! to a thread.

  --- ULID primary key for a comment
  id ULID PRIMARY KEY,

  --- Foreign key to the thread the comment belongs in.
  thread_id TEXT REFERENCES datasette_comments_threads(id),

  --- Timestamp creation time of the original comment.
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  --- Timestamp of the last time the comment was created/updated.
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  --- Datasette actor ID for the author of the comment
  author_actor_id TEXT,

  --- Raw text contents of the individual comment.
  contents TEXT,

  --- "Mentions" (@ mentions) referenced in the comment.
  --- Schema: string[]
  mentions JSON,

  --- Tags (ex. #hastag) created in the comment.
  --- Schema: string[]
  hashtags JSON,

  --- Whether the comment has been edited or not. Based on if there
  --- are any revisions.
  has_edits BOOLEAN AS (json_array_length(past_revisions) > 0),

  --- All the prevision versions of the comment, made when an author edits the comment.
  --- The JSON document has the following schema:
  --- {"contents": string, "created_at": datetime}[]
  past_revisions JSON
);

--- Make it faster to find comments an actor has made
CREATE INDEX IF NOT EXISTS datasette_comments_comments_author_actor_id
  ON datasette_comments_comments(author_actor_id);

--- Make it faster to find recently updated comments
CREATE INDEX IF NOT EXISTS datasette_comments_comments_updated_at
  ON datasette_comments_comments(updated_at);


CREATE TABLE IF NOT EXISTS datasette_comments_reactions(
  --! All "reactions" made on specific tables. An actor can add a reaction
  --! to any comment, and can add multiple reactions to a single comment.
  --! One row is a single reaction an actor made on a specific comment.

  --- ULID primary key of the reaction
  id ULID PRIMARY KEY,

    --- Foreign key to the comment the reaction is a part of.
  comment_id TEXT REFERENCES datasette_comments_comments(id),

  --- Datasette actor ID of the user adding a reaction.
  reactor_actor_id TEXT,

  --- The reaction a user left, usually an emoji.
  reaction TEXT,

  --- only 1 reaction per comment per user per reaction
  UNIQUE (comment_id, reactor_actor_id, reaction)
);

-- Get all reactions for a specific comment.
CREATE INDEX IF NOT EXISTS idx_datasette_comments_reactions_comment_id
  ON datasette_comments_reactions(comment_id);

--- Get all reactions a user has made.
CREATE INDEX IF NOT EXISTS idx_datasette_comments_reactions_reactor_actor_id
  ON datasette_comments_reactions(reactor_actor_id);

