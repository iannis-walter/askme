"""Offline evaluation harness for the agent.

For each case it runs the full agentic loop against the real knowledge base and
scores the answer:

  * deterministic — are the expected facts present? are forbidden strings
    absent? are sources cited when required? how many steps / tokens did it
    take? (cheap, reproducible)
  * LLM-as-judge (optional, `--judge`) — a second model call rates faithfulness
    and completeness 0-5 with a strict rubric. (costs tokens, kept out of CI)

Running the agent requires a configured provider (LLM_PROVIDER + key), so this
harness is a manual/dev tool, never part of the deterministic CI suite.

Usage:
    python eval/run_eval.py                     # deterministic only
    python eval/run_eval.py --judge             # + LLM-as-judge
    python eval/run_eval.py --json report.json  # also write a JSON report
    python eval/run_eval.py --case location     # one case
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

# Make the flat backend modules importable when run from anywhere.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

import agent  # noqa: E402
import llm_client  # noqa: E402
from content_loader import all_chunks, load_documents  # noqa: E402
from retrieve import build_retriever  # noqa: E402
from tools import ToolContext  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

CASES_PATH = Path(__file__).with_name("cases.json")

JUDGE_SYSTEM = """You are a strict evaluator of an AI assistant's answer about a job candidate.
Score the answer on two axes, each 0-5:
- faithfulness: is every claim supported by the provided reference facts? Penalise anything invented or unsupported. 5 = fully grounded, 0 = fabricated.
- completeness: does it actually answer the question using the available facts? 5 = complete, 0 = misses the point.
Return ONLY a JSON object: {"faithfulness": int, "completeness": int, "reasoning": "one sentence"}.
"""


async def build_ctx(content_dir: str) -> ToolContext:
    docs = load_documents(content_dir)
    retriever = await build_retriever(all_chunks(docs))
    return ToolContext(retriever=retriever, docs=docs)


def score_deterministic(case: dict, answer: str, sources: list[dict]) -> dict:
    low = answer.lower()
    expected = case.get("expected_facts", [])
    found = [f for f in expected if f.lower() in low]
    facts_score = 1.0 if not expected else len(found) / len(expected)

    forbidden = case.get("must_not_contain", [])
    forbidden_hits = [b for b in forbidden if b.lower() in low]

    must_cite = case.get("must_cite", False)
    citation_ok = (not must_cite) or len(sources) > 0

    passed = facts_score == 1.0 and citation_ok and not forbidden_hits
    return {
        "passed": passed,
        "facts_score": round(facts_score, 3),
        "facts_found": found,
        "facts_missing": [f for f in expected if f not in found],
        "forbidden_hits": forbidden_hits,
        "citation_ok": citation_ok,
    }


async def judge(case: dict, answer: str) -> dict:
    facts = ", ".join(case.get("expected_facts", [])) or "(no specific facts; honesty matters)"
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {
            "role": "user",
            "content": (
                f"QUESTION:\n{case['question']}\n\n"
                f"REFERENCE FACTS:\n{facts}\n\n"
                f"ANSWER TO GRADE:\n{answer}"
            ),
        },
    ]
    try:
        data = await llm_client.complete_json(messages)
        return {
            "faithfulness": int(data.get("faithfulness", 0)),
            "completeness": int(data.get("completeness", 0)),
            "reasoning": data.get("reasoning", ""),
        }
    except Exception as exc:  # noqa: BLE001
        return {"faithfulness": 0, "completeness": 0, "reasoning": f"judge error: {exc}"}


async def run_case(case: dict, ctx: ToolContext, use_judge: bool) -> dict:
    outcome = await agent.run_agent(
        case["question"], [], ctx, request_id=f"eval-{case['id']}-{uuid.uuid4().hex[:6]}"
    )
    tool_steps = sum(1 for s in outcome.trace.steps if s.kind == "tool")
    det = score_deterministic(case, outcome.answer, outcome.sources)
    row = {
        "id": case["id"],
        "question": case["question"],
        "answer": outcome.answer,
        "sources": [s["id"] for s in outcome.sources],
        "tool_steps": tool_steps,
        "tokens_in": outcome.trace.total_tokens_in,
        "tokens_out": outcome.trace.total_tokens_out,
        "truncated": outcome.truncated,
        "stop_reason": outcome.trace.stop_reason,
        **det,
    }
    if use_judge:
        row["judge"] = await judge(case, outcome.answer)
    return row


def print_report(rows: list[dict], use_judge: bool) -> dict:
    passed = sum(1 for r in rows if r["passed"])
    total = len(rows)
    avg_steps = sum(r["tool_steps"] for r in rows) / total if total else 0
    avg_tok_in = sum(r["tokens_in"] for r in rows) / total if total else 0
    avg_tok_out = sum(r["tokens_out"] for r in rows) / total if total else 0

    print("\n" + "=" * 72)
    print("ASK-ME AGENT EVAL")
    print("=" * 72)
    for r in rows:
        status = "PASS" if r["passed"] else "FAIL"
        facts = f"{len(r['facts_found'])}/{len(r['facts_found']) + len(r['facts_missing'])} facts"
        extra = ""
        if r["facts_missing"]:
            extra += f"  missing={r['facts_missing']}"
        if r["forbidden_hits"]:
            extra += f"  FORBIDDEN={r['forbidden_hits']}"
        if not r["citation_ok"]:
            extra += "  NO-CITATION"
        judge_str = ""
        if use_judge and "judge" in r:
            j = r["judge"]
            judge_str = f"  judge=F{j['faithfulness']}/C{j['completeness']}"
        print(f"[{status}] {r['id']:<22} {facts}  steps={r['tool_steps']}  tok={r['tokens_in']}+{r['tokens_out']}{judge_str}{extra}")

    print("-" * 72)
    print(f"Pass rate:     {passed}/{total} ({100 * passed / total:.0f}%)" if total else "no cases")
    print(f"Avg tool steps: {avg_steps:.1f}")
    print(f"Avg tokens:     {avg_tok_in:.0f} in / {avg_tok_out:.0f} out")
    summary = {
        "pass_rate": round(passed / total, 3) if total else 0,
        "passed": passed,
        "total": total,
        "avg_tool_steps": round(avg_steps, 2),
        "avg_tokens_in": round(avg_tok_in, 1),
        "avg_tokens_out": round(avg_tok_out, 1),
    }
    if use_judge:
        graded = [r["judge"] for r in rows if "judge" in r]
        if graded:
            summary["avg_faithfulness"] = round(sum(g["faithfulness"] for g in graded) / len(graded), 2)
            summary["avg_completeness"] = round(sum(g["completeness"] for g in graded) / len(graded), 2)
            print(f"Avg judge:      faithfulness {summary['avg_faithfulness']}/5, completeness {summary['avg_completeness']}/5")
    print("=" * 72)
    return summary


async def main_async(args) -> int:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"No case with id '{args.case}'")
            return 1
    if args.max_cases:
        cases = cases[: args.max_cases]

    cfg = llm_client.LLMConfig()
    print(f"Provider: {cfg.provider} | model: {cfg.model} | cases: {len(cases)} | judge: {args.judge}")
    ctx = await build_ctx(args.content_dir)

    rows = []
    for case in cases:
        print(f"  running {case['id']}…")
        rows.append(await run_case(case, ctx, args.judge))

    summary = print_report(rows, args.judge)

    if args.json:
        report = {"summary": summary, "cases": rows}
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nJSON report written to {args.json}")

    # Non-zero exit if any case failed deterministically — handy for dev gating.
    return 0 if summary.get("passed") == summary.get("total") else 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ask-me agent eval suite.")
    parser.add_argument("--content-dir", default=os.getenv("CONTENT_DIR", str(BACKEND_DIR.parent / "content")))
    parser.add_argument("--judge", action="store_true", help="enable optional LLM-as-judge scoring")
    parser.add_argument("--json", help="write a JSON report to this path")
    parser.add_argument("--case", help="run only the case with this id")
    parser.add_argument("--max-cases", type=int, help="cap the number of cases")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
