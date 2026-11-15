import { postToBackend, visitorMessage } from "@/lib/backend";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const upstream = await postToBackend(req, "/job-fit");
  if (!upstream.ok) {
    // Same shape as a real report, so the page shows the reason in place.
    const summary = await visitorMessage(upstream);
    return Response.json(
      { summary, strengths: [], gaps: [], relevant_projects: [], pitch: "", sources: [] },
      { status: upstream.status }
    );
  }
  return Response.json(await upstream.json());
}
