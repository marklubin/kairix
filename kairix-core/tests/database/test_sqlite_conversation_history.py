"""
Test SQLite conversation history perceptor.
"""
import pytest
import asyncio
from kairix_core.cognition.perceptor.sqlite_conversation_history import SQLiteConversationHistoryPerceptor
from kairix_core.types.cognition import Stimulus, StimulusType
from kairix_core.types.db import ConversationMessage


@pytest.mark.asyncio
async def test_conversation_storage(test_db):
    """Test storing and retrieving conversation pairs."""
    perceptor = SQLiteConversationHistoryPerceptor(
        agent_id="test_agent",
        user_id="test_user",
        storage=test_db
    )
    
    # Send user message
    user_stimulus = Stimulus(
        content="Hello, how are you?",
        type=StimulusType.user_message
    )
    perceptions = await perceptor.perceive(user_stimulus)
    
    # Should return empty history initially
    assert len(perceptions) == 1
    assert "[]" in perceptions[0].content  # Empty history
    
    # Send assistant response
    assistant_stimulus = Stimulus(
        content="I'm doing well, thank you!",
        type=StimulusType.self_perception
    )
    perceptions = await perceptor.perceive(assistant_stimulus)
    
    # Should now contain the conversation pair
    assert len(perceptions) == 1
    history_str = perceptions[0].content
    assert "Hello, how are you?" in history_str
    assert "I'm doing well, thank you!" in history_str
    
    # Verify in database
    with test_db.session() as session:
        messages = session.query(ConversationMessage).filter_by(
            thread_id="test_agent_test_user"
        ).order_by(ConversationMessage.sequence_number).all()
        
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello, how are you?"
        assert messages[0].sequence_number == 1
        assert messages[1].role == "assistant"
        assert messages[1].content == "I'm doing well, thank you!"
        assert messages[1].sequence_number == 2


@pytest.mark.asyncio
async def test_conversation_sequence_integrity(test_db):
    """Test that conversation sequences are maintained properly."""
    perceptor = SQLiteConversationHistoryPerceptor(
        agent_id="test_agent",
        user_id="test_user",
        storage=test_db
    )
    
    # Store multiple conversation pairs
    for i in range(3):
        user_stimulus = Stimulus(
            content=f"Message {i}",
            type=StimulusType.user_message
        )
        await perceptor.perceive(user_stimulus)
        
        assistant_stimulus = Stimulus(
            content=f"Response {i}",
            type=StimulusType.self_perception
        )
        await perceptor.perceive(assistant_stimulus)
    
    # Check sequence numbers
    with test_db.session() as session:
        messages = session.query(ConversationMessage).filter_by(
            thread_id="test_agent_test_user"
        ).order_by(ConversationMessage.sequence_number).all()
        
        assert len(messages) == 6
        for i, msg in enumerate(messages):
            assert msg.sequence_number == i + 1


@pytest.mark.asyncio
async def test_window_size_limiting(test_db):
    """Test that window size limits the cached history."""
    perceptor = SQLiteConversationHistoryPerceptor(
        agent_id="test_agent",
        user_id="test_user",
        window_size=4,  # Only keep 4 messages
        storage=test_db
    )
    
    # Store 3 conversation pairs (6 messages total)
    for i in range(3):
        user_stimulus = Stimulus(
            content=f"Message {i}",
            type=StimulusType.user_message
        )
        await perceptor.perceive(user_stimulus)
        
        assistant_stimulus = Stimulus(
            content=f"Response {i}",
            type=StimulusType.self_perception
        )
        perceptions = await perceptor.perceive(assistant_stimulus)
    
    # Check that cache only has window_size messages
    history_str = perceptions[0].content
    # Should have messages 1 and 2 (4 messages total)
    assert "Message 0" not in history_str  # First pair should be dropped
    assert "Response 0" not in history_str
    assert "Message 1" in history_str
    assert "Response 1" in history_str
    assert "Message 2" in history_str
    assert "Response 2" in history_str


@pytest.mark.asyncio
async def test_multiple_agents_isolation(test_db):
    """Test that different agents have isolated conversation histories."""
    perceptor1 = SQLiteConversationHistoryPerceptor(
        agent_id="agent1",
        user_id="user1",
        storage=test_db
    )
    
    perceptor2 = SQLiteConversationHistoryPerceptor(
        agent_id="agent2",
        user_id="user1",
        storage=test_db
    )
    
    # Store conversation for agent1
    await perceptor1.perceive(Stimulus(
        content="Hello agent 1",
        type=StimulusType.user_message
    ))
    await perceptor1.perceive(Stimulus(
        content="Hello from agent 1",
        type=StimulusType.self_perception
    ))
    
    # Store conversation for agent2
    await perceptor2.perceive(Stimulus(
        content="Hello agent 2",
        type=StimulusType.user_message
    ))
    perceptions = await perceptor2.perceive(Stimulus(
        content="Hello from agent 2",
        type=StimulusType.self_perception
    ))
    
    # Agent2's history should not contain agent1's messages
    history_str = perceptions[0].content
    assert "Hello agent 2" in history_str
    assert "Hello from agent 2" in history_str
    assert "Hello agent 1" not in history_str
    assert "Hello from agent 1" not in history_str


@pytest.mark.asyncio
async def test_get_recent_context(test_db):
    """Test getting recent context with limit."""
    perceptor = SQLiteConversationHistoryPerceptor(
        agent_id="test_agent",
        user_id="test_user",
        storage=test_db
    )
    
    # Store 3 conversation pairs
    for i in range(3):
        await perceptor.perceive(Stimulus(
            content=f"Message {i}",
            type=StimulusType.user_message
        ))
        await perceptor.perceive(Stimulus(
            content=f"Response {i}",
            type=StimulusType.self_perception
        ))
    
    # Get recent context
    recent = await perceptor.get_recent_context(limit=2)
    
    # Should return last 2 messages
    assert len(recent) == 2
    assert recent[0]["role"] == "user"
    assert recent[0]["content"] == "Message 2"
    assert recent[1]["role"] == "assistant"
    assert recent[1]["content"] == "Response 2"