import { h, render } from "preact";
import { Thread, ThreadProps } from "../components/Thread";
import { Api, Author, CommentData } from "../api";

interface Datum {
  author_actor_id: string;
  author_actor: {
    id: string;
    name: string;
    profile_picture_url: string;
  };
  contents: string;
  created_at: string;
  target_type: "database" | "table" | "columns" | "row" | "value";
  target_database: string;
  target_table: string | null;
  target_row_ids: string | null;
  target_columns: string | null;
}
const data = JSON.parse(
  document.getElementById("datasette-comments-data").textContent
) as {
  data: Datum[];
  author: Author;
};

function renderTarget({
  target_type,
  target_database,
  target_table,
  target_row_ids,
  target_columns,
}: Datum) {
  switch (target_type) {
    case "database":
      return target_database;
    case "table":
      return `${target_database}/${target_table}`;
    case "columns":
      return `${target_database}/${target_columns}`;
    case "row":
      return `${target_database}/${target_table}/${JSON.parse(
        target_row_ids
      ).join(",")}`;
    case "value":
      return `${target_database}/${target_table}/${target_columns}/${JSON.parse(
        target_row_ids
      ).join(",")}`;
  }
}

function main() {
  console.log(data.data[0]);
  render(
    <div>
      {data.data.map((d, i) => {
        const { author_actor, contents, created_at } = d;
        const isLastRead = i === 4;
        const target = renderTarget(d);
        return (
          <div
            style={{
              position: "relative",
              borderBottom: isLastRead ? "1px solid red" : null,
            }}
          >
            <span>
              <span style="font-family: monospace;">{created_at}</span>:{" "}
              <span style="font-weight:600;">
                <img
                  src={author_actor.profile_picture_url}
                  width="14px"
                  style="border-radius: 50%; margin-right: 2px;"
                />
                {author_actor.name}
              </span>{" "}
              commented on{" "}
              <b style="font-weight: 600;">
                <a href={"/" + target}>{target}</a>
              </b>
              : <i style="font-style: italic">{contents}</i>
            </span>
            {isLastRead && (
              <div style="position: absolute; right: 0; bottom: 0; background: red; color: white; font-size: 12px; line-height: 12px; padding: 2px 6px">
                ⌃New
              </div>
            )}
          </div>
        );
      })}
    </div>,
    document.querySelector("#root")
  );
}
document.addEventListener("DOMContentLoaded", main);
