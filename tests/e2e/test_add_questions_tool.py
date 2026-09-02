"""End-to-end tests for the knowledge-base MCP server.

These tests spawn the real server as a subprocess over stdio (no mocked
transport) and let a real Anthropic model choose and call the tools from a
natural-language prompt, the same way Claude Code or Claude Desktop would.
They require ANTHROPIC_API_KEY and network access; they are skipped otherwise.
"""

from anthropic import Anthropic

from _support import (
    ANTHROPIC_MODEL,
    mcp_tools_to_anthropic_tools,
    open_mcp_session,
    require_anthropic_api_key,
    tool_result_payload,
    tool_use_block,
)


async def test_add_questions():
    # Arrange
    require_anthropic_api_key()
    client = Anthropic()

    add_prompt = (
        "I approve saving the following questions to my knowledge base. "
        "Call the add_questions tool now with exactly this data, unmodified:\n"
        "- content: \"What is a Databricks cluster policy?\"\n"
        "  answer: \"A set of rules that limits the cluster configurations users are allowed to create.\"\n"
        "- content: \"What is a Postgres B-tree index?\"\n"
        "  answer: \"An ordered index structure good for range queries.\"\n"
    )
    retrieve_prompt = "What questions do I have saved about databricks? Use the tool to look them up."

    async with open_mcp_session() as mcp_session:
        tools_result = await mcp_session.list_tools()
        tools = mcp_tools_to_anthropic_tools(tools_result.tools)

        # Act
        add_message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            tools=tools,
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": add_prompt}],
        )
        add_tool_use = tool_use_block(add_message)
        add_result = await mcp_session.call_tool(add_tool_use.name, add_tool_use.input)

        retrieve_message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            tools=tools,
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": retrieve_prompt}],
        )
        retrieve_tool_use = tool_use_block(retrieve_message)
        retrieve_result = await mcp_session.call_tool(retrieve_tool_use.name, retrieve_tool_use.input)

    # Assert
    assert add_tool_use.name == "add_questions"
    assert not add_result.isError, add_result.content
    add_payload = tool_result_payload(add_result)
    assert add_payload["count"] == 2

    assert retrieve_tool_use.name == "retrieve_questions_by_topic"
    assert not retrieve_result.isError, retrieve_result.content
    retrieve_payload = tool_result_payload(retrieve_result)
    assert len(retrieve_payload) == 1
    assert "cluster policy" in retrieve_payload[0]["content"].lower()
