"""Generate backend/embeddings.json from content/. Run after editing content.

    cd backend && LLM_PROVIDER=mistral LLM_API_KEY=... python build_embeddings.py
"""
import asyncio
import json
import os

from dotenv import load_dotenv

import embeddings
from content_loader import all_chunks, load_documents


async def main() -> None:
    load_dotenv()
    content_dir = os.getenv("CONTENT_DIR", "../content")
    chunks = all_chunks(load_documents(content_dir))
    model = embeddings._embed_model()
    print(f"[build] embedding {len(chunks)} chunks with {model}")
    vectors = await embeddings.embed_texts([c.text for c in chunks])
    cache = {embeddings.cache_key(c.text, model): v for c, v in zip(chunks, vectors)}
    embeddings.CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")
    print(f"[build] wrote {embeddings.CACHE_PATH} ({len(cache)} entries)")


if __name__ == "__main__":
    asyncio.run(main())
