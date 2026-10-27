import type { ReactNode, CSSProperties } from "react";
import type { Issue } from "@/lib/issues";

// Comic-book primitives shared by the cover, the page and the job-fit issue.

export function Caption({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`caption ${className}`}>{children}</div>;
}

export function Panel({
  tone = "paper",
  caption,
  className = "",
  children,
  style,
}: {
  tone?: "paper" | "blue" | "yellow" | "cream";
  caption?: ReactNode;
  className?: string;
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <section className={`panel panel--${tone} ${className}`} style={style}>
      {caption ? <Caption className="panel-caption">{caption}</Caption> : null}
      {children}
    </section>
  );
}

export function Balloon({
  tail = "left",
  className = "",
  children,
}: {
  tail?: "left" | "right" | "none";
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={`balloon balloon--${tail} ${className}`}>
      {children}
      {tail !== "none" && (
        <svg className="balloon-tail" width="56" height="52" viewBox="0 0 56 52" aria-hidden="true">
          <path d={tail === "left" ? "M4 0 L8 49 L50 0" : "M52 0 L48 49 L6 0"} />
        </svg>
      )}
    </div>
  );
}

const BURST =
  "50,0 58,14 73,6 74,23 91,21 85,37 100,44 88,56 97,71 80,74 82,91 66,86 59,100 50,88 41,100 34,86 18,91 20,74 3,71 12,56 0,44 15,37 9,21 26,23 27,6 42,14";

export function Burst({
  children,
  className = "",
  color = "red",
}: {
  children: ReactNode;
  className?: string;
  color?: "red" | "yellow" | "orange";
}) {
  return (
    <span className={`burst burst--${color} ${className}`}>
      <svg viewBox="0 0 100 100" aria-hidden="true">
        <polygon points={BURST} />
      </svg>
      <span className="burst-text">{children}</span>
    </span>
  );
}

export function IssueCover({
  issue,
  stamped = false,
  className = "",
  style,
}: {
  issue: Issue;
  stamped?: boolean;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <span className={`issue ${className}`} style={style}>
      <span className="issue-mast">Ask Iannis!</span>
      <span className="issue-no">{issue.no}</span>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="issue-art" src={issue.art} alt="" loading="lazy" decoding="async" />
      <span className="issue-title">{issue.title}</span>
      <span className="issue-tagline">{issue.tagline}</span>
      {stamped && <Burst className="issue-stamp">Sourced!</Burst>}
    </span>
  );
}
