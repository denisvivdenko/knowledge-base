import hashlib

import pytest
from starlette.testclient import TestClient

from knowledge_base.api.auth import BearerTokenAuthMiddleware, hash_token

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
    app = BearerTokenAuthMiddleware(_downstream_app, token_hash=TOKEN_HASH)
    return TestClient(app)


def test_hash_token_returns_sha256_hex_digest():
    assert hash_token(TOKEN) == TOKEN_HASH


def test_hash_token_differs_for_different_tokens():
    assert hash_token(TOKEN) != hash_token("some-other-token")


def test_request_with_correct_bearer_token_is_allowed(client):
    response = client.get(MCP_PATH, headers={"Authorization": f"Bearer {TOKEN}"})

    assert response.status_code == 200
    assert response.text == "ok"


def test_request_without_authorization_header_is_rejected(client):
    response = client.get(MCP_PATH)

    assert response.status_code == 401


def test_request_with_wrong_token_is_rejected(client):
    response = client.get(MCP_PATH, headers={"Authorization": "Bearer wrong-token"})

    assert response.status_code == 401


def test_request_with_non_bearer_scheme_is_rejected(client):
    response = client.get(MCP_PATH, headers={"Authorization": f"Basic {TOKEN}"})

    assert response.status_code == 401


def test_rejection_response_carries_www_authenticate_header(client):
    response = client.get(MCP_PATH)

    assert response.headers["www-authenticate"] == "Bearer"
