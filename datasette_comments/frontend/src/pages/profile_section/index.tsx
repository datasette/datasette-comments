import { h, render } from "preact";
import { useState, useEffect } from "preact/hooks";
import register from "preact-custom-element";

function timeAgo(seconds: number): string {
  if (seconds < 60) return "just now";
  if (seconds < 3600) return Math.floor(seconds / 60) + "m ago";
  if (seconds < 86400) return Math.floor(seconds / 3600) + "h ago";
  return Math.floor(seconds / 86400) + "d ago";
}

interface ActivityItem {
  type: "comment" | "reaction";
  created_at: string;
  created_duration_seconds: number;
  target_type: string;
  target_database?: string;
  target_table?: string;
  target_row_ids?: string;
  target_label?: string;
  contents?: string;
  reaction?: string;
  comment_contents?: string;
}

function targetPath(row: ActivityItem): string {
  const db = row.target_database;
  const table = row.target_table;
  const rowIds = row.target_row_ids;
  switch (row.target_type) {
    case "database":
      return db || "";
    case "table":
      return db + "/" + table;
    case "row": {
      let ids = "";
      try {
        const parsed = JSON.parse(rowIds || "");
        ids = Array.isArray(parsed) ? parsed.join(",") : String(parsed);
      } catch {
        ids = rowIds || "";
      }
      return db + "/" + table + "/" + ids;
    }
    default:
      return db + "/" + (table || "");
  }
}

function CommentItem({ item }: { item: ActivityItem }) {
  return (
    <div style="border-bottom: 1px solid #eee; padding-bottom: 10px;">
      <div style="font-size: 0.85rem; color: #666; margin-bottom: 4px;">
        on{" "}
        <a
          href={"/" + targetPath(item)}
          style="font-weight: 600; color: #333;"
        >
          {item.target_label || targetPath(item)}
        </a>{" "}
        <span style="color: #999;">
          {timeAgo(item.created_duration_seconds)}
        </span>
      </div>
      <div style="font-size: 0.9rem; font-style: italic; padding-left: 8px;">
        {item.contents}
      </div>
    </div>
  );
}

function ReactionItem({ item }: { item: ActivityItem }) {
  return (
    <div style="border-bottom: 1px solid #eee; padding-bottom: 10px;">
      <div style="font-size: 0.85rem; color: #666; margin-bottom: 4px;">
        reacted {item.reaction} on{" "}
        <a
          href={"/" + targetPath(item)}
          style="font-weight: 600; color: #333;"
        >
          {item.target_label || targetPath(item)}
        </a>{" "}
        <span style="color: #999;">
          {timeAgo(item.created_duration_seconds)}
        </span>
      </div>
      <div style="font-size: 0.9rem; color: #888; padding-left: 8px;">
        {item.comment_contents}
      </div>
    </div>
  );
}

function ProfileComments(props: {
  "actor-id": string;
  "is-own-profile"?: string;
}) {
  const actorId = props["actor-id"];
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("actorId", actorId);
    fetch(`/-/datasette-comments/api/profile_activity?${params}`, {
      credentials: "include",
    })
      .then((r) => r.json())
      .then((data) => {
        setItems(data.data || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [actorId]);

  if (loading) {
    return <p style="color: #888; font-size: 0.9rem;">Loading...</p>;
  }

  if (items.length === 0) {
    return (
      <p style="color: #888; font-size: 0.9rem; margin: 0;">
        No activity yet.
      </p>
    );
  }

  return (
    <div style="display: flex; flex-direction: column; gap: 12px;">
      {items.slice(0, 20).map((item, i) =>
        item.type === "reaction" ? (
          <ReactionItem key={i} item={item} />
        ) : (
          <CommentItem key={i} item={item} />
        ),
      )}
      {items.length > 20 && (
        <a
          href={
            "/-/datasette-comments/activity?authorActorId=" +
            encodeURIComponent(actorId)
          }
          style="font-size: 0.85rem;"
        >
          View all activity
        </a>
      )}
    </div>
  );
}

register(ProfileComments, "profile-comments", ["actor-id", "is-own-profile"], {
  shadow: false,
});
