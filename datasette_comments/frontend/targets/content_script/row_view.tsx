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
        />
      ))}
      {startThread && (
        <Thread
          initialId={null}
          author={author}
          target={{ type: "row", database, table, rowids }}
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
  author: Author
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
    />,
    target
  );
}
