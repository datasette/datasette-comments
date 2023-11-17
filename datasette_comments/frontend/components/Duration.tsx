import { h } from "preact";
import ms from "ms";

export function Duration(props: { duration_ms: number; timestamp: string }) {
  return (
    <span style="font-size: .8rem" title={props.timestamp}>
      {props.duration_ms < 1000
        ? "Just now"
        : `${ms(props.duration_ms, { long: true })} ago`}
    </span>
  );
}
