import hashlib

import pytest
from starlette.testclient import TestClient

from knowledge_base.api.auth import ApiKeyAuthMiddleware, hash_token

TOKEN = "correct-horse-battery-staple"
TOKEN_HASH = hashlib.sha256(TOKEN.encode("utf-8")).hexdigest()

MCP_PATH = "/mcp"


async def _downstream_app(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        }
    )
    await send({"type": "http.response.body", "body": b"ok"})


@pytest.fixture
def client():
    app = ApiKeyAuthMiddleware(_downstream_app, token_hash=TOKEN_HASH)
    return TestClient(app)


def test_hash_token_returns_sha256_hex_digest():
    assert hash_token(TOKEN) == TOKEN_HASH


def test_hash_token_differs_for_different_tokens():
    assert hash_token(TOKEN) != hash_token("some-other-token")


def test_request_with_correct_api_key_is_allowed(client):
    response = client.get(MCP_PATH, headers={"X-API-Key": TOKEN})

    assert response.status_code == 200
    assert response.text == "ok"


def test_request_without_api_key_header_is_rejected(client):
    response = client.get(MCP_PATH)

    assert response.status_code == 401


def test_request_with_wrong_api_key_is_rejected(client):
    response = client.get(MCP_PATH, headers={"X-API-Key": "wrong-token"})

    assert response.status_code == 401


def test_request_with_authorization_header_only_is_rejected(client):
    response = client.get(MCP_PATH, headers={"Authorization": f"Bearer {TOKEN}"})

    assert response.status_code == 401
