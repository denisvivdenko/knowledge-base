import uuid
import pytest

from anthropic import Anthropic

from _support import (
    mcp_tools_to_anthropic_tools,
    open_mcp_session,
    print_conversation,
    prompt_text,
    require_anthropic_api_key,
    run_tool_loop,
    tool_result_payload,
)


def _mock_conversation(topic_slug: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": (
                f"We just finished migrating our service to the {topic_slug} caching "
                "layer. Can you remind me how its eviction policy works?"
            ),
        },
        {
            "role": "assistant",
            "content": (
                f"Sure — {topic_slug} uses a two-tier hybrid eviction policy: keys "
                "are tracked with LFU hit counters, and any key that gets 4 or more "
                "hits within a 60 second window gets promoted from the LFU tier into "
                "a protected LRU tier, so hot keys survive eviction storms that would "
                "wipe out a plain LRU cache. One gotcha we found: that promotion "
                "threshold (4 hits / 60s) is hard-coded as the default, and it's too "
                "conservative for spiky traffic, so we saw noticeable cache thrash "
                "until we tuned it."
            ),
        },
    ]


_APPROVAL_MESSAGE = {
    "role": "user",
    "content": "Automatically approve the questions you proposed if there are any.",
}


async def test_process_conversation_prompt_is_registered_with_expected_guidance():
    # Arrange
    async with open_mcp_session() as mcp_session:
        # Act
        prompts_result = await mcp_session.list_prompts()
        registered = {prompt.name: prompt for prompt in prompts_result.prompts}
        assert "process_conversation" in registered

        prompt_result = await mcp_session.get_prompt("process_conversation")

    # Assert
    assert prompt_text(prompt_result)


async def _process_conversation_and_approve(client, mcp_session, tools, topic_slug, process_instruction):
    """Runs one full retrieve -> draft -> approve -> add cycle for a fresh
    conversation about `topic_slug`. Returns (process_calls, approval_calls,
    messages, saved_questions)."""
    messages = [*_mock_conversation(topic_slug), process_instruction]
    process_calls, _ = await run_tool_loop(client, mcp_session, tools, messages)
    print_conversation(f"process — {topic_slug}", messages)
    print(f"process tool calls ({topic_slug}): {process_calls}")

    messages.append(_APPROVAL_MESSAGE)
    approval_calls, _ = await run_tool_loop(client, mcp_session, tools, messages)
    print_conversation(f"after approval — {topic_slug}", messages)
    print(f"approval tool calls ({topic_slug}): {approval_calls}")

    saved = tool_result_payload(
        await mcp_session.call_tool("retrieve_questions_by_topic", {"topic": topic_slug})
    )
    print(f"saved after processing ({topic_slug}): {saved}")

    return process_calls, approval_calls, messages, saved


async def test_process_conversation_follows_retrieve_draft_approve_add_flow():
    """Verifies the prompt's core contract in a single pass: it must retrieve
    existing questions before drafting anything, must not submit before the
    user approves, and must submit once approved."""
    # Arrange
    require_anthropic_api_key()
    client = Anthropic()
    topic_slug = f"zorbex-{uuid.uuid4().hex[:8]}"

    async with open_mcp_session() as mcp_session:
        tools_result = await mcp_session.list_tools()
        tools = mcp_tools_to_anthropic_tools(tools_result.tools)

        prompt_result = await mcp_session.get_prompt("process_conversation")
        process_instruction = {"role": "user", "content": prompt_text(prompt_result)}

        # Act
        process_calls, approval_calls, _, saved = await _process_conversation_and_approve(
            client, mcp_session, tools, topic_slug, process_instruction
        )

    # Assert — retrieved before drafting, didn't submit before approval,
    # submitted once approved.
    assert "retrieve_questions_by_topic" in process_calls
    assert "add_questions" not in process_calls
    assert "add_questions" in approval_calls
    assert len(saved) >= 1


@pytest.mark.xfail(reason="retrieve questions is not yet a reliable tool")
async def test_process_conversation_run_twice_does_not_add_duplicate_questions():
    # Arrange
    require_anthropic_api_key()
    client = Anthropic()
    topic_slug = f"zorbex-{uuid.uuid4().hex[:8]}"

    async with open_mcp_session() as mcp_session:
        tools_result = await mcp_session.list_tools()
        tools = mcp_tools_to_anthropic_tools(tools_result.tools)

        prompt_result = await mcp_session.get_prompt("process_conversation")
        process_instruction = {"role": "user", "content": prompt_text(prompt_result)}

        # Act — first run: process the conversation, then approve and submit.
        _, _, _, saved_after_first_run = await _process_conversation_and_approve(
            client, mcp_session, tools, topic_slug, process_instruction
        )
        assert len(saved_after_first_run) >= 1

        # Act — second run: same prompt, same conversation, fresh chat (no
        # shared message history), now that the questions are already saved.
        second_run_messages = [*_mock_conversation(topic_slug), process_instruction]
        second_run_calls, _ = await run_tool_loop(client, mcp_session, tools, second_run_messages)
        print_conversation("second run — process", second_run_messages)
        print(f"second run tool calls: {second_run_calls}")
        assert "retrieve_questions_by_topic" in second_run_calls

        second_run_messages.append(_APPROVAL_MESSAGE)
        second_approval_calls, _ = await run_tool_loop(client, mcp_session, tools, second_run_messages)
        print_conversation("second run — after approval", second_run_messages)
        print(f"second run approval tool calls: {second_approval_calls}")

        saved_after_second_run = tool_result_payload(
            await mcp_session.call_tool("retrieve_questions_by_topic", {"topic": topic_slug})
        )
        print(f"saved after second run: {saved_after_second_run}")

    # Assert — it checked what was already saved, but never called
    # add_questions, even after being told to submit, because there was
    # nothing new to add.
    assert "add_questions" not in second_run_calls
    assert "add_questions" not in second_approval_calls
    assert saved_after_second_run == saved_after_first_run
