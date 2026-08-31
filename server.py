import os

import uvicorn

from knowledge_base.api.auth import BearerTokenAuthMiddleware
from knowledge_base.api.server import mcp


def _build_app():
    token_hash = os.environ["AUTH_TOKEN_HASH"]
    return BearerTokenAuthMiddleware(mcp.streamable_http_app(), token_hash=token_hash)


if __name__ == "__main__":
    uvicorn.run(
        _build_app(),
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=mcp.settings.log_level.lower(),
    )
