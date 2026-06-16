"use client";

import { useState } from "react";
import type { JobFitResult, Source } from "@/lib/types";
import { SourceTags } from "@/components/source-tags";
import { SourceDrawer } from "@/components/source-drawer";
import { Markdown } from "@/components/markdown";

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
      <div className="jobfit">
        <div className="eyebrow" style={{ marginBottom: 14 }}>Job fit</div>
        <h1 className="display" style={{ fontSize: "clamp(34px, 5vw, 58px)", lineHeight: 1.04 }}>
          Paste a role.<br />
          See <em style={{ fontStyle: "italic", color: "var(--ember)" }}>where it lands.</em>
        </h1>
        <p style={{ color: "var(--muted)", marginTop: 16, maxWidth: 560, fontSize: 19 }}>
          Drop in a job description. The candidate&apos;s profile is matched against
          it — strengths, honest gaps, the projects worth showing, and a tailored pitch.
        </p>

        <textarea
          className="textarea-big"
          style={{ marginTop: 20 }}
          placeholder="Paste the full job description here…"
          value={jd}
          onChange={(e) => setJd(e.target.value)}
        />
        <div style={{ marginTop: 14 }}>
          <button className="btn-primary" onClick={run} disabled={loading || !jd.trim()}>
            {loading ? "Analysing…" : "Run fit analysis"}
          </button>
        </div>

        {loading && (
          <div className="report-card" style={{ marginTop: 24 }}>
            <div className="skeleton" style={{ width: "60%", marginBottom: 12 }} />
            <div className="skeleton" style={{ width: "90%", marginBottom: 8 }} />
            <div className="skeleton" style={{ width: "80%" }} />
          </div>
        )}

        {result && !loading && (
          <div style={{ marginTop: 24 }}>
            <div className="report-card">
              <h3>Overall fit</h3>
              <Markdown>{result.summary}</Markdown>
            </div>

            {result.strengths.length > 0 && (
              <div className="report-card">
                <h3>Strongest matches</h3>
                <ul>{result.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </div>
            )}

            {result.gaps.length > 0 && (
              <div className="report-card">
                <h3>Honest gaps</h3>
                <ul>{result.gaps.map((g, i) => <li key={i}>{g}</li>)}</ul>
              </div>
            )}

            {result.relevant_projects.length > 0 && (
              <div className="report-card">
                <h3>Projects to show</h3>
                <div>{result.relevant_projects.map((p, i) => <span key={i} className="pill">{p}</span>)}</div>
              </div>
            )}

            {result.pitch && (
              <div className="report-card">
                <h3>Suggested pitch</h3>
                <Markdown>{result.pitch}</Markdown>
              </div>
            )}

            {result.sources.length > 0 && (
              <div style={{ marginTop: 14 }}>
                <SourceTags sources={result.sources} onOpen={setOpenSource} />
              </div>
            )}
          </div>
        )}
      </div>
      <SourceDrawer source={openSource} onClose={() => setOpenSource(null)} />
    </main>
  );
}
