import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_SCRIPT = REPO_ROOT / "server.py"

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


def require_anthropic_api_key() -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set; skipping real-LLM e2e test")
    return api_key


@asynccontextmanager
async def open_mcp_session(data_dir):
    """Connect to the real server over stdio for the lifetime of one test.

    Deliberately not a pytest fixture: mcp's stdio_client/ClientSession use
    anyio task groups internally, and anyio requires a cancel scope to be
    exited from the same asyncio.Task it was entered in. pytest-asyncio runs
    an async generator fixture's setup and its post-yield teardown as two
    separate top-level tasks, which trips that check. Opening this inline
    with `async with` inside the test keeps setup, use, and teardown in one
    task.
    """
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
        env={**os.environ, "KNOWLEDGE_BASE_DATA_DIR": str(data_dir)},
    )
    async with stdio_client(server_params) as (read, write):
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
