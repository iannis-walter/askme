import { streamFromBackend } from "@/lib/backend";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  return streamFromBackend(req, "/chat");
}
