import hashlib
import hmac
import json

from starlette.types import ASGIApp, Receive, Scope, Send


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


API_KEY_HEADER = b"x-api-key"


class ApiKeyAuthMiddleware:
    """Gate an ASGI app behind an API key, checked by hash only.

    Uses a dedicated `X-API-Key` header rather than `Authorization`, since
    OAuth-based MCP clients (e.g. Claude) already populate `Authorization`
    for their own flow.

    The raw key is never held server-side; only its SHA-256 hash is
    configured, so a leaked env dump or config file doesn't hand out a
    usable credential.
    """

    def __init__(self, app: ASGIApp, token_hash: str) -> None:
        self.app = app
        self._token_hash = token_hash

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        token = headers.get(API_KEY_HEADER)
        token = token.decode("latin-1") if token is not None else None

        if token is None or not hmac.compare_digest(hash_token(token), self._token_hash):
            await self._send_unauthorized(send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _send_unauthorized(send: Send) -> None:
        body = json.dumps({"error": "invalid_token"}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("latin-1")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
