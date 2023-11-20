import { h, render } from "preact";
import { useEffect, useState } from "preact/hooks";
import { Api, Author, CommentTargetType } from "../../api";
import { Thread } from "../../components/Thread";
import { ICONS } from "../../icons";
let THREAD_ROOT: HTMLElement;

// a wrapper around <Thread/> to make it appear next to elements in the page
function ThreadPopup(props: {
  attachTo: HTMLElement;
  target: CommentTargetType;
  initialId: string | null;
  marked_resolved: boolean;
  author: Author;
  onNewThread: (id: string) => void;
}) {
  const { attachTo } = props;
  const [show, setShow] = useState<boolean>(true);

  // handle opening/showing thread on clicking out + escape keypress
  useEffect(() => {
    setShow(true);
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setShow(false);
      }
    }
    function onClick(e: MouseEvent) {
      let current = e.target as HTMLElement;
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

  async function onNewThread(thread_id: string) {
    props.onNewThread(thread_id);
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

interface TableRow {
  pkEncoded: string;
  tdElement: HTMLElement;
}
function tableViewExtractRowIds(): TableRow[] {
  const encodedRowids = [];
  const rowids = [];
  for (const tdElement of document.querySelectorAll("tbody td.type-pk")) {
    const href = tdElement.querySelector("a").getAttribute("href");
    // skip the first two parts, which are database/table names
    const [pkEncoded] = href.split("/").slice(-1);
    encodedRowids.push(pkEncoded);
    rowids.push({
      pkEncoded,
      tdElement,
    });
  }
  return rowids;
}

export async function attachTableView(
  database: string,
  table: string,
  author: Author
) {
  const THREAD_ROOT = document.body.appendChild(document.createElement("div"));
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

  for (const { tdElement, pkEncoded } of rowids) {
    let thread_id = rowThreadLookup.get(pkEncoded) ?? null;
    tdElement.style.position = "relative";
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
      tdElement.addEventListener("mouseenter", mouseenter);
      tdElement.addEventListener("mouseleave", mouseleave);
      cancel = () => {
        tdElement.removeEventListener("mouseenter", mouseenter);
        tdElement.removeEventListener("mouseleave", mouseleave);
      };
    }

    button.innerHTML = thread_id ? ICONS.COMMENT : ICONS.COMMENT_ADD;
    // @ts-ignore
    (button.querySelector("svg") as SVGElement).width = 16;
    // @ts-ignore
    (button.querySelector("svg") as SVGElement).height = 16;

    button.addEventListener("click", () => {
      // clear out any pre-existing preact components
      render(null, THREAD_ROOT);

      render(
        <ThreadPopup
          attachTo={tdElement}
          target={{
            type: "row",
            database,
            table,
            rowids: pkEncoded,
          }}
          initialId={thread_id}
          marked_resolved={false}
          author={author}
          onNewThread={(id) => {
            // when a new thread is created, changed the row button to the "comment" icon, from the "new comment" icon
            thread_id = id;
            button.innerHTML = ICONS.COMMENT;
            button.style.display = "block";
            if (cancel) cancel();
          }}
        />,
        THREAD_ROOT
      );
    });
    span.appendChild(button);
    tdElement.appendChild(span);
  }

  /* step 4: value comments */
}
