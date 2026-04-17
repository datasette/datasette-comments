/**
 * This "content script" is JavaScript that gets executing on every Datasette
 * page for each client. The main goal of this content script is to ensure
 * targets with unresolved threads/comments are shown to users that have
 * permission to see it.
 *
 * Supported targets:
 * 1. Row View `/db/table/rowids`
 * 2. Table View `/db/table`
 */
import { loadPageData } from "../lib/page_data";
import type { ContentScriptPageData } from "../page_data/ContentScriptPageData.types";
import { attachRowView } from "./row_view";
import { attachTableView } from "./table_view";

function main() {
  const CONFIG = loadPageData<ContentScriptPageData>();

  switch (CONFIG.view_name) {
    case "index":
      break;
    case "database":
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
