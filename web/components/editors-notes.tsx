"use client";

import type { Source } from "@/lib/types";
import { fileLabel, noteMarker, noteText } from "@/lib/issues";

// Citations as comic editor's notes: "*See Issue #04: Hyperion! —Ed."
// Each note opens the source it points to.
export function EditorsNotes({
  sources,
  onOpen,
}: {
  sources: Source[];
  onOpen: (s: Source) => void;
}) {
  if (!sources?.length) return null;
  return (
    <div className="notes" aria-label={`${sources.length} sources cited`}>
      {sources.map((s, i) => (
        <button
          key={s.id}
          type="button"
          className="note"
          style={{ ["--i" as string]: i }}
          onClick={() => onOpen(s)}
          title={s.title}
        >
          <span className="note-text">
            <span className="note-marker">{noteMarker(i)}</span>
            {noteText(s)} <span className="note-ed">—Ed.</span>
          </span>
          <span className="note-file">{fileLabel(s)}</span>
        </button>
      ))}
    </div>
  );
}
