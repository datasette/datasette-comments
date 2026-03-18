import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { Api, Author, CommentTargetType } from "../lib/api";
import { Thread } from "../components/Thread";
import { ICONS } from "../lib/icons";
let THREAD_ROOT: HTMLElement;

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
        current = current.parentElement!;
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

  useEffect(() => {
    if (show) {
      props.attachTo.parentElement!.style.boxShadow =
        "#edb61f 0px 0px 4px 1px inset";
      if (popupRef.current && !isInViewport(popupRef.current)) {
        popupRef.current.scrollIntoView({ behavior: "smooth" });
      }
    } else {
      props.attachTo.style.boxShadow = "";
    }
    return () => {
      props.attachTo.parentElement!.style.boxShadow = "";
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

interface TableRow {
  pkEncoded: string;
  tdElement: HTMLElement;
}
function tableViewExtractRowIds(): TableRow[] {
  const rowids: TableRow[] = [];
  for (const tdElement of document.querySelectorAll("tbody td.type-pk")) {
    const href = tdElement.querySelector("a")!.getAttribute("href")!;
    const [pkEncoded] = href.split("/").slice(-1);
    rowids.push({
      pkEncoded,
      tdElement: tdElement as HTMLElement,
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

  for (const { tdElement, pkEncoded } of rowids) {
    let thread_id: string | null = rowThreadLookup.get(pkEncoded) ?? null;

    const div = document.createElement("div");
    Object.assign(div.style, {
      "white-space": "nowrap",
      "display": "flex"
    });

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

    if (thread_id) {
      button.classList.add("show");
    }

    button.innerHTML = thread_id ? ICONS.COMMENT : ICONS.COMMENT_ADD;
    (button.querySelector("svg") as any).width = 16;
    (button.querySelector("svg") as any).height = 16;

    button.addEventListener("click", () => {
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
            thread_id = id;
            button.innerHTML = ICONS.COMMENT;
            button.classList.add("show");
          }}
          onResolvedThread={() => {
            thread_id = null;
            button.innerHTML = ICONS.COMMENT_ADD;
            button.classList.remove("show");
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
}
