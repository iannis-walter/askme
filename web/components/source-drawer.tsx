"use client";

import { useEffect, useRef, useState } from "react";
import type { Source } from "@/lib/types";
import { fileLabel, issueFor } from "@/lib/issues";
import { Caption, IssueCover } from "@/components/comic";

interface DrawerData {
  id: string;
  title: string;
  kind: string;
  text?: string;
}

export function SourceDrawer({
  source,
  onClose,
}: {
  source: Source | null;
  onClose: () => void;
}) {
  const [data, setData] = useState<DrawerData | null>(null);
  const [loading, setLoading] = useState(false);
  // Keep the drawer mounted through its exit transition.
  const [render, setRender] = useState(false);
  const [shown, setShown] = useState(false);
  const lastSource = useRef<Source | null>(null);

  if (source) lastSource.current = source;
  const current = source ?? lastSource.current;

  // Drive the enter/exit transition off `source`.
  useEffect(() => {
    if (source) {
      setRender(true);
      const id = requestAnimationFrame(() => setShown(true));
      return () => cancelAnimationFrame(id);
    }
    setShown(false);
    const t = setTimeout(() => setRender(false), 320);
    return () => clearTimeout(t);
  }, [source]);

  // Fetch the source body when one is opened.
  useEffect(() => {
    if (!source) return;
    setData(null);
    setLoading(true);
    fetch(`/api/sources?id=${encodeURIComponent(source.id)}`)
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [source]);

  // Close on Escape.
  useEffect(() => {
    if (!source) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [source, onClose]);

  if (!render || !current) return null;
  const issue = issueFor(current);

  return (
    <>
      <div className="drawer-backdrop" data-shown={shown} onClick={onClose} />
      <div className="drawer" data-shown={shown} role="dialog" aria-label="Source content">
        <div className="drawer-head">
          <Caption>{issue ? `Back issue ${issue.no}` : "From the Files"}</Caption>
          <button onClick={onClose} className="drawer-close" aria-label="Close">
            Close ✕
          </button>
        </div>
        <div className="drawer-title-row">
          {issue && <IssueCover issue={issue} className="drawer-cover" />}
          <div>
            <h2 className="drawer-title">{issue?.title ?? current.title}</h2>
            <p className="drawer-file">{fileLabel(current)}</p>
          </div>
        </div>
        <div className="drawer-body">
          {loading && <p className="drawer-status">Pulling the file from the archives…</p>}
          {data?.text && <pre>{data.text}</pre>}
          {!loading && !data?.text && <p className="drawer-status">Source not found.</p>}
        </div>
      </div>
    </>
  );
}
