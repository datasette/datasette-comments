import { h, render } from "preact";
import { Thread, ThreadProps } from "../components/Thread";
import { Api, CommentData } from "../api";

const data = JSON.parse(
  document.getElementById("datasette-comments-data").textContent
) as {
  data: any[];
  actor_id: string;
  profile_photo_url: string;
};

async function onRefreshComments(thread_id: string): Promise<CommentData[]> {
  return Api.threadComments(thread_id).then((data) => data.data);
}

function main() {
  render(
    <div>
      {data.data.map((d) => (
        <Thread
          key={d.thread_id}
          initialId={d.thread_id}
          marked_resolved={false}
          onRefreshComments={onRefreshComments}
          onNewThread={async () => ""}
          onSubmitComment={async () => true}
          onMarkResolved={async () => true}
          author={{
            author_actor_id: data.actor_id,
            profile_photo_url: data.profile_photo_url,
          }}
        />
      ))}
    </div>,
    document.querySelector("#root")
  );
}
document.addEventListener("DOMContentLoaded", main);
