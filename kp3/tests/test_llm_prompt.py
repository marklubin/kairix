"""Tests for LLM prompt processor."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.processors.base import ProcessorGroup
from kp3.processors.llm_prompt import LLMPromptConfig, LLMPromptProcessor
from kp3.services.passages import create_passage


@pytest.fixture
def mock_anthropic_client():
    """Create mock Anthropic client."""
    client = AsyncMock()
    # Mock response
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "This is a summary of the passages."

    response = MagicMock()
    response.content = [text_block]

    client.messages.create.return_value = response
    return client


async def test_llm_processor_creates_summary(
    session: AsyncSession,
    mock_anthropic_client: AsyncMock,
):
    """Processor creates new passage from LLM response."""
    p1 = await create_passage(session, content="First thing", passage_type="raw")
    p2 = await create_passage(session, content="Second thing", passage_type="raw")
    await session.commit()

    processor = LLMPromptProcessor(client=mock_anthropic_client)

    group = ProcessorGroup(
        passage_ids=[p1.id, p2.id],
        passages=[p1, p2],
        group_key="test_group",
        group_metadata={"date": "2024-01-01"},
    )

    config = LLMPromptConfig(prompt_template="Summarize these {count} items:\n\n{passages}")
    result = await processor.process(group, config)

    assert result.action == "create"
    assert result.content == "This is a summary of the passages."
    assert result.metadata["source_count"] == 2
    assert result.metadata["group_key"] == "test_group"

    # Verify API was called
    mock_anthropic_client.messages.create.assert_called_once()


async def test_llm_processor_uses_config_model(
    session: AsyncSession,
    mock_anthropic_client: AsyncMock,
):
    """Processor uses model from config."""
    passage = await create_passage(session, content="Content", passage_type="raw")
    await session.commit()

    processor = LLMPromptProcessor(client=mock_anthropic_client)

    group = ProcessorGroup(
        passage_ids=[passage.id],
        passages=[passage],
        group_key="test",
    )

    config = LLMPromptConfig(model="claude-sonnet-4-20250514")
    await processor.process(group, config)

    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-20250514"


async def test_llm_processor_with_system_prompt(
    session: AsyncSession,
    mock_anthropic_client: AsyncMock,
):
    """Processor includes system prompt when provided."""
    passage = await create_passage(session, content="Content", passage_type="raw")
    await session.commit()

    processor = LLMPromptProcessor(client=mock_anthropic_client)

    group = ProcessorGroup(
        passage_ids=[passage.id],
        passages=[passage],
        group_key="test",
    )

    config = LLMPromptConfig(system_prompt="You are a helpful assistant.")
    await processor.process(group, config)

    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == "You are a helpful assistant."


async def test_llm_processor_empty_group(
    mock_anthropic_client: AsyncMock,
):
    """Processor returns pass for empty groups."""
    processor = LLMPromptProcessor(client=mock_anthropic_client)

    group = ProcessorGroup(
        passage_ids=[],
        passages=[],
        group_key="empty",
    )

    config = LLMPromptConfig()
    result = await processor.process(group, config)

    assert result.action == "pass"
    mock_anthropic_client.messages.create.assert_not_called()


async def test_llm_processor_empty_response(
    session: AsyncSession,
    mock_anthropic_client: AsyncMock,
):
    """Processor returns pass when LLM returns empty content."""
    passage = await create_passage(session, content="Content", passage_type="raw")
    await session.commit()

    # Mock empty response
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "   "  # whitespace only
    mock_anthropic_client.messages.create.return_value.content = [text_block]

    processor = LLMPromptProcessor(client=mock_anthropic_client)

    group = ProcessorGroup(
        passage_ids=[passage.id],
        passages=[passage],
        group_key="test",
    )

    config = LLMPromptConfig()
    result = await processor.process(group, config)

    assert result.action == "pass"


async def test_llm_processor_template_formatting(
    session: AsyncSession,
    mock_anthropic_client: AsyncMock,
):
    """Processor correctly formats template with group metadata."""
    passage = await create_passage(session, content="Day content", passage_type="raw")
    await session.commit()

    processor = LLMPromptProcessor(client=mock_anthropic_client)

    group = ProcessorGroup(
        passage_ids=[passage.id],
        passages=[passage],
        group_key="2024-01-15",
        group_metadata={"date": "January 15, 2024", "count": 5},
    )

    config = LLMPromptConfig(prompt_template="Summarize {count} items from {date}:\n\n{passages}")
    await processor.process(group, config)

    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    prompt = call_kwargs["messages"][0]["content"]

    # count is overridden by actual passage count (1), date comes from metadata
    assert "1 items from January 15, 2024" in prompt
    assert "Day content" in prompt
