import { BACKEND_URL } from "@/lib/config";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id") ?? "";
  const upstream = await fetch(
    `${BACKEND_URL}/sources?id=${encodeURIComponent(id)}`
  );
  const data = await upstream.json();
  return Response.json(data, { status: upstream.status });
}
