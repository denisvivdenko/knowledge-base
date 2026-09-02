import json
import os
from contextlib import asynccontextmanager

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ANTHROPIC_MODEL = "claude-sonnet-5"

TEST_SERVER_URL = "http://localhost:8000/mcp"


def require_anthropic_api_key() -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set; skipping real-LLM e2e test")
    return api_key


def require_test_server_token() -> str:
    token = os.environ.get("TEST_AUTH_TOKEN")
    if not token:
        pytest.skip("TEST_AUTH_TOKEN is not set")
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
    headers = {"X-API-Key": require_test_server_token()}
    async with httpx.AsyncClient(headers=headers) as http_client:
        async with streamable_http_client(TEST_SERVER_URL, http_client=http_client) as (read, write, _):
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


def tool_use_block(message):
    """Returns the first tool_use block in a model response, or raises if the
    model didn't call a tool. Use with tool_choice={"type": "any"}, which
    forces exactly one tool call, so "first" is also "only"."""
    for block in message.content:
        if block.type == "tool_use":
            return block
    raise AssertionError(f"model did not call a tool: {message.content}")


def tool_result_payload(result):
    """Extract the JSON payload from a CallToolResult.

    FastMCP represents dict returns as a single JSON text block
    (structuredContent is None), but list returns as structuredContent
    wrapped in {"result": [...]} plus one text block per item — so a single
    "parse content[0] as JSON" approach doesn't work for both shapes.
    """
    if result.structuredContent is not None:
        data = result.structuredContent
        if isinstance(data, dict) and data.keys() == {"result"}:
            return data["result"]
        return data
    text_blocks = [block.text for block in result.content if block.type == "text"]
    assert text_blocks, f"tool call returned no text content: {result.content}"
    return json.loads(text_blocks[0])


def prompt_text(get_prompt_result) -> str:
    return "\n".join(
        block.text
        for message in get_prompt_result.messages
        for block in [message.content]
        if block.type == "text"
    )


def _summarize_block(block):
    """Renders one message content block (either a raw dict we constructed,
    or an SDK ContentBlock object from a model response) as one debug line."""
    if isinstance(block, dict):
        block_type = block.get("type")
        if block_type == "tool_result":
            return f"[tool_result id={block.get('tool_use_id')} is_error={block.get('is_error')}] {block.get('content')}"
        if block_type == "text":
            return block.get("text", "")
        return json.dumps(block)
    block_type = getattr(block, "type", None)
    if block_type == "text":
        return block.text
    if block_type == "tool_use":
        return f"[tool_use name={block.name} id={block.id} input={block.input}]"
    return repr(block)


def print_conversation(label: str, messages: list) -> None:
    """Dumps the full message history so far to stdout. pytest captures
    stdout by default and shows it automatically for failing tests, so this
    doesn't need -s to be useful when debugging a failure."""
    print(f"\n===== {label} ({len(messages)} messages) =====")
    for i, message in enumerate(messages):
        role = message["role"]
        content = message["content"]
        if isinstance(content, str):
            print(f"[{i}] {role}: {content}")
            continue
        print(f"[{i}] {role}:")
        for block in content:
            print(f"    - {_summarize_block(block)}")
    print("=" * 60)


async def run_tool_loop(client, mcp_session, tools, messages, max_turns=6):
    """Drives one Anthropic <-> MCP tool-use loop until the model stops
    calling tools, mutating `messages` in place. Returns the list of tool
    names called, in order, and the final (text-only) response."""
    tool_calls_made = []
    for _ in range(max_turns):
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
        if not tool_use_blocks:
            return tool_calls_made, response

        tool_result_content = []
        for block in tool_use_blocks:
            result = await mcp_session.call_tool(block.name, block.input)
            tool_calls_made.append(block.name)
            tool_result_content.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(tool_result_payload(result)),
                    "is_error": result.isError,
                }
            )
        messages.append({"role": "user", "content": tool_result_content})

    raise AssertionError(f"tool loop did not terminate in {max_turns} turns; calls so far: {tool_calls_made}")
