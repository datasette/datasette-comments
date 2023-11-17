import "./Thread.css";
import { h, createContext } from "preact";
import {
  useEffect,
  useState,
  useContext,
  useReducer,
  useRef,
} from "preact/hooks";
import { ICONS } from "../icons";
import {
  Api,
  CommentData,
  ReactionData,
  State,
  Action,
  apiReducer,
  CommentTargetType,
  Author,
} from "../api";
import { Duration } from "./Duration";

export const DEFAULT_PROFILE_PICTURE =
  "data:image/svg+xml,%3Csvg width='32' height='32' viewBox='0 0 32 32' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cmask id='mask0_136_16' style='mask-type:alpha' maskUnits='userSpaceOnUse' x='0' y='0' width='32' height='32'%3E%3Ccircle cx='16' cy='16' r='16' fill='%23D9D9D9'/%3E%3C/mask%3E%3Cg mask='url(%23mask0_136_16)'%3E%3Crect width='32' height='32' fill='%23D9D9D9'/%3E%3Ccircle cx='16' cy='13' r='7' fill='%236D6D6D'/%3E%3Ccircle cx='16' cy='13' r='7' fill='%236D6D6D'/%3E%3Ccircle cx='16' cy='13' r='7' fill='%236D6D6D'/%3E%3Ccircle cx='16' cy='13' r='7' fill='%236D6D6D'/%3E%3Cpath d='M30 32.5C23.25 32.5 23.9558 32.5 16.5 32.5C9.04416 32.5 9.75 32.5 3 32.5C3 25.0442 9.04416 19 16.5 19C23.9558 19 30 25.0442 30 32.5Z' fill='%236D6D6D'/%3E%3Cpath d='M30 32.5C23.25 32.5 23.9558 32.5 16.5 32.5C9.04416 32.5 9.75 32.5 3 32.5C3 25.0442 9.04416 19 16.5 19C23.9558 19 30 25.0442 30 32.5Z' fill='%236D6D6D'/%3E%3Cpath d='M30 32.5C23.25 32.5 23.9558 32.5 16.5 32.5C9.04416 32.5 9.75 32.5 3 32.5C3 25.0442 9.04416 19 16.5 19C23.9558 19 30 25.0442 30 32.5Z' fill='%236D6D6D'/%3E%3Cpath d='M30 32.5C23.25 32.5 23.9558 32.5 16.5 32.5C9.04416 32.5 9.75 32.5 3 32.5C3 25.0442 9.04416 19 16.5 19C23.9558 19 30 25.0442 30 32.5Z' fill='%236D6D6D'/%3E%3C/g%3E%3C/svg%3E%0A";
const AuthorContext = createContext<Author>({
  actor_id: "",
  name: "",
  profile_photo_url: "",
  username: null,
});

function ReactionSection(props: {
  comment_id: string;
  initialReactions: ReactionData[];
}) {
  const { actor_id } = useContext(AuthorContext);
  const [reactions, setReactions] = useState<ReactionData[]>(
    props.initialReactions
  );
  const [showReactionPopup, setShowReactionPopup] = useState<boolean>(false);

  function refreshReactions() {
    Api.reactions(props.comment_id).then((data) => setReactions(data));
  }
  function onClickAddReaction(e) {
    e.stopPropagation();
    setShowReactionPopup((prev) => !prev);
  }
  function onReact(reaction: string) {
    Api.reactionAdd(props.comment_id, reaction).then(() => refreshReactions());
  }

  // popup show/hide
  useEffect(() => {
    if (showReactionPopup) {
      // close popup when user clicks outside of it
      function onClick(e) {
        let current = e.target;
        while (current) {
          current = current.parentElement;
          if (current?.classList?.contains("datasette-comments-reactions")) {
            break;
          }
        }
        if (!current) {
          setShowReactionPopup(false);
        }
      }
      document.addEventListener("click", onClick);
      return () => {
        document.removeEventListener("click", onClick);
      };
    }
  }, [showReactionPopup, setShowReactionPopup]);

  const reactionStats = new Map<string, string[]>();
  for (const reaction of reactions) {
    if (reactionStats.has(reaction.reaction)) {
      reactionStats.set(reaction.reaction, [
        ...reactionStats.get(reaction.reaction),
        reaction.reactor_actor_id,
      ]);
    } else {
      reactionStats.set(reaction.reaction, [reaction.reactor_actor_id]);
    }
  }

  return (
    <div class="datasette-comments-reactions">
      {Array.from(reactionStats).map(([reaction, reactors], i) => (
        <div>
          <button
            key={i}
            class={
              "other-reactions" +
              (reactors.indexOf(actor_id) >= 0 ? " viewer-reacted" : "")
            }
            onClick={() => {
              if (reactionStats.get(reaction)?.find((id) => id === actor_id)) {
                Api.reactionRemove(props.comment_id, reaction).then(() =>
                  refreshReactions()
                );
              } else {
                onReact(reaction);
              }
            }}
          >
            {reaction} {reactors.length}
          </button>
        </div>
      ))}
      <div>
        <button
          class="datasette-comments-add-reaction"
          dangerouslySetInnerHTML={{ __html: ICONS.ADD_REACTION }}
          onClick={onClickAddReaction}
        ></button>
      </div>
      <div style="position:relative">
        {showReactionPopup && (
          <div className="popup">
            {["👍", "👎", "😀", "😕", "🎉", "❤️", "🚀", "👀"]
              .filter((reaction) => {
                const stats = reactionStats.get(reaction);
                return !stats ? true : stats.indexOf(actor_id) < 0;
              })
              .map((d) => (
                <button
                  key={d}
                  onClick={(e) => {
                    e.stopPropagation();
                    onReact(d);
                    setShowReactionPopup(false);
                  }}
                >
                  {d}
                </button>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Comment(props: { comment: CommentData }) {
  const { comment } = props;
  return (
    <div class="datasette-comments-comment">
      <div style="display: grid; grid-template-columns: 30px auto;">
        <div>
          <img
            width="25px"
            src={comment.author.profile_photo_url || DEFAULT_PROFILE_PICTURE}
            style="border-radius: 50%"
          />
        </div>
        <div style="line-height: .9rem;">
          <strong>{comment.author.name}</strong>
          <div>
            <Duration
              duration_ms={comment.created_duration_seconds * 1000}
              timestamp={comment.created_at}
            />
          </div>
        </div>
      </div>

      <div style={{ margin: ".25rem .5rem" }}>
        {comment.render_nodes.map((node) => {
          switch (node.node_type) {
            case "linebreak":
              return <br />;
            case "raw":
              return <span>{node.value}</span>;
            case "mention":
              return (
                <span class="mention">
                  <a
                    href={`/-/datasette-comments/activity?author=${node.value.slice(
                      1
                    )}`}
                  >
                    {node.value}
                  </a>
                </span>
              );
            case "tag":
              return (
                <span class="tag">
                  <a href={`/-/datasette-comments/tags/${node.value.slice(1)}`}>
                    {node.value}
                  </a>
                </span>
              );
            case "url":
              return (
                <span class="url">
                  <a href={node.value} target="_no">
                    {node.value}
                  </a>
                </span>
              );
          }
        })}
      </div>
      <ReactionSection
        comment_id={comment.id}
        initialReactions={comment.reactions}
      />
    </div>
  );
}
function autocompleteOptions(
  textarea: HTMLTextAreaElement
): { type: "tag" | "mention"; prefix: string } | null {
  const { value, selectionStart, selectionEnd } = textarea;
  const cursorIdx = selectionStart;

  for (let i = cursorIdx - 1; i >= 0; i--) {
    if (value[i] === " ") return;
    if (value[i] === "#") {
      return { type: "tag", prefix: value.substring(i + 1, cursorIdx) };
    }
    if (value[i] === "@") {
      return { type: "mention", prefix: value.substring(i + 1, cursorIdx) };
    }
  }
}

function MentionSuggestion(props: {
  author: Author;
  onSelect: (author: Author) => void;
}) {
  return (
    <div
      onClick={() => props.onSelect(props.author)}
      className="mention-suggestion"
    >
      <img
        style="width: 1rem; height: 1rem;"
        src={props.author.profile_photo_url ?? DEFAULT_PROFILE_PICTURE}
      />
      <span style="font-weight: 600;">{props.author.name}</span>
      <span>({props.author.username})</span>
    </div>
  );
}
function Draft(props: { onSubmitted: (contents: string) => void }) {
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const { profile_photo_url } = useContext<Author>(AuthorContext);
  const [value, setValue] = useState<string>("");
  const [suggestions, setSuggestions] = useState<Author[]>([]);
  function onCancel() {
    setValue("");
  }
  function onAddComment() {
    props.onSubmitted(value);
    setValue("");
  }
  return (
    <div class="datasette-comments-draft">
      <div style="display: flex;">
        <div style="padding: 4px;">
          <img
            src={profile_photo_url || DEFAULT_PROFILE_PICTURE}
            width="25px"
          ></img>
        </div>
        <div style="width: 100%">
          <div>
            <textarea
              ref={inputRef}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                setValue(target.value);

                // resize textarea on new lines
                target.style.height = "";
                target.style.height = target.scrollHeight + "px";

                const x = autocompleteOptions(target);
                if (x) {
                  if (x.type === "mention") {
                    Api.autocomplete_mentions(x.prefix).then((data) => {
                      setSuggestions(data.suggestions.map((d) => d.author));
                    });
                  }
                } else {
                  setSuggestions([]);
                }
              }}
              value={value}
              style="width: calc(100% - 1rem)"
            ></textarea>
          </div>
          <div>
            {suggestions.map((suggestion) => (
              <MentionSuggestion
                author={suggestion}
                onSelect={(author) => {
                  const { selectionEnd, value } = inputRef.current;
                  let mentionStartIdx;
                  for (let i = selectionEnd; i >= 0; i--) {
                    if (value[i] === "@") {
                      mentionStartIdx = i;
                    } else if (value[i] === " ") {
                      break;
                    }
                  }
                  if (mentionStartIdx === undefined) {
                    return;
                  }
                  const newValue = `${value.substring(0, mentionStartIdx)}@${
                    author.username
                  } ${value.substring(selectionEnd)}`;

                  setValue(newValue);
                  inputRef.current.value = newValue;
                  inputRef.current.selectionEnd =
                    mentionStartIdx +
                    "@".length +
                    author.username.length +
                    " ".length;
                  inputRef.current.focus();
                  setSuggestions([]);
                }}
              />
            ))}
          </div>
        </div>
      </div>
      <div class="draft-bottom-drawer">
        <div>
          <button class="draft-cancel-button" onClick={onCancel}>
            Cancel
          </button>
          <button
            class="draft-add-button"
            onClick={onAddComment}
            disabled={value === ""}
          >
            Add comment
          </button>
        </div>
      </div>
    </div>
  );
}

export interface ThreadProps {
  initialId: string | null;
  author: Author;
  target: CommentTargetType;
  onNewThread?: (contents: string) => Promise<string>;
}

export function Thread(props: ThreadProps) {
  const [id, setId] = useState<string | null>(props.initialId || null);

  const [comments, dispatch] = useReducer<
    State<CommentData[], string>,
    Action<CommentData[], string>
  >(apiReducer, {
    isLoading: false,
  });

  function refreshComments() {
    if (id === null) return;
    dispatch({ type: "init" });
    Api.threadComments(id)
      .then((data) => {
        dispatch({ type: "success", data: data.data });
      })
      .catch((error) => {
        dispatch({ type: "failure", error: "TODO" });
      });
  }

  // watch for prop.initialId changes
  useEffect(() => {
    setId(props.initialId);
  }, [props.initialId, setId]);

  // refresh comments whenever id changes
  useEffect(() => {
    refreshComments();
  }, [id]);

  function onNewComment(contents: string) {
    if (id === null) {
      Api.threadNew(props.target, contents).then(({ thread_id }) => {
        setId(thread_id);
        if (props.onNewThread) props.onNewThread(contents);
      });
    } else {
      Api.commentAdd(id, contents)
        .then(() => refreshComments())
        .catch(() => {});
    }
  }
  function onMarkAsResolved() {
    const confirmed = window.confirm(
      "Are you sure you want to mark this thread resolved? You can still access resolved thread on the Comments page."
    );
    if (confirmed) {
      Api.threadMarkResolved(id)
        .then(() => {
          // TODO show message?
        })
        .catch(() => {});
    }
  }

  return (
    <AuthorContext.Provider value={props.author}>
      <div className="datasette-comments-thread">
        <div className="datasette-comments-thread-meta">
          {id !== null && (
            <button
              class="mark-resolved-button"
              onClick={() => onMarkAsResolved()}
            >
              <span
                dangerouslySetInnerHTML={{ __html: ICONS.CHECK_CIRCLE }}
              ></span>
            </button>
          )}
        </div>
        <div className="datasette-comments-thread-comments">
          {comments.isLoading ? (
            <div style="text-align:center; margin: 1rem;">Loading...</div>
          ) : comments.error ? (
            comments.error
          ) : (
            comments.data?.map((comment) => <Comment comment={comment} />)
          )}
        </div>
        <div>
          <Draft onSubmitted={onNewComment} />
        </div>
      </div>
    </AuthorContext.Provider>
  );
}
export { CommentData };
