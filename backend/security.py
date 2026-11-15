"""The trust boundary between the Next.js proxy and this service.

In production every request reaches uvicorn from the same peer (the Vercel
function), so the socket address says nothing about the visitor. The front-end
therefore sends two headers: a shared secret proving the request came through it,
and the visitor's address as Vercel reported it. The address is believed only
when the secret matches — otherwise anyone could pick their own rate-limit bucket.

  BACKEND_SHARED_SECRET   unset → open service (local dev); set → every route
                          except /health requires the matching X-Proxy-Secret.

NB: no `from __future__ import annotations` here — FastAPI must see the real
`Request` annotation on the dependency below.
"""
import hmac
import os

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

SECRET_HEADER = "x-proxy-secret"
CLIENT_IP_HEADER = "x-client-ip"
_TOO_LARGE = "Request body too large."


def _secret() -> str:
    return os.getenv("BACKEND_SHARED_SECRET", "")


def from_trusted_proxy(request: Request) -> bool:
    secret = _secret()
    if not secret:
        return False
    sent = request.headers.get(SECRET_HEADER, "")
    return hmac.compare_digest(sent.encode(), secret.encode())


def client_ip(request: Request) -> str:
    """The visitor's address: forwarded by our own proxy, else the socket peer."""
    if from_trusted_proxy(request):
        forwarded = request.headers.get(CLIENT_IP_HEADER, "").strip()
        if forwarded:
            return forwarded[:64]
    return request.client.host if request.client else "unknown"


async def require_proxy_secret(request: Request) -> None:
    """App-wide dependency: once a secret is configured, only our proxy gets in."""
    if not _secret() or request.url.path == "/health":
        return
    if not from_trusted_proxy(request):
        raise HTTPException(status_code=403, detail="Forbidden")


class BodySizeLimitMiddleware:
    """Refuse request bodies above `max_bytes`, declared or streamed.

    Without it the whole body is read into memory before Pydantic gets to
    enforce any field limit.
    """

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > self.max_bytes:
            await JSONResponse({"detail": _TOO_LARGE}, status_code=413)(scope, receive, send)
            return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # FastAPI re-raises HTTPException from body parsing as-is.
                    raise HTTPException(status_code=413, detail=_TOO_LARGE)
            return message

        await self.app(scope, limited_receive, send)
