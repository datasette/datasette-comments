import "./activity_view.css";
import { h, render } from "preact";
import { DEFAULT_PROFILE_PICTURE } from "../../components/Thread";
import { Api, ActivtySearchResult, apiReducer, State, Action } from "../../api";
import { useReducer, useState } from "preact/hooks";
import { batch, computed, signal, useSignalEffect } from "@preact/signals";
import { Duration } from "../../components/Duration";
import { ICONS } from "../../icons";

function targetPath({
  target_type,
  target_database,
  target_table,
  target_row_ids,
  target_columns,
}: ActivtySearchResult) {
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

function ResultRow(props: { data: ActivtySearchResult; isLastRead: boolean }) {
  const { author, contents, created_at, created_duration_seconds } = props.data;
  const target = targetPath(props.data);
  return (
    <div
      style={{
        position: "relative",
        borderBottom: props.isLastRead ? "1px solid red" : null,
        paddingBottom: ".5rem",
      }}
    >
      <span>
        <div>
          <a
            style="font-weight:600; display: inline;"
            href={
              author.username
                ? `/-/datasette-comments/activity?author=${author.username}`
                : undefined
            }
          >
            <img
              src={author.profile_photo_url || DEFAULT_PROFILE_PICTURE}
              width="14px"
              style="border-radius: 50%; margin-right: 2px; display: inline;"
            />
            {author.name}
          </a>{" "}
          on{" "}
          <b style="font-weight: 600;">
            <a href={"/" + target}>{props.data.target_label ?? target}</a>
          </b>{" "}
          <Duration
            duration_ms={created_duration_seconds * 1000}
            timestamp={created_at}
          />
        </div>
        <div style="padding-left: 1rem;">
          <i style="font-style: italic">{contents}</i>
        </div>
      </span>
      {props.isLastRead && (
        <div style="position: absolute; right: 0; bottom: 0; background: red; color: white; font-size: 12px; line-height: 12px; padding: 2px 6px">
          ⌃New
        </div>
      )}
    </div>
  );
}

const STATE = {
  searchComments: signal(""),
  author: signal<string | null>(null),
  database: signal<string | null>(null),
  table: signal<string | null>(null),
  containsTag: signal<string[]>([]),
  isResolved: signal(false),
};

function applyUrlSearchParams(url: string): boolean {
  const params = new URL(url).searchParams;
  if (params.has("author")) STATE.author.value = params.get("author");
  if (params.has("database")) STATE.database.value = params.get("database");
  if (params.has("table")) STATE.table.value = params.get("table");
  if (params.has("sc")) STATE.searchComments.value = params.get("sc");
  if (params.has("tag")) STATE.containsTag.value = params.getAll("tag");
  if (params.has("resolved"))
    STATE.isResolved.value = params.get("resolved") === "1";
  return (
    params.has("author") ||
    params.has("database") ||
    params.has("table") ||
    params.has("sc") ||
    params.has("tag") ||
    params.has("resolved")
  );
}

const hasInitialUrlParams = applyUrlSearchParams(window.location.href);

const stateUrlParams = computed(() => {
  const params = new URLSearchParams();
  if (STATE.searchComments.value.length) {
    params.set("sc", STATE.searchComments.value);
  }
  if (STATE.author.value) {
    params.set("author", STATE.author.value);
  }
  if (STATE.database.value) {
    params.set("database", STATE.database.value);
  }
  if (STATE.table.value) {
    params.set("table", STATE.table.value);
  }
  params.set("resolved", STATE.isResolved.value ? "1" : "0");
  STATE.containsTag.value.forEach((tag) => params.append("tag", tag));
  return params;
});

function ActivitySearch() {
  const [searchComments, setSearchComments] = useState<string>(
    STATE.searchComments.value
  );
  const [author, setAuthor] = useState<string>(STATE.author.value);
  const [database, setDatabase] = useState<string>(STATE.database.value);
  const [table, setTable] = useState<string>(STATE.table.value);
  const [tags, setTags] = useState<string>(STATE.containsTag.value.join(","));
  const [isResolved, setIsResolved] = useState<boolean>(STATE.isResolved.value);

  function onSubmit() {
    batch(() => {
      STATE.searchComments.value = searchComments;
      STATE.containsTag.value = tags.length ? tags.split(",") : [];
      STATE.isResolved.value = isResolved;
      STATE.author.value = author;
      STATE.database.value = database;
      STATE.table.value = table;
    });
  }
  return (
    <div className="activity-search">
      <div className="activity-search-field">
        <label for="search-comments">Search comments</label>
        <input
          id="search-comments"
          type="text"
          value={searchComments}
          onKeyDown={(e) => e.key === "Enter" && onSubmit()}
          onInput={(e) => {
            setSearchComments((e.target as HTMLInputElement).value);
          }}
        />
      </div>
      <div className="activity-search-field">
        <label for="author">Author</label>
        <input
          id="author"
          type="text"
          value={author}
          onKeyDown={(e) => e.key === "Enter" && onSubmit()}
          onInput={(e) => {
            setAuthor((e.target as HTMLInputElement).value);
          }}
        />
      </div>
      <div className="activity-search-field">
        <label for="database">Database</label>
        <input
          id="database"
          type="text"
          value={database}
          onKeyDown={(e) => e.key === "Enter" && onSubmit()}
          onInput={(e) => {
            setDatabase((e.target as HTMLInputElement).value);
          }}
        />
      </div>
      <div className="activity-search-field">
        <label for="table">Table</label>
        <input
          id="table"
          type="text"
          value={table}
          onKeyDown={(e) => e.key === "Enter" && onSubmit()}
          onInput={(e) => {
            setTable((e.target as HTMLInputElement).value);
          }}
        />
      </div>
      <div className="activity-search-field">
        <label for="containing-tags">Containing tags</label>
        <div>
          <input
            id="containing-tags"
            type="text"
            value={tags}
            onKeyDown={(e) => e.key === "Enter" && onSubmit()}
            onInput={(e) => setTags((e.target as HTMLInputElement).value)}
          />
          <div class="help">Separate tags with commas</div>
        </div>
      </div>
      <div className="activity-search-field">
        <label for="is-resolved">Is resolved</label>
        <div>
          <input
            id="is-resolved"
            type="checkbox"
            checked={isResolved}
            onInput={(e) => {
              setIsResolved((e.target as HTMLInputElement).checked);
              // a bug: this onSubmit() doesn't have the right isResolved state yet
              //onSubmit();
            }}
          />
        </div>
      </div>
      <div className="activity-search-footer">
        <button onClick={onSubmit}>Submit</button>
        <div>
          <a href={`?${stateUrlParams}`}>Link to this search</a>
        </div>
      </div>
    </div>
  );
}

function ActivityView() {
  const [showFilters, setShowFilters] = useState<boolean>(hasInitialUrlParams);
  const [data, dispatch] = useReducer<
    State<ActivtySearchResult[], string>,
    Action<ActivtySearchResult[], string>
  >(apiReducer, { isLoading: true });

  useSignalEffect(() => {
    dispatch({ type: "init" });
    Api.activitySearch({
      searchComments: STATE.searchComments.value,
      containsTags: STATE.containsTag.value,
      isResolved: STATE.isResolved.value,
      author: STATE.author.value,
      database: STATE.database.value,
      table: STATE.table.value,
    })
      .then((data) => {
        dispatch({ type: "success", data: data.data });
      })
      .catch((error) => {
        dispatch({ type: "failure", error: error.toString() });
      });
  });

  /* TODO bring back the "last seen" indiciator on non-search feeds
  const lastSeen: string | null = localStorage.getItem(
    "datasette-comments-last-seen"
  );
  const idxLastSeen =
  lastSeen === null
      ? null
      : data.data.findIndex(
          (d, i) =>
            i < data.data.length - 1 &&
            d.created_at > lastSeen &&
            data.data[i + 1].created_at <= lastSeen
        );
  localStorage.setItem("datasette-comments-last-seen", data.data[0].created_at);*/

  return (
    <div className="datasette-comments-activity-view">
      <div className="header">
        <h1>Comments</h1>
        <button
          class="filter"
          dangerouslySetInnerHTML={{ __html: ICONS.TUNE }}
          onClick={() => setShowFilters((prev) => !prev)}
        ></button>
      </div>
      {showFilters ? <ActivitySearch /> : null}
      <div>
        {data.isLoading ? (
          "Loading..."
        ) : data.error ? (
          <div>Unknown error occurred.</div>
        ) : data.data.length > 0 ? (
          data.data.map((data, i) => (
            <ResultRow data={data} isLastRead={false /*i === idxLastSeen*/} />
          ))
        ) : (
          <p>No comments yet</p>
        )}
      </div>
    </div>
  );
}

async function main() {
  render(<ActivityView />, document.querySelector("#root"));
}
document.addEventListener("DOMContentLoaded", main);
