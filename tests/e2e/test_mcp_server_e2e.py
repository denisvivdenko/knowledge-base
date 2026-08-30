"""End-to-end tests for the knowledge-base MCP server.

These tests spawn the real server as a subprocess over stdio (no mocked
transport) and let a real Anthropic model choose and call the tools from a
natural-language prompt, the same way Claude Code or Claude Desktop would.
They require ANTHROPIC_API_KEY and network access; they are skipped otherwise.
"""

import json

from anthropic import Anthropic

from _support import (
    ANTHROPIC_MODEL,
    mcp_tools_to_anthropic_tools,
    open_mcp_session,
    require_anthropic_api_key,
)


def _read_jsonl(path):
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_jsonl(path, records):
    with path.open("w") as f:
        for record in records:
            f.write(json.dumps(record))
            f.write("\n")


def _tool_use_block(message):
    for block in message.content:
        if block.type == "tool_use":
            return block
    raise AssertionError(f"model did not call a tool: {message.content}")


def _tool_result_payload(result):
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


async def test_add_questions_e2e_saves_question_via_real_llm_tool_call(data_dir):
    require_anthropic_api_key()
    client = Anthropic()

    async with open_mcp_session(data_dir) as mcp_session:
        tools_result = await mcp_session.list_tools()
        tools = mcp_tools_to_anthropic_tools(tools_result.tools)

        prompt = (
            "I approve saving the following question to my knowledge base. "
            "Call the add_questions tool now with exactly this data, unmodified:\n"
            "- content: \"What is a Databricks cluster policy?\"\n"
            "- answer: \"A set of rules that limits the cluster configurations users are allowed to create.\"\n"
        )
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            tools=tools,
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": prompt}],
        )

        tool_use = _tool_use_block(message)
        assert tool_use.name == "add_questions"

        result = await mcp_session.call_tool(tool_use.name, tool_use.input)
        assert not result.isError, result.content

    payload = _tool_result_payload(result)
    assert payload["count"] == 1

    questions_file = data_dir / "questions.jsonl"
    assert questions_file.exists()
    saved = _read_jsonl(questions_file)

    assert len(saved) == 1
    assert "cluster policy" in saved[0]["content"].lower()


async def test_retrieve_questions_by_topic_e2e_filters_via_real_llm_tool_call(data_dir):
    require_anthropic_api_key()
    client = Anthropic()

    data_dir.mkdir(parents=True, exist_ok=True)
    seeded = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "content": "What is a Databricks cluster policy?",
            "answer": "A set of rules that limits cluster configurations.",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "content": "What is a Postgres B-tree index?",
            "answer": "An ordered index structure good for range queries.",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
    ]
    _write_jsonl(data_dir / "questions.jsonl", seeded)

    async with open_mcp_session(data_dir) as mcp_session:
        tools_result = await mcp_session.list_tools()
        tools = mcp_tools_to_anthropic_tools(tools_result.tools)

        prompt = "What questions do I have saved about databricks? Use the tool to look them up."
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            tools=tools,
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": prompt}],
        )

        tool_use = _tool_use_block(message)
        assert tool_use.name == "retrieve_questions_by_topic"

        result = await mcp_session.call_tool(tool_use.name, tool_use.input)
        assert not result.isError, result.content

    payload = _tool_result_payload(result)
    assert len(payload) == 1
    assert "cluster policy" in payload[0]["content"].lower()
