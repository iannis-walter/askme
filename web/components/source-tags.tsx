"use client";

import type { Source } from "@/lib/types";

const FILE_NAME: Record<string, (id: string) => string> = {
  bio: () => "bio.json",
  skills: () => "skills.json",
  experience: () => "experience.json",
  faq: () => "faq.json",
  project: (id) => `projects/${id}.md`,
  role: (id) => `roles/${id}.md`,
};

function fileLabel(s: Source): string {
  const fn = FILE_NAME[s.kind];
  return fn ? fn(s.id) : s.id;
}

export function SourceTags({
  sources,
  onOpen,
}: {
  sources: Source[];
  onOpen: (s: Source) => void;
}) {
  if (!sources?.length) return null;
  return (
    <div className="sources-row">
      <span className="grounded">
        <span className="dot" />
        Grounded · {sources.length} {sources.length === 1 ? "source" : "sources"}
      </span>
      {sources.map((s) => (
        <button key={s.id} className="source-tag" onClick={() => onOpen(s)} title={s.title}>
          {fileLabel(s)}
        </button>
      ))}
    </div>
  );
}
