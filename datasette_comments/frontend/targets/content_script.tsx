/**
 * This "content script" is JavaScript that gets executing on every Datasette
 * page for each client. It's important that the code-size of this script
 * remains minimal and resources are used sparringly (memory, network requests,
 * etc.).
 *
 * The main goal of this content script is to ensure targets with unresolved
 * threads/comments are shown to users that have permission to see it.
 *
 * The JavaScript for other datasette-comments targets (admin pages, etc)
 * exist in different files.
 *
 */
import { h, render } from "preact";
import { ICONS } from "../icons";
import { Thread, ThreadProps } from "../components/Thread";
import { Api, Author, CommentTargetType, CommentData } from "../api";
import { useEffect, useState } from "preact/hooks";
let THREAD_ROOT: HTMLElement;

function addCommentIcon(
  target: HTMLElement,
  hasThreads: boolean,
  onClick: (icon: HTMLElement) => void
) {
  const icon = document.createElement("span");
  Object.assign(icon.style, { cursor: "pointer" });
  icon.innerHTML = hasThreads ? ICONS.COMMENT : ICONS.COMMENT_ADD;
  icon.addEventListener("click", () => {
    onClick(icon);
  });
  target.appendChild(icon);
}

// a wrapper around <Thread/> to make it appear next to elements in the page
function ThreadPopup(props: {
  attachTo: HTMLElement;
  target: CommentTargetType;
  initialId: string | null;
  marked_resolved: boolean;
  author: Author;
  onNewThread: () => void;
}) {
  const { attachTo } = props;
  const [show, setShow] = useState<boolean>(true);

  // handle opening/showing thread on clicking out + escape keypress
  useEffect(() => {
    setShow(true);
    function onKeyDown(e) {
      if (e.key === "Escape") {
        setShow(false);
      }
    }
    function onClick(e) {
      let current = e.target;
      while (current) {
        current = current.parentElement;
        if (current?.classList?.contains("datasette-comments-thread-popup")) {
          break;
        }
      }
      if (!current) {
        setShow(false);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("click", onClick);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("click", onClick);
    };
  }, [props.initialId, props.attachTo]);

  // add border style to the target, when shown
  useEffect(() => {
    if (show) {
      props.attachTo.style.border = "1px solid red";
    } else {
      props.attachTo.style.border = "";
    }
    return () => {
      props.attachTo.style.border = "";
    };
  }, [props.attachTo, show]);

  async function onNewThread(): Promise<string> {
    props.onNewThread();
    return;
  }

  const rect = attachTo.getBoundingClientRect();
  const transform = `translate(${rect.left + attachTo.offsetWidth + 10}px, ${
    rect.top + window.scrollY
  }px`;
  return (
    <div className="datasette-comments-thread-popup">
      <div
        style={{
          position: "absolute",
          inset: "0px auto auto 0px",
          transform,
        }}
      >
        {show && (
          <Thread
            target={props.target}
            initialId={props.initialId}
            author={props.author}
            onNewThread={onNewThread}
          />
        )}
      </div>
    </div>
  );
}

interface TableRow {
  pkEncoded: string;
  td: HTMLElement;
}
function tableViewExtractRowIds(): TableRow[] {
  const encodedRowids = [];
  const rowids = [];
  for (const td of document.querySelectorAll("tbody td.type-pk")) {
    const href = td.querySelector("a").getAttribute("href");
    // skip the first two parts, which are database/table names
    const [pkEncoded] = href.split("/").slice(-1);
    encodedRowids.push(pkEncoded);
    rowids.push({
      pkEncoded,
      td,
    });
  }
  return rowids;
}

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
async function attachRowView(database: string, table: string, author: Author) {
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
async function attachTableView(
  database: string,
  table: string,
  author: Author
) {
  const rowids = tableViewExtractRowIds();
  const response = await Api.tableViewThreads(
    database,
    table,
    rowids.map((d) => d.pkEncoded)
  );
  const rowThreadLookup = new Map(
    response.data.row_threads.map((row_thread) => [
      row_thread.rowids,
      row_thread.id,
    ])
  );

  /* step 1: table comments */
  addCommentIcon(
    document.querySelector("h1"),
    response.data.table_threads.length > 0,
    (icon) => {
      render(
        <ThreadPopup
          attachTo={icon}
          target={{
            type: "table",
            database,
            table,
          }}
          initialId={response.data.table_threads?.[0]?.id}
          marked_resolved={false}
          author={author}
          onNewThread={() => {}}
        />,
        THREAD_ROOT
      );
    }
  );

  /* step 2: column comments */

  /* step 3: row comments */

  for (const { td, pkEncoded } of rowids) {
    const thread_id = rowThreadLookup.get(pkEncoded) ?? null;
    td.style.position = "relative";
    const span = document.createElement("span");
    Object.assign(span.style, { position: "absolute", bottom: 0, right: 0 });
    const button = document.createElement("button");
    Object.assign(button.style, {
      background: "none",
      border: "none",
      cursor: "pointer",
    });
    // cancels the mouseenter/leave event listeners when a new thread is started
    let cancel: () => void | null = null;

    if (!thread_id) {
      button.style.display = "none";

      function mouseenter() {
        button.style.display = "block";
      }
      function mouseleave() {
        button.style.display = "none";
      }
      td.addEventListener("mouseenter", mouseenter);
      td.addEventListener("mouseleave", mouseleave);
      cancel = () => {
        td.removeEventListener("mouseenter", mouseenter);
        td.removeEventListener("mouseleave", mouseleave);
      };
    }

    button.innerHTML = thread_id ? ICONS.COMMENT : ICONS.COMMENT_ADD;
    // @ts-ignore
    (button.querySelector("svg") as SVGElement).width = 16;
    // @ts-ignore
    (button.querySelector("svg") as SVGElement).height = 16;

    button.addEventListener("click", () => {
      render(null, THREAD_ROOT);
      render(
        <ThreadPopup
          attachTo={td}
          target={{
            type: "row",
            database,
            table,
            rowids: pkEncoded,
          }}
          initialId={thread_id}
          marked_resolved={false}
          author={author}
          onNewThread={() => {
            button.innerHTML = ICONS.COMMENT;
            button.style.display = "block";
            if (cancel) cancel();
          }}
        />,
        THREAD_ROOT
      );
    });
    span.appendChild(button);
    td.appendChild(span);
  }

  /* step 4: value comments */
}

function main() {
  THREAD_ROOT = document.body.appendChild(document.createElement("div"));
  const CONFIG = (window as any).DATASETTE_COMMENTS_META as {
    view_name: "index" | "database" | "table" | "row";
    database?: string;
    table?: string;
    author: Author;
  };

  switch (CONFIG.view_name) {
    case "index":
      break;
    case "database":
      break;
    case "table":
      if (CONFIG.database && CONFIG.table)
        attachTableView(CONFIG.database!, CONFIG.table!, CONFIG.author);
      break;
    case "row":
      attachRowView(CONFIG.database!, CONFIG.table!, CONFIG.author);
      break;
  }
}

document.addEventListener("DOMContentLoaded", main);
