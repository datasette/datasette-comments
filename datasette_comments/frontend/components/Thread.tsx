import { h } from "preact";
import { useEffect, useState } from "preact/hooks";
import { ICONS } from "../icons";
import { CommentData } from "../api";

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

      <div style={{ margin: ".25rem .5rem" }}>{props.comment.contents}</div>
      <div>
        {comment.render_nodes.map((node) => {
          switch (node.node_type) {
            case "raw":
              return <span>{node.value}</span>;
            case "mention":
              return (
                <span>
                  <a href={"#TODO"}>{node.value}</a>
                </span>
              );
            case "tag":
              return (
                <span>
                  <a href={"#TODO"}>{node.value}</a>
                </span>
              );
            case "url":
              return (
                <span>
                  <a href={node.value} target="_no">
                    {node.value}
                  </a>
                </span>
              );
          }
        })}
      </div>
      <button
        class="datasette-comments-add-reaction"
        dangerouslySetInnerHTML={{ __html: ICONS.ADD_REACTION }}
      ></button>
    </div>
  );
}
function Draft(props: { onSubmitted: (contents: string) => void }) {
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
          <img src="data:image/svg+xml,%3Csvg width='24' height='24' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='24' height='24' fill='%23B400E1'/%3E%3Cpath d='M9.86009 16H8.75213L11.9567 7.27273H13.0476L16.2521 16H15.1442L12.5362 8.65341H12.468L9.86009 16ZM10.2692 12.5909H14.7351V13.5284H10.2692V12.5909Z' fill='white'/%3E%3C/svg%3E%0A"></img>
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
  onRefreshComments: (thread_id: string) => Promise<CommentData[]>;
  onNewThread: (contents: string) => Promise<string>;
  onSubmitComment: (thread_id: string, contents: string) => Promise<boolean>;
  onMarkResolved: (thread_id: string) => Promise<boolean>;
}

export function Thread(props: ThreadProps) {
  const [show, setShow] = useState<boolean>(true);
  const [id, setId] = useState<string | null>(props.initialId || null);

  const [comments, setComments] = useState<CommentData[]>([]);
  function refreshComments() {
    if (id === null) return;
    props.onRefreshComments(id).then((comments) => setComments([...comments]));
  }
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
  );
}
export { CommentData };
