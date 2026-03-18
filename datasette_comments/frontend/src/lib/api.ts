import createClient from "openapi-fetch";
import type { paths, components } from "../generated/api";

const client = createClient<paths>({ baseUrl: "" });

export type Author = components["schemas"]["Author"];
export type CommentData = components["schemas"]["CommentData"];
export type ReactionData = components["schemas"]["ReactionData"];
export type RenderNode = components["schemas"]["RenderNode"];
export type ActivitySearchResult = components["schemas"]["ActivitySearchResult"];

export type CommentTargetType =
  | { type: "database"; database: string }
  | { type: "table"; database: string; table: string }
  | { type: "row"; database: string; table: string; rowids: string };

export interface ActivitySearchParams {
  searchComments: string | null;
  containsTags: string[] | null;
  isResolved: boolean;
  author: string | null;
  database: string | null;
  table: string | null;
}

// Thin wrapper that maintains the same call signatures as the old Api class
// but uses the typed openapi-fetch client under the hood.
export class Api {
  static async threadNew(target: CommentTargetType, comment: string) {
    const { data } = await client.POST(
      "/-/datasette-comments/api/thread/new",
      { body: { ...target, comment } }
    );
    return data!;
  }

  static async tableViewThreads(
    database: string,
    table: string,
    rowids: string[]
  ) {
    const { data } = await client.POST(
      "/-/datasette-comments/api/threads/table_view",
      { body: { database, table, rowids } }
    );
    return data!;
  }

  static async rowViewThreads(
    database: string,
    table: string,
    rowids: string
  ) {
    const { data } = await client.POST(
      "/-/datasette-comments/api/threads/row_view",
      { body: { database, table, rowids } }
    );
    return data!;
  }

  static async threadMarkResolved(thread_id: string) {
    const { data } = await client.POST(
      "/-/datasette-comments/api/threads/mark_resolved",
      { body: { thread_id } }
    );
    return data!;
  }

  static async threadComments(thread_id: string) {
    const { data } = await client.GET(
      "/-/datasette-comments/api/thread/comments/{thread_id}",
      { params: { path: { thread_id } } }
    );
    return data!;
  }

  static async commentAdd(thread_id: string, contents: string) {
    const { data } = await client.POST(
      "/-/datasette-comments/api/thread/comment/add",
      { body: { thread_id, contents } }
    );
    return data!;
  }

  static async reactionAdd(comment_id: string, reaction: string) {
    const { data } = await client.POST(
      "/-/datasette-comments/api/reaction/add",
      { body: { comment_id, reaction } }
    );
    return data!;
  }

  static async reactionRemove(comment_id: string, reaction: string) {
    const { data } = await client.POST(
      "/-/datasette-comments/api/reaction/remove",
      { body: { comment_id, reaction } }
    );
    return data!;
  }

  static async reactions(comment_id: string): Promise<ReactionData[]> {
    // This endpoint returns a bare array — not typed via OpenAPI output
    const resp = await fetch(
      `/-/datasette-comments/api/reactions/${encodeURIComponent(comment_id)}`,
      { credentials: "include" }
    );
    return resp.json();
  }

  static async autocomplete_mentions(prefix: string) {
    const { data } = await client.GET(
      "/-/datasette-comments/api/autocomplete/mentions",
      {
        params: { query: { prefix } as any },
      }
    );
    return data!;
  }

  static async activitySearch(params: ActivitySearchParams) {
    const searchParams = new URLSearchParams();
    if (params.searchComments)
      searchParams.set("searchComments", params.searchComments);
    if (params.containsTags)
      params.containsTags.forEach((tag) =>
        searchParams.append("containsTag", tag)
      );
    searchParams.set("isResolved", params.isResolved ? "1" : "0");
    if (params.author) searchParams.set("author", params.author);
    if (params.database) searchParams.set("database", params.database);
    if (params.table) searchParams.set("table", params.table);

    // activity_search uses query params, not request body
    const resp = await fetch(
      `/-/datasette-comments/api/activity_search?${searchParams}`,
      { credentials: "include" }
    );
    return (await resp.json()) as { data: ActivitySearchResult[] };
  }
}
