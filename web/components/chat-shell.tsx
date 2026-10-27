"use client";

import { useEffect, useRef, useState } from "react";
import type { AgentStep, Message, Source } from "@/lib/types";
import { issueFor, type Issue } from "@/lib/issues";
import { EditorsNotes } from "@/components/editors-notes";
import { SourceDrawer } from "@/components/source-drawer";
import { Markdown } from "@/components/markdown";
import { Cover } from "@/components/cover";
import { Balloon, Burst, IssueCover, Panel } from "@/components/comic";

export function ChatShell() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [agentMode, setAgentMode] = useState(false);
  const [openSource, setOpenSource] = useState<Source | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // The cover reads top-down; only the comic page follows the latest panel.
    if (messages.length) scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    setBusy(true);
    setInput("");

    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [
      ...prev,
      { role: "user", content: message },
      { role: "assistant", content: "", sources: [], steps: [], streaming: true },
    ]);

    try {
      const res = await fetch(agentMode ? "/api/chat/agent" : "/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, conversation: history }),
      });
      if (!res.body) throw new Error("No response stream");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const update = (fn: (m: Message) => Message) =>
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = fn(next[next.length - 1]);
          return next;
        });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx: number;
        while ((idx = buffer.indexOf("\n")) >= 0) {
          const line = buffer.slice(0, idx).trim();
          buffer = buffer.slice(idx + 1);
          if (!line) continue;
          let evt: {
            type: string;
            text?: string;
            sources?: Source[];
            tool?: string;
            args?: Record<string, unknown>;
            ok?: boolean;
            error?: string | null;
          };
          try {
            evt = JSON.parse(line);
          } catch {
            continue;
          }
          if (evt.type === "sources") {
            update((m) => ({ ...m, sources: evt.sources ?? [] }));
          } else if (evt.type === "step") {
            const step: AgentStep = {
              tool: evt.tool ?? "",
              args: evt.args ?? {},
              ok: evt.ok ?? true,
              error: evt.error,
            };
            update((m) => ({ ...m, steps: [...(m.steps ?? []), step] }));
          } else if (evt.type === "delta") {
            update((m) => ({ ...m, content: m.content + (evt.text ?? "") }));
          } else if (evt.type === "done") {
            update((m) => ({ ...m, streaming: false }));
          }
        }
      }
      update((m) => ({ ...m, streaming: false }));
    } catch {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          content:
            "Something went wrong reaching the assistant. Check that the backend is running and the Mistral key is set.",
          streaming: false,
        };
        return next;
      });
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  function autosize() {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }

  // Pair each question with the answer that follows it: one tier per turn.
  const turns: { q: Message; a?: Message }[] = [];
  messages.forEach((m, i) => {
    if (m.role === "user") turns.push({ q: m, a: messages[i + 1] });
  });

  return (
    <main className="stage">
      <div className="stage-scroll" ref={scrollRef}>
        {turns.length === 0 ? (
          <Cover onAsk={send} />
        ) : (
          <div className="comic-page">
            {turns.map((t, i) => (
              <Tier key={i} index={i} q={t.q} a={t.a} onOpen={setOpenSource} />
            ))}
          </div>
        )}
      </div>

      <div className="composer-bar">
        <div className="composer">
          <Balloon tail="left" className="composer-field">
            <textarea
              ref={taRef}
              value={input}
              placeholder="Your question here, recruiter…"
              aria-label="Your question"
              onChange={(e) => {
                setInput(e.target.value);
                autosize();
              }}
              onKeyDown={onKeyDown}
              rows={1}
            />
          </Balloon>
          <div className="composer-side">
            <div
              className="modes"
              role="group"
              aria-label="Answer mode"
              title="Agent loop: the model calls tools in a loop (searching the knowledge base itself, possibly several times) instead of a single-shot answer. The searches are shown in their own panel."
            >
              <button type="button" className="mode" aria-pressed={!agentMode} onClick={() => setAgentMode(false)}>
                One-shot
              </button>
              <button type="button" className="mode" aria-pressed={agentMode} onClick={() => setAgentMode(true)}>
                Agent loop
              </button>
            </div>
            <span className="composer-hint">
              {agentMode ? "tool-use loop · searches shown" : "single-shot · one retrieval"}
            </span>
          </div>
          <button
            type="button"
            className="ask-btn"
            disabled={busy || !input.trim()}
            onClick={() => send(input)}
            aria-label="Ask"
          >
            <Burst>Ask!</Burst>
          </button>
        </div>
      </div>

      <SourceDrawer source={openSource} onClose={() => setOpenSource(null)} />
    </main>
  );
}

function formatArgs(args: Record<string, unknown>): string {
  return Object.values(args)
    .map((v) => JSON.stringify(v))
    .join(", ");
}

// One question and its answer, laid out as a tier of comic panels.
function Tier({
  index,
  q,
  a,
  onOpen,
}: {
  index: number;
  q: Message;
  a?: Message;
  onOpen: (s: Source) => void;
}) {
  const steps = a?.steps ?? [];
  const sources = a?.sources ?? [];
  const cited: { issue: Issue; source: Source }[] = [];
  for (const s of sources) {
    const issue = issueFor(s);
    if (issue && !cited.some((c) => c.issue.slug === issue.slug)) cited.push({ issue, source: s });
  }

  return (
    <article className="tier">
      <div className={`tier-row ${steps.length ? "" : "tier-row--solo"}`}>
        <Panel
          tone="blue"
          caption={index === 0 ? "A recruiter asks…" : "Then the recruiter asks…"}
          className="panel-question"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="panel-mic" src="/art/hero-mic.png" alt="" aria-hidden="true" />
          <Balloon tail="left" className="q-balloon">
            <p>{q.content}</p>
          </Balloon>
        </Panel>
        {steps.length > 0 && (
          <Panel tone="cream" caption="Meanwhile, in the archives…" className="panel-steps">
            <ol className="calls">
              {steps.map((s, i) => (
                <li
                  key={i}
                  className={`call ${s.ok ? "" : "call--failed"}`}
                  style={{ ["--i" as string]: i }}
                  title={s.error ?? JSON.stringify(s.args)}
                >
                  <span className="call-no">{s.ok ? i + 1 : "✕"}</span>
                  <code>
                    {s.tool}({formatArgs(s.args)})
                  </code>
                </li>
              ))}
            </ol>
            <span className="sfx sfx--riffle" aria-hidden="true">
              Riffle! Riffle!
            </span>
          </Panel>
        )}
      </div>

      {a && (
        <div className={`tier-row ${cited.length ? "" : "tier-row--solo"}`}>
          <Panel tone="yellow" caption="Iannis answers:" className="panel-answer">
            <div className="answer-wrap">
              <Balloon tail="right" className="a-balloon">
                <div className={`answer ${a.streaming && !a.content ? "caret" : ""}`}>
                  <Markdown>{a.content}</Markdown>
                  {a.streaming && a.content ? <span className="caret" /> : null}
                </div>
              </Balloon>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img className="answer-hero" src="/art/hero-avatar.png" alt="" aria-hidden="true" />
            </div>
            <EditorsNotes sources={sources} onOpen={onOpen} />
          </Panel>
          {cited.length > 0 && (
            <Panel tone="blue" caption="Back issues cited" className="panel-issues">
              <div className="issue-stack">
                {cited.map(({ issue, source }, k) => (
                  <button
                    key={issue.slug}
                    type="button"
                    className="stack-item"
                    style={{ ["--k" as string]: k }}
                    onClick={() => onOpen(source)}
                    aria-label={`Open issue ${issue.no}: ${issue.title}`}
                  >
                    <IssueCover issue={issue} stamped={!a.streaming && k === cited.length - 1} />
                  </button>
                ))}
              </div>
            </Panel>
          )}
        </div>
      )}
    </article>
  );
}
