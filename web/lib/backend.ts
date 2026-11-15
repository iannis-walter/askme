// Server-only. The one place the route handlers talk to the FastAPI backend.
//
// Every call carries two headers the backend relies on:
//   X-Proxy-Secret  proves the request came through this front-end, so the
//                   backend can refuse anyone calling its public URL directly.
//   X-Client-IP     the visitor's address, so rate limits apply per visitor and
//                   not to the single address of this server.
import { BACKEND_URL } from "@/lib/config";

const SHARED_SECRET = process.env.BACKEND_SHARED_SECRET ?? "";

// Matches the backend's own cap; far above any legitimate chat or job-fit body.
const MAX_BODY_BYTES = 1_000_000;

const GENERIC_ERROR = "Something went wrong. Please try again in a moment.";

// On Vercel both headers are set by the platform, which overwrites whatever the
// caller sent, so they can be trusted there. Anywhere else a caller could send
// its own value and pick a fresh rate-limit bucket per request, so the address
// is forwarded only when the operator says a trusted reverse proxy sets it
// (TRUST_PROXY_HEADERS=1). Otherwise the backend keeps one shared bucket.
const TRUST_FORWARDED_IP = process.env.VERCEL === "1" || process.env.TRUST_PROXY_HEADERS === "1";

function clientIp(req: Request): string | null {
  if (!TRUST_FORWARDED_IP) return null;
  const real = req.headers.get("x-real-ip")?.trim();
  const forwarded = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  return real || forwarded || null;
}

function backendHeaders(req: Request): Record<string, string> {
  const headers: Record<string, string> = {};
  if (SHARED_SECRET) headers["X-Proxy-Secret"] = SHARED_SECRET;
  const ip = clientIp(req);
  if (ip) headers["X-Client-IP"] = ip;
  return headers;
}

async function callBackend(path: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(`${BACKEND_URL}${path}`, init);
  } catch {
    // Backend asleep or unreachable: answer like any other upstream failure.
    return Response.json({ detail: "Backend unreachable." }, { status: 502 });
  }
}

export function getFromBackend(req: Request, path: string): Promise<Response> {
  return callBackend(path, { headers: backendHeaders(req) });
}

export async function postToBackend(req: Request, path: string): Promise<Response> {
  const body = await req.text();
  if (Buffer.byteLength(body) > MAX_BODY_BYTES) {
    return Response.json({ detail: "Request body too large." }, { status: 413 });
  }
  return callBackend(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...backendHeaders(req) },
    body,
  });
}

// The text to show a visitor for a failed backend call. Only the rate-limit
// messages are written for visitors; every other failure stays generic.
export async function visitorMessage(upstream: Response): Promise<string> {
  if (upstream.status === 429) {
    try {
      const detail = (await upstream.json()).detail;
      if (typeof detail === "string") return detail;
    } catch {
      // fall through to the generic message
    }
  }
  return GENERIC_ERROR;
}

// Proxies a streamed NDJSON answer. A failed call is turned into the same event
// shape, so the chat shows the reason instead of an empty balloon.
export async function streamFromBackend(req: Request, path: string): Promise<Response> {
  const upstream = await postToBackend(req, path);
  const headers = { "Content-Type": "application/x-ndjson", "Cache-Control": "no-cache" };
  if (!upstream.ok) {
    const text = await visitorMessage(upstream);
    const events = [{ type: "delta", text }, { type: "done" }];
    return new Response(events.map((e) => JSON.stringify(e) + "\n").join(""), {
      status: upstream.status,
      headers,
    });
  }
  return new Response(upstream.body, { status: upstream.status, headers });
}
