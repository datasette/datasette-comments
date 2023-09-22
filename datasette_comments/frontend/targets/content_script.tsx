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
import { Api, CommentTargetType, CommentData } from "../api";
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

function ThreadPopup(props: {
  attachTo: HTMLElement;
  target: CommentTargetType;
  initialId: string | null;
  marked_resolved: boolean;
  actor_id: string;
  profile_photo_url: string;
}) {
  const { attachTo } = props;
  const [show, setShow] = useState<boolean>(true);
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

  async function onRefreshComments(thread_id: string): Promise<CommentData[]> {
    return Api.threadComments(thread_id).then((data) => data.data);
  }
  async function onNewThread(contents: string): Promise<string> {
    return Api.threadNew(props.target, contents).then(
      ({ thread_id }) => thread_id
    );
  }
  async function onSubmitComment(
    thread_id: string,
    contents: string
  ): Promise<boolean> {
    return Api.commentAdd(thread_id, contents).then(() => true);
  }
  async function onMarkResolved(thread_id: string): Promise<boolean> {
    return Api.threadMarkResolved(thread_id).then(() => true);
  }

  const rect = attachTo.getBoundingClientRect();
  const transform = `translate(${rect.left + attachTo.offsetWidth + 10}px, ${
    rect.top
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
            initialId={props.initialId}
            marked_resolved={props.marked_resolved}
            onRefreshComments={onRefreshComments}
            onNewThread={onNewThread}
            onSubmitComment={onSubmitComment}
            onMarkResolved={onMarkResolved}
            author={{
              author_actor_id: props.actor_id,
              profile_photo_url: props.profile_photo_url,
            }}
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
async function attachThreadsTableView(
  database: string,
  table: string,
  actor_id: string,
  profile_photo_url: string
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
          actor_id={actor_id}
          profile_photo_url={profile_photo_url}
        />,
        THREAD_ROOT
      );
    }
  );

  /* step 2: column comments */

  /* step 3: row comments */

  for (const { td, pkEncoded } of rowids) {
    const thread_id = rowThreadLookup.get(pkEncoded) ?? null;

    const span = document.createElement("span");
    const button = document.createElement("button");
    button.innerText = thread_id === null ? "Comment" : "Comment +";
    span.appendChild(button);
    td.appendChild(span);
    button.addEventListener("click", () => {
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
          actor_id={actor_id}
          profile_photo_url={profile_photo_url}
        />,
        THREAD_ROOT
      );
    });
  }

  /* step 4: value comments */
}

function main() {
  THREAD_ROOT = document.body.appendChild(document.createElement("div"));
  const CONFIG = (window as any).DATASETTE_COMMENTS_META as {
    view_name: "index" | "database" | "table" | "row";
    database?: string;
    table?: string;
    actor_id?: string;
    profile_photo_url: string;
  };

  switch (CONFIG.view_name) {
    case "index":
      break;
    case "database":
      break;
    case "table":
      if (CONFIG.database && CONFIG.table)
        attachThreadsTableView(
          CONFIG.database!,
          CONFIG.table!,
          CONFIG.actor_id,
          CONFIG.profile_photo_url
        );
      break;
    case "row":
      break;
  }
}

document.addEventListener("DOMContentLoaded", main);
