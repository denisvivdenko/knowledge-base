import os
from contextlib import asynccontextmanager

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

TEST_SERVER_URL = "http://localhost:8000/mcp"


def require_anthropic_api_key() -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set; skipping real-LLM e2e test")
    return api_key


def require_test_server_token() -> str:
    token = os.environ.get("AUTH_TEST_TOKEN")
    if not token:
        pytest.skip("AUTH_TEST_TOKEN is not set")
    return token


@asynccontextmanager
async def open_mcp_session():
    """Connect to the real server, run via `make test-e2e` (docker compose --profile test),
    for the lifetime of one test.

    Deliberately not a pytest fixture: mcp's client session uses anyio task
    groups internally, and anyio requires a cancel scope to be exited from the
    same asyncio.Task it was entered in. pytest-asyncio runs an async generator
    fixture's setup and its post-yield teardown as two separate top-level
    tasks, which trips that check. Opening this inline with `async with`
    inside the test keeps setup, use, and teardown in one task.
    """
    headers = {"Authorization": f"Bearer {require_test_server_token()}"}
    async with streamablehttp_client(TEST_SERVER_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def mcp_tools_to_anthropic_tools(tools) -> list[dict]:
    return [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        }
        for tool in tools
    ]
