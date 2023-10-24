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

// map EXACTLY to the Python Author class
export interface Author {
  actor_id: string;
  name: string;
  profile_photo_url: string | null;
}

export type CommentTargetType =
  | { type: "database"; database: string }
  | { type: "table"; database: string; table: string }
  | { type: "row"; database: string; table: string; rowids: string };

export interface ReactionData {
  reactor_actor_id: string;
  reaction: string;
}

export interface CommentData {
  id: string;
  author: Author;
  contents: string;
  created_at: string;
  created_duration_seconds: number;
  render_nodes: {
    node_type: "raw" | "mention" | "url" | "tag" | "linebreak";
    value: string;
  }[];
  reactions: ReactionData[];
}
export class Api {
  static async threadNew(
    target: CommentTargetType,
    comment: string
  ): Promise<{
    ok: boolean;
    thread_id: string;
  }> {
    return api("/-/datasette-comments/api/thread/new", {
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
    return api("/-/datasette-comments/api/threads/table_view", {
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
    return api("/-/datasette-comments/api/threads/mark_resolved", {
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
    return api(`/-/datasette-comments/api/thread/comments/${thread_id}`);
  }
  static async commentAdd(
    thread_id: string,
    contents: string
  ): Promise<{
    ok: boolean;
  }> {
    return api(`/-/datasette-comments/api/thread/comment/add`, {
      method: "POST",
      data: {
        thread_id,
        contents,
      },
    });
  }
  static async reactionAdd(
    comment_id: string,
    reaction: string
  ): Promise<{
    ok: boolean;
  }> {
    return api(`/-/datasette-comments/api/reaction/add`, {
      method: "POST",
      data: {
        comment_id,
        reaction,
      },
    });
  }
  static async reactionRemove(
    comment_id: string,
    reaction: string
  ): Promise<{
    ok: boolean;
  }> {
    return api(`/-/datasette-comments/api/reaction/remove`, {
      method: "POST",
      data: {
        comment_id,
        reaction,
      },
    });
  }
  static async reactions(comment_id: string): Promise<
    {
      reactor_actor_id: string;
      reaction: string;
    }[]
  > {
    return api(`/-/datasette-comments/api/reactions/${comment_id}`);
  }
}

export interface State<T, E> {
  isLoading: boolean;
  data?: T;
  error?: E;
}
export type Action<T, E> =
  | { type: "init" }
  | { type: "success"; data: T }
  | { type: "failure"; error: E };

export function apiReducer<
  T,
  E,
  TState extends State<T, E>,
  TAction extends Action<T, E>
>(state: TState, action: TAction): TState {
  switch (action.type) {
    case "init":
      return {
        ...state,
        isLoading: true,
      };
    case "failure":
      return { ...state, isLoading: false, error: action.error };
    case "success":
      return {
        ...state,
        isLoading: false,
        data: action.data,
      };
  }
}
