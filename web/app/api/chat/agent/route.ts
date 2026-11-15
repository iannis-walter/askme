import { streamFromBackend } from "@/lib/backend";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Proxies the agentic chat endpoint, preserving the NDJSON stream. Mirrors
// /api/chat; the only difference is the upstream path and the extra `step`
// events the front-end renders.
export async function POST(req: Request) {
  return streamFromBackend(req, "/chat/agent");
}
