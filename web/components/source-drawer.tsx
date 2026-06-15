"use client";

import { useEffect, useState } from "react";
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

  if (!source) return null;

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer" role="dialog" aria-label="Source content">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
          <div>
            <div className="eyebrow" style={{ marginBottom: 4 }}>{source.kind}</div>
            <div className="display" style={{ fontSize: 22 }}>{source.title}</div>
          </div>
          <button
            onClick={onClose}
            className="mono"
            style={{ background: "none", border: "none", color: "var(--muted)", cursor: "pointer", fontSize: 18 }}
            aria-label="Close"
          >
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
