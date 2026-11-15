import { getFromBackend } from "@/lib/backend";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id") ?? "";
  const upstream = await getFromBackend(req, `/sources?id=${encodeURIComponent(id)}`);
  if (!upstream.ok) return Response.json({ error: "not found" }, { status: upstream.status });
  return Response.json(await upstream.json());
}
