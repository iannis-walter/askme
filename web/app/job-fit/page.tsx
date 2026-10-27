"use client";

import { useState } from "react";
import type { JobFitResult, Source } from "@/lib/types";
import { issueByName } from "@/lib/issues";
import { EditorsNotes } from "@/components/editors-notes";
import { SourceDrawer } from "@/components/source-drawer";
import { Markdown } from "@/components/markdown";
import { Balloon, IssueCover, Panel } from "@/components/comic";

// Job fit as a special crossover issue: the role meets the hero, and the
// findings are laid out panel by panel.
export default function JobFitPage() {
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<JobFitResult | null>(null);
  const [openSource, setOpenSource] = useState<Source | null>(null);

  async function run() {
    if (!jd.trim() || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch("/api/job-fit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_description: jd }),
      });
      setResult(await res.json());
    } catch {
      setResult({
        summary: "Something went wrong. Check the backend and the Mistral key.",
        strengths: [],
        gaps: [],
        relevant_projects: [],
        pitch: "",
        sources: [],
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="stage-scroll">
      <div className="comic-page jobfit">
        <Panel tone="blue" caption="Special crossover issue!" className="panel-crossover">
          <h1 className="crossover-title">Crossover!</h1>
          <div className="crossover-row">
            <Balloon tail="right" className="crossover-balloon">
              <p>
                Paste a role. I&apos;ll show you where I land: strengths, honest gaps, the projects worth
                showing, and a pitch made for it.
              </p>
            </Balloon>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className="crossover-hero" src="/art/hero-avatar.png" alt="" aria-hidden="true" />
          </div>
        </Panel>

        <Panel tone="cream" caption="The role:" className="panel-role">
          <textarea
            className="role-input"
            aria-label="Job description"
            placeholder="Paste the full job description here…"
            value={jd}
            onChange={(e) => setJd(e.target.value)}
          />
          <button type="button" className="btn-pow" onClick={run} disabled={loading || !jd.trim()}>
            {loading ? "Analysing…" : "Run fit analysis!"}
          </button>
        </Panel>

        {loading && (
          <Panel tone="yellow" className="panel-loading">
            <p className="sfx sfx--crunch" role="status">
              Crunch! Crunch! Reading the files…
            </p>
          </Panel>
        )}

        {result && !loading && <Findings result={result} onOpen={setOpenSource} />}
      </div>
      <SourceDrawer source={openSource} onClose={() => setOpenSource(null)} />
    </main>
  );
}

function Findings({ result, onOpen }: { result: JobFitResult; onOpen: (s: Source) => void }) {
  const issues = result.relevant_projects.map((p) => ({ name: p, issue: issueByName(p) }));
  return (
    <div className="findings">
      <Panel tone="yellow" caption="Overall fit" className="panel-finding panel-summary">
        <Balloon tail="none" className="finding-balloon">
          <Markdown>{result.summary}</Markdown>
        </Balloon>
      </Panel>

      <div className="tier-row">
        {result.strengths.length > 0 && (
          <Panel tone="cream" caption="Strongest matches" className="panel-finding">
            <ul className="finding-list finding-list--yes">
              {result.strengths.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </Panel>
        )}
        {result.gaps.length > 0 && (
          <Panel tone="blue" caption="Honest gaps" className="panel-finding panel-gaps">
            <ul className="finding-list finding-list--gap">
              {result.gaps.map((g, i) => (
                <li key={i}>{g}</li>
              ))}
            </ul>
          </Panel>
        )}
      </div>

      {issues.length > 0 && (
        <Panel tone="paper" caption="Projects to show" className="panel-finding">
          <div className="issue-row">
            {issues.map(({ name, issue }, i) =>
              issue ? (
                <IssueCover key={i} issue={issue} className="issue--row" />
              ) : (
                <span key={i} className="pill">
                  {name}
                </span>
              )
            )}
          </div>
        </Panel>
      )}

      {result.pitch && (
        <Panel tone="yellow" caption="Suggested pitch" className="panel-finding panel-pitch">
          <div className="answer-wrap">
            <Balloon tail="right" className="a-balloon">
              <div className="answer">
                <Markdown>{result.pitch}</Markdown>
              </div>
            </Balloon>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className="answer-hero" src="/art/hero-avatar.png" alt="" aria-hidden="true" />
          </div>
          <EditorsNotes sources={result.sources} onOpen={onOpen} />
        </Panel>
      )}

      {!result.pitch && result.sources.length > 0 && (
        <Panel tone="paper" caption="Sources" className="panel-finding">
          <EditorsNotes sources={result.sources} onOpen={onOpen} />
        </Panel>
      )}
    </div>
  );
}
