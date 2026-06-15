"use client";

import { useEffect, useRef, useState } from "react";
import type { Source } from "@/lib/types";

interface DrawerData {
  id: string;
  title: string;
  kind: string;
  text: string;
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

  return (
    <>
      <div className="drawer-backdrop" data-shown={shown} onClick={onClose} />
      <div className="drawer" data-shown={shown} role="dialog" aria-label="Source content">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
          <div>
            <div className="eyebrow" style={{ marginBottom: 4 }}>{current.kind}</div>
            <div className="display" style={{ fontSize: 22 }}>{current.title}</div>
          </div>
          <button onClick={onClose} className="icon-btn mono" aria-label="Close">
            ✕
          </button>
        </div>
        <div style={{ marginTop: 18 }}>
          {loading && <div className="mono" style={{ color: "var(--faint)" }}>Loading source…</div>}
          {data && <pre>{data.text}</pre>}
          {!loading && !data && (
            <div className="mono" style={{ color: "var(--faint)" }}>Source not found.</div>
          )}
        </div>
      </div>
    </>
  );
}
