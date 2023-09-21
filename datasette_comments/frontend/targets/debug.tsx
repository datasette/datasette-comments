import { h, render } from "preact";
import { Thread, CommentData } from "../components/Thread";

function profilePic() {
  return `data:image/svg+xml,%3Csvg width='24' height='24' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Crect width='24' height='24' fill='%23B400E1'/%3E %3Ctext fill='white' text-anchor='middle' alignment-baseline='middle' x='12' y='12' %3E A %3C/text%3E %3C/svg%3E%0A`;
}
let thread_id = null;
const comments: CommentData[] = [];
//window.comments = comments;
async function onRefreshComments(thread_id: string): Promise<CommentData[]> {
  return comments;
}
async function onNewThread(contents: string): Promise<string> {
  thread_id = Math.random().toString();
  comments.push({
    contents,
    author_profile_picture: profilePic(),
    author_name: "TODO",
    created_at: "TODO",
  });
  return thread_id;
}
async function onSubmitComment(
  thread_id: string,
  contents: string
): Promise<boolean> {
  comments.push({
    contents,
    author_profile_picture: profilePic(),
    author_name: "TODO",
    created_at: "TODO",
  });
  <text>df</text>;
  return true;
}
async function onMarkResolved(thread_id: string): Promise<boolean> {
  return true;
}

function main() {
  const THREAD_ROOT = document.body.appendChild(document.createElement("div"));
  render(
    <Thread
      /*target={{
        type: "table",
        database: "aaa",
        table: "bbb",
      }}*/
      initialId={null}
      marked_resolved={false}
      onRefreshComments={onRefreshComments}
      onNewThread={onNewThread}
      onSubmitComment={onSubmitComment}
      onMarkResolved={onMarkResolved}
    />,
    THREAD_ROOT
  );
}

document.addEventListener("DOMContentLoaded", main);
