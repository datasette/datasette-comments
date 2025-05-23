import { Fragment, h, render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { Api, Author, CommentTargetType } from "../../api";
import { Thread } from "../../components/Thread";
import { ICONS } from "../../icons";
let THREAD_ROOT: HTMLElement;

// source: https://gist.github.com/jjmu15/8646226
function isInViewport(element: HTMLElement) {
  var rect = element.getBoundingClientRect();
  var html = document.documentElement;
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || html.clientHeight) &&
    rect.right <= (window.innerWidth || html.clientWidth)
  );
}

// a wrapper around <Thread/> to make it appear next to elements in the page
function ThreadPopup(props: {
  attachTo: HTMLElement;
  target: CommentTargetType;
  initialId: string | null;
  marked_resolved: boolean;
  author: Author;
  onNewThread: (id: string) => void;
  onResolvedThread: () => void;
  readonly_viewer: boolean;
}) {
  const { attachTo, readonly_viewer } = props;
  const [show, setShow] = useState<boolean>(true);
  const popupRef = useRef<HTMLDivElement>(null);

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
      props.attachTo.parentElement.style.boxShadow =
        "#edb61f 0px 0px 4px 1px inset";
      if (popupRef.current && !isInViewport(popupRef.current)) {
        popupRef.current.scrollIntoView({ behavior: "smooth" });
      }
    } else {
      props.attachTo.style.boxShadow = "";
    }
    return () => {
      props.attachTo.parentElement.style.boxShadow = "";
    };
  }, [props.attachTo, show, popupRef]);

  async function onNewThread(thread_id: string) {
    props.onNewThread(thread_id);
    return;
  }
  async function onResolvedThread() {
    props.onResolvedThread();
    setShow(false);
    return;
  }

  const rect = attachTo.getBoundingClientRect();
  let transform;
  if (window.innerWidth < 600) {
    // Mobile
    transform = `translate(20px, ${rect.top + window.scrollY + 40}px)`;
  } else {
    transform = `translate(${rect.left + attachTo.offsetWidth + 10}px, ${rect.top + rect.height + 4 + window.scrollY
      }px`;
  }
  return (
    <div className="datasette-comments-thread-popup">
      <div
        ref={popupRef}
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
            onResolvedThread={onResolvedThread}
            readonly_viewer={readonly_viewer}
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
  author: Author,
  readonly_viewer: boolean
) {

  document.head.appendChild(
    Object.assign(document.createElement("style"), {
      textContent: `
      .datasette-comments-thread-button {
        opacity: 0.0
      }
      .datasette-comments-thread-button.show {
        opacity: 1;
      }
      .datasette-comments-thread-button:hover {
        opacity: 0.8;
      }
      `}));

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
  // Skipping table comments for now, it's a bit awkward
  /*
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
  */

  /* step 2: column comments */

  /* step 3: row comments */

  for (const { tdElement, pkEncoded } of rowids) {
    let thread_id: string | null = rowThreadLookup.get(pkEncoded);

    const div = document.createElement("div");
    Object.assign(div.style, {
      "white-space": "nowrap",
      "display": "flex"
    });
    
    // Move primary key <a> element into new inner <div> for easier styling
    while (tdElement.firstChild) {
      div.appendChild(tdElement.firstChild);
    }
    

    const span = document.createElement("span");
    const button = document.createElement("button");
    Object.assign(button.style, {
      background: "none",
      border: "none",
      cursor: "pointer",
    });
    button.classList.add("datasette-comments-thread-button");
    // cancels the mouseenter/leave event listeners when a new thread is started
    let cancel: () => void | null = null;

    if (thread_id) {
      button.classList.add("show");
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
            button.classList.add("show");
            if (cancel) cancel();
          }}
          onResolvedThread={() => {
            // when a thread is resolved, remove the button
            thread_id = null;
            button.innerHTML = ICONS.COMMENT_ADD;
            button.classList.remove("show");
            if (cancel) cancel();
          }}
          readonly_viewer={readonly_viewer}
        />,
        THREAD_ROOT
      );
    });

    if (!thread_id && readonly_viewer) {
      continue;
    }
    span.appendChild(button);
    div.appendChild(span);
    tdElement.appendChild(div);
  }

  /* step 4: value comments */
}
