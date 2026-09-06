from _support import (
    open_mcp_session,
    prompt_text,
)


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
