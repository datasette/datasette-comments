import { h, createContext } from "preact";
import { useEffect, useState, useContext, useReducer } from "preact/hooks";
import { ICONS } from "../icons";
import {
  Api,
  CommentData,
  ReactionData,
  State,
  Action,
  apiReducer,
  CommentTargetType,
} from "../api";
import ms from "ms";

interface AuthorContext {
  author_actor_id: string;
  profile_photo_url: string;
}
const Author = createContext<AuthorContext>({
  author_actor_id: "",
  profile_photo_url: "",
});

function ReactionSection(props: {
  comment_id: string;
  initialReactions: ReactionData[];
}) {
  const { author_actor_id } = useContext(Author);
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
              (reactors.indexOf(author_actor_id) >= 0 ? " viewer-reacted" : "")
            }
            onClick={() => {
              if (
                reactionStats
                  .get(reaction)
                  ?.find((id) => id === author_actor_id)
              ) {
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
                return !stats ? true : stats.indexOf(author_actor_id) < 0;
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
            src={comment.author_profile_picture}
            style="border-radius: 50%"
          />
        </div>
        <div style="line-height: .9rem;">
          <strong>{comment.author_name}</strong>
          <div style="font-size: .8rem" title={comment.created_at}>
            {ms(comment.created_duration_seconds * 1000, { long: true })} ago
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
                  <a href={"#TODO"}>{node.value}</a>
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
function Draft(props: { onSubmitted: (contents: string) => void }) {
  const { profile_photo_url } = useContext<AuthorContext>(Author);
  const [value, setValue] = useState<string>("");
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
          <img src={profile_photo_url} width="25px"></img>
        </div>
        <div style="width: 100%; display: flex;">
          <textarea
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              setValue(target.value);

              // resize textarea on new lines
              target.style.height = "";
              target.style.height = target.scrollHeight + "px";
            }}
            value={value}
          ></textarea>
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
  //target: CommentTargetType;
  initialId: string | null;
  marked_resolved: boolean;
  author: AuthorContext;
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
        props.onNewThread(contents);
      });
    } else {
      Api.commentAdd(id, contents)
        .then(() => refreshComments())
        .catch(() => {});
    }
  }
  function onMarkAsResolved() {
    Api.threadMarkResolved(id)
      .then(() => {
        // TODO show message?
      })
      .catch(() => {});
  }

  return (
    <Author.Provider value={props.author}>
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
    </Author.Provider>
  );
}
export { CommentData };
