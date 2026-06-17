"use client";

import { useEffect, useRef, useState } from "react";
import { PROFILE, SUGGESTED_PROMPTS } from "@/lib/profile";
import type { AgentStep, Message, Source } from "@/lib/types";
import { SourceTags } from "@/components/source-tags";
import { SourceDrawer } from "@/components/source-drawer";
import { Markdown } from "@/components/markdown";

export function ChatShell() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [agentMode, setAgentMode] = useState(false);
  const [openSource, setOpenSource] = useState<Source | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
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

  function formatArgs(args: Record<string, unknown>): string {
    const entries = Object.entries(args);
    if (entries.length === 0) return "";
    return entries.map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(" ");
  }

  const empty = messages.length === 0;

  return (
    <main className="stage">
      <div className="topbar">
        <span className="display" style={{ fontSize: 18 }}>{PROFILE.name}</span>
        <a className="mono" style={{ color: "var(--ember)", fontSize: 13 }} href="/job-fit">Job fit →</a>
      </div>

      <div className="stage-scroll" ref={scrollRef}>
        <div className="stage-inner">
          {empty ? (
            <div className="intro" style={{ paddingTop: "2vh" }}>
              <div className="eyebrow">Candidate briefing</div>
              <h1 className="display hero-title">
                A profile you can <em>interrogate.</em>
              </h1>
              <p style={{ color: "var(--muted)", marginTop: 18, maxWidth: 540, fontSize: 19 }}>
                {PROFILE.subtitle} Every answer is grounded in a curated knowledge
                base and shows the files it drew from. Nothing invented.
              </p>
              <div className="chips">
                {SUGGESTED_PROMPTS.map((p) => (
                  <button key={p.label} className="chip" onClick={() => send(p.text)}>
                    <span className="chip-label">{p.label}</span>
                    {p.text}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`msg ${m.role === "user" ? "msg-user" : "msg-assistant"}`}>
                <span className="role-tag">{m.role === "user" ? "Question" : "Response"}</span>
                {m.role === "user" ? (
                  <div className="qtext">{m.content}</div>
                ) : (
                  <>
                    {m.steps && m.steps.length > 0 && (
                      <div className="agent-steps">
                        {m.steps.map((s, si) => (
                          <span
                            key={si}
                            className="agent-step"
                            style={{ opacity: s.ok ? 1 : 0.6 }}
                            title={s.error ?? JSON.stringify(s.args)}
                          >
                            <span className="mono" style={{ color: "var(--ember)" }}>
                              {s.ok ? "▸" : "✕"} {s.tool}
                            </span>
                            <span className="mono" style={{ color: "var(--muted)", fontSize: 11 }}>
                              {formatArgs(s.args)}
                            </span>
                          </span>
                        ))}
                      </div>
                    )}
                    <div className={`answer ${m.streaming && !m.content ? "caret" : ""}`}>
                      <Markdown>{m.content}</Markdown>
                      {m.streaming && m.content ? <span className="caret" /> : null}
                    </div>
                    {m.sources && m.sources.length > 0 && (
                      <SourceTags sources={m.sources} onOpen={setOpenSource} />
                    )}
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      <div className="composer-wrap">
        <div className="composer-controls">
          <button
            type="button"
            className="mono agent-toggle"
            onClick={() => setAgentMode((v) => !v)}
            aria-pressed={agentMode}
            title="Agent mode: the model calls tools in a loop (searching the knowledge base itself, possibly several times) instead of a single-shot answer. The steps are shown above each answer."
          >
            {agentMode ? "● Agent mode" : "○ Agent mode"}
          </button>
          <span className="mono composer-hint">
            {agentMode ? "tool-use loop · steps shown" : "single-shot · one retrieval"}
          </span>
        </div>
        <div className="composer">
          <textarea
            ref={taRef}
            value={input}
            placeholder="Ask anything about the candidate…"
            onChange={(e) => {
              setInput(e.target.value);
              autosize();
            }}
            onKeyDown={onKeyDown}
            rows={1}
          />
          <button
            className="send-btn"
            disabled={busy || !input.trim()}
            onClick={() => send(input)}
            aria-label="Send"
          >
            Ask
          </button>
        </div>
      </div>

      <SourceDrawer source={openSource} onClose={() => setOpenSource(null)} />
    </main>
  );
}
