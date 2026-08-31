import hashlib
import hmac
import json

from starlette.types import ASGIApp, Receive, Scope, Send


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class BearerTokenAuthMiddleware:
    """Gate an ASGI app behind a bearer token, checked by hash only.

    The raw token is never held server-side; only its SHA-256 hash is
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
        auth_header = headers.get(b"authorization", b"").decode("latin-1")
        token = auth_header[7:] if auth_header.lower().startswith("bearer ") else None

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
                    (b"www-authenticate", b"Bearer"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
