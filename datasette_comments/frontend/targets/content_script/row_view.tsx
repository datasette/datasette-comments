import { h, render } from "preact";
import { Thread } from "../../components/Thread";
import { Api, Author } from "../../api";
import { useState } from "preact/hooks";

function RowViewComments(props: {
  row_threads: string[];
  author: Author;
  database: string;
  table: string;
  rowids: string;
  readonly_viewer: boolean;
}) {
  const { row_threads, author, database, table, rowids } = props;
  const [startThread, setStartThread] = useState<boolean>(false);
  return (
    <div>
      <h2>Comments</h2>

      {row_threads.map((d) => (
        <Thread
          initialId={d}
          author={author}
          target={{ type: "row", database, table, rowids }}
          readonly_viewer={props.readonly_viewer}
        />
      ))}
      {startThread && (
        <Thread
          initialId={null}
          author={author}
          target={{ type: "row", database, table, rowids }}
          readonly_viewer={props.readonly_viewer}
        />
      )}
      {!startThread && row_threads.length === 0 && (
        <div>
          <div>No comments!</div>
          <button onClick={() => setStartThread(true)}>Add comment</button>
        </div>
      )}
    </div>
  );
}

export async function attachRowView(
  database: string,
  table: string,
  author: Author,
  readonly_viewer: boolean
) {
  const rowids = window.location.pathname.split("/").pop();
  const threads = await Api.rowViewThreads(database, table, rowids);
  const target = document
    .querySelector("section.content")
    .appendChild(document.createElement("div"));

  render(
    <RowViewComments
      row_threads={threads.data.row_threads}
      author={author}
      database={database}
      table={table}
      rowids={rowids}
      readonly_viewer={readonly_viewer}
    />,
    target
  );
}
