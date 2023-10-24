import { h, render } from "preact";
import { Thread, ThreadProps } from "../components/Thread";
import { Author } from "../api";

const data = JSON.parse(
  document.getElementById("datasette-comments-data").textContent
) as {
  data: {
    thread_id: string;
    target_type: "database" | "table" | "columns" | "row" | "value";
    target_database: string;
    target_table: string;
    target_row_ids: string;
    target_columns: string;
    marked_resolved: string;
  }[];
  author: Author;
};

const comments_tree: Map<
  string,
  {
    database_threads: string;
    tables: Map<
      string,
      {
        table_threads: string;
        rows: Map<string, string>;
      }
    >;
  }
> = new Map();

for (const row of data.data) {
  switch (row.target_type) {
    case "database": {
      break;
    }
  }
}

function main() {
  render(
    <div>
      {data.data.map((d) => (
        <Thread
          target={
            d.target_type === "database"
              ? { type: "database", database: d.target_database }
              : d.target_type === "table"
              ? {
                  type: "table",
                  database: d.target_database,
                  table: d.target_table,
                }
              : {
                  type: "row",
                  database: d.target_database,
                  table: d.target_table,
                  rowids: d.target_row_ids,
                }
          }
          key={d.thread_id}
          initialId={d.thread_id}
          marked_resolved={false}
          onNewThread={async () => ""}
          author={data.author}
        />
      ))}
    </div>,
    document.querySelector("#root")
  );
}
document.addEventListener("DOMContentLoaded", main);
