import { h, createContext } from "preact";
import { useEffect, useState, useContext } from "preact/hooks";
import { ICONS } from "../icons";
import { Api, CommentData, ReactionData } from "../api";

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
    setShowReactionPopup(true);
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
            style={{
              border:
                reactors.indexOf(author_actor_id) >= 0
                  ? "1px solid red"
                  : "1px solid grey",
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
          <div style="font-size: .8rem">{comment.created_at}</div>
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
          <img src={profile_photo_url} width="22px"></img>
        </div>
        <div style="width: 100%;">
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
  onRefreshComments: (thread_id: string) => Promise<CommentData[]>;
  onNewThread: (contents: string) => Promise<string>;
  onSubmitComment: (thread_id: string, contents: string) => Promise<boolean>;
  onMarkResolved: (thread_id: string) => Promise<boolean>;
}

export function Thread(props: ThreadProps) {
  const [id, setId] = useState<string | null>(props.initialId || null);
  const [comments, setComments] = useState<CommentData[]>([]);

  function refreshComments() {
    if (id === null) return;
    props.onRefreshComments(id).then((comments) => setComments([...comments]));
  }
  useEffect(() => {
    setId(props.initialId);
  }, [props.initialId, setId]);

  useEffect(() => {
    refreshComments();
  }, [id, setComments]);

  function onNewComment(contents: string) {
    if (id === null) {
      props
        .onNewThread(contents)
        .then((id) => setId(id))
        .catch(() => {});
    } else {
      props
        .onSubmitComment(id, contents)
        .then(() => refreshComments())
        .catch(() => {});
    }
  }
  function onMarkAsResolved() {
    props
      .onMarkResolved(id)
      .then(() => {})
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
              Mark as resolved
            </button>
          )}
        </div>
        <div className="datasette-comments-thread-comments">
          {comments.map((comment) => (
            <Comment comment={comment} />
          ))}
        </div>
        <div>
          <Draft onSubmitted={onNewComment} />
        </div>
      </div>
    </Author.Provider>
  );
}
export { CommentData };
