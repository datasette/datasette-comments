/**
 * This "content script" is JavaScript that gets executing on every Datasette
 * page for each client. The main goal of this content script is to ensure
 * targets with unresolved threads/comments are shown to users that have
 * permission to see it.
 *
 * Supported targets:
 * 1. Row View `/db/table/rowids`
 * 2. Table View `/db/table`
 *
 *
 *
 * It's important that the code-size of this script remains minimal and
 * resources are used sparringly (memory, network requests, etc.). The
 * JavaScript for other datasette-comments targets (admin pages, etc)
 * exist in different files.
 *
 */
import { Author } from "../../api";
import { attachRowView } from "./row_view";
import { attachTableView } from "./table_view";

function main() {
  const CONFIG = (window as any).DATASETTE_COMMENTS_META as {
    view_name: "index" | "database" | "table" | "row";
    database?: string;
    table?: string;
    author: Author;
    readonly_viewer: boolean;
  };

  switch (CONFIG.view_name) {
    case "index":
      // TODO supported index page comments
      break;
    case "database":
      // TODO support database page comments
      break;
    case "table":
      if (CONFIG.database && CONFIG.table)
        attachTableView(
          CONFIG.database!,
          CONFIG.table!,
          CONFIG.author,
          CONFIG.readonly_viewer
        );
      break;
    case "row":
      attachRowView(
        CONFIG.database!,
        CONFIG.table!,
        CONFIG.author,
        CONFIG.readonly_viewer
      );
      break;
  }
}

document.addEventListener("DOMContentLoaded", main);
