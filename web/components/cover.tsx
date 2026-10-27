"use client";

import { SOURCES_ON_FILE, SUGGESTED_PROMPTS } from "@/lib/profile";
import { FEATURED_ISSUES } from "@/lib/issues";
import { Balloon, Burst, IssueCover } from "@/components/comic";

// The empty state is the comic's cover: the masked hero, the hook, the
// teasers (suggested questions) and the back issues (projects).
export function Cover({ onAsk }: { onAsk: (text: string) => void }) {
  return (
    <section className="cover" aria-label="Cover">
      <div className="cover-price" aria-hidden="true">
        <span>No.</span>
        <b>1</b>
        <span>Oct 2026</span>
        <em>Free!</em>
      </div>

      <h1 className="cover-logo">Ask Iannis!</h1>
      <p className="cover-ribbon">The only profile that answers back!</p>

      <div className="cover-grid">
        <div className="cover-left">
          <Balloon tail="right" className="cover-balloon">
            <p>Go on. Ask me anything about my work. I&apos;ll show you where every answer comes from.</p>
          </Balloon>

          <h2 className="cover-teasers-title">In this issue:</h2>
          <ul className="cover-teasers">
            {SUGGESTED_PROMPTS.map((p) => (
              <li key={p.label}>
                <button type="button" className="teaser" onClick={() => onAsk(p.text)} title={p.text}>
                  {p.teaser}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="cover-right">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="cover-hero" src="/art/hero-avatar.png" alt="Iannis, drawn as a masked comic hero" />
          <Burst className="cover-burst">{SOURCES_ON_FILE} sources inside!</Burst>
          <div className="cover-blurb">
            <strong>Nothing invented!</strong>
            <span>Every claim gets an editor&apos;s note pointing to its source.</span>
          </div>
        </div>
      </div>

      <div className="cover-backissues" aria-label="Back issues">
        {FEATURED_ISSUES.map((issue, i) => (
          <button
            key={issue.slug}
            type="button"
            className="backissue"
            style={{ ["--r" as string]: `${[-6, 3, 8][i]}deg` }}
            onClick={() => onAsk(`Tell me about the ${issue.title} project.`)}
            aria-label={`Ask about ${issue.title}`}
          >
            <IssueCover issue={issue} />
          </button>
        ))}
      </div>
    </section>
  );
}
