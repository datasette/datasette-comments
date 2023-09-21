async function api(path: string, params?: { method?: string; data?: any }) {
  const { method, data } = params ?? {};
  // TODO base_url
  return fetch(`${path}`, {
    method,
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: data ? JSON.stringify(data) : undefined,
  }).then((response) => response.json());
}

export type CommentTargetType =
  | { type: "database"; database: string }
  | { type: "table"; database: string; table: string }
  | { type: "row"; database: string; table: string; rowids: string };

export interface CommentData {
  id: string;
  author_actor_id: string;
  author_profile_picture: string;
  author_name: string;
  contents: string;
  created_at: string;
  render_nodes: {
    node_type: "raw" | "mention" | "url" | "tag";
    value: string;
  }[];
}
export class Api {
  static async threadNew(
    target: CommentTargetType,
    comment: string
  ): Promise<{
    ok: boolean;
    thread_id: string;
  }> {
    return api("/-/datasette-comments/thread/new", {
      method: "POST",
      data: {
        ...target,
        comment,
      },
    });
  }
  static async tableViewThreads(
    database: string,
    table: string,
    rowids: string[]
  ): Promise<{
    ok: boolean;
    data: {
      table_threads: {
        id: string;
      }[];
      column_threads: {}[];
      row_threads: {
        id: string;
        rowids: string;
      }[];
      value_threads: {}[];
    };
  }> {
    return api("/-/datasette-comments/threads/table_view", {
      method: "POST",
      data: {
        database,
        table,
        rowids,
      },
    });
  }
  static async threadMarkResolved(thread_id: string): Promise<{
    ok: boolean;
  }> {
    return api("/-/datasette-comments/threads/mark_resolved", {
      method: "POST",
      data: {
        thread_id,
      },
    });
  }

  static async threadComments(thread_id: string): Promise<{
    ok: boolean;
    data: CommentData[];
  }> {
    return api(`/-/datasette-comments/thread/comments/${thread_id}`);
  }
  static async commentAdd(
    thread_id: string,
    contents: string
  ): Promise<{
    ok: boolean;
  }> {
    return api(`/-/datasette-comments/thread/comment/add`, {
      method: "POST",
      data: {
        thread_id,
        contents,
      },
    });
  }
}
