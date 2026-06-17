import { BACKEND_URL } from "@/lib/config";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Proxies the agentic chat endpoint, preserving the NDJSON stream. Mirrors
// /api/chat; the only difference is the upstream path and the extra `step`
// events the front-end renders.
export async function POST(req: Request) {
  const body = await req.text();
  const debug = new URL(req.url).searchParams.get("debug") === "1" ? "?debug=1" : "";
  const upstream = await fetch(`${BACKEND_URL}/chat/agent${debug}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "application/x-ndjson",
      "Cache-Control": "no-cache",
    },
  });
}
