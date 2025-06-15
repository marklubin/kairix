import asyncio
import datetime

import aiofiles
import pytest
import pytest_asyncio
import yaml

from kairix_engine.message_history import MessageHistory


@pytest_asyncio.fixture
async def message_history(tmp_path, monkeypatch):
    """Create a MessageHistory instance with a temporary directory."""
    # Mock date for consistent filenames
    fixed_date = datetime.date(2025, 1, 15)
    
    class MockDate:
        @staticmethod
        def today():
            return fixed_date
    
    monkeypatch.setattr("datetime.date", MockDate)
    
    history = MessageHistory(log_dir=str(tmp_path / "chat_logs"))
    await history.start()
    yield history
    await history.stop()


@pytest.fixture
def mock_today(monkeypatch):
    """Mock datetime.date.today to return a fixed date."""
    fixed_date = datetime.date(2025, 1, 15)
    
    class MockDate:
        @staticmethod
        def today():
            return fixed_date
    
    monkeypatch.setattr("datetime.date", MockDate)
    return fixed_date


@pytest.mark.asyncio
async def test_init_creates_log_directory(tmp_path):
    """Test that initialization creates the log directory."""
    log_dir = tmp_path / "chat_logs"
    assert not log_dir.exists()
    
    MessageHistory(log_dir=str(log_dir))
    assert log_dir.exists()
    assert log_dir.is_dir()


@pytest.mark.asyncio
async def test_append_message_pair(message_history):
    """Test appending a message pair writes to log file."""
    await message_history.append_message_pair("Hello", "Hi there!")
    
    # Give the background task time to write
    await asyncio.sleep(0.1)
    
    # Check the file exists
    expected_file = message_history._filename
    assert expected_file.exists()
    
    # Verify content
    async with aiofiles.open(expected_file) as f:
        content = await f.read()
        data = yaml.safe_load(content)
        
    assert "messages" in data
    assert len(data["messages"]) == 1
    assert data["messages"][0]["user"] == "Hello"
    assert data["messages"][0]["assistant"] == "Hi there!"
    assert "timestamp" in data["messages"][0]


@pytest.mark.asyncio
async def test_multiple_messages_same_file(message_history):
    """Test that multiple messages append to the same file."""
    await message_history.append_message_pair("First", "Response 1")
    await message_history.append_message_pair("Second", "Response 2")
    
    await asyncio.sleep(0.1)
    
    expected_file = message_history._filename
    
    async with aiofiles.open(expected_file) as f:
        content = await f.read()
        data = yaml.safe_load(content)
        
    assert len(data["messages"]) == 2
    assert data["messages"][0]["user"] == "First"
    assert data["messages"][1]["user"] == "Second"


@pytest.mark.asyncio
async def test_load_recent_context_empty(message_history):
    """Test loading context when no history exists."""
    context = await message_history.load_recent_context()
    assert context == []


@pytest.mark.asyncio
async def test_load_recent_context_single_file(message_history):
    """Test loading context from current session's file."""
    # Write some messages
    for i in range(5):
        await message_history.append_message_pair(f"User {i}", f"Assistant {i}")
    
    await asyncio.sleep(0.1)
    
    # Load context
    context = await message_history.load_recent_context()
    assert len(context) == 5
    assert context[0]["user"] == "User 0"
    assert context[4]["user"] == "User 4"


@pytest.mark.asyncio
async def test_load_recent_context_max_pairs(message_history):
    """Test that load_recent_context respects max_context_pairs."""
    # Create history with max 3 pairs
    history = MessageHistory(
        log_dir=str(message_history.log_dir),
        max_context_pairs=3
    )
    await history.start()
    
    # Write 10 messages
    for i in range(10):
        await message_history.append_message_pair(f"User {i}", f"Assistant {i}")
    
    await asyncio.sleep(0.1)
    
    # Load context - should only get last 3
    context = await history.load_recent_context()
    assert len(context) == 3
    assert context[0]["user"] == "User 7"
    assert context[2]["user"] == "User 9"
    
    await history.stop()


@pytest.mark.asyncio
async def test_load_recent_context_multiple_files(tmp_path):
    """Test loading context across multiple daily files."""
    log_dir = tmp_path / "chat_logs"
    log_dir.mkdir()
    
    # Create files for different days
    for day in range(1, 4):
        date = datetime.date(2025, 1, day)
        file_path = log_dir / f"chat_{date.strftime('%Y-%m-%d')}.yaml"
        
        messages = []
        for i in range(3):
            messages.append({
                "timestamp": f"2025-01-{day:02d}T10:{i:02d}:00Z",
                "user": f"Day {day} User {i}",
                "assistant": f"Day {day} Assistant {i}"
            })
        
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(yaml.dump({"messages": messages}))
    
    # Load with max 5 pairs
    history = MessageHistory(log_dir=str(log_dir), max_context_pairs=5)
    context = await history.load_recent_context()
    
    # Should get last 5 messages: all 3 from day 3, and 2 from day 2
    assert len(context) == 5
    assert context[0]["user"] == "Day 2 User 1"  # First of the 5 most recent
    assert context[1]["user"] == "Day 2 User 2"
    assert context[2]["user"] == "Day 3 User 0"
    assert context[3]["user"] == "Day 3 User 1"
    assert context[4]["user"] == "Day 3 User 2"  # Most recent


@pytest.mark.asyncio
async def test_file_created_on_start(tmp_path, monkeypatch):
    """Test that file is created with header on start."""
    # Mock date
    fixed_date = datetime.date(2025, 1, 20)
    
    class MockDate:
        @staticmethod
        def today():
            return fixed_date
    
    monkeypatch.setattr("datetime.date", MockDate)
    
    history = MessageHistory(log_dir=str(tmp_path / "chat_logs"))
    expected_file = history._filename
    
    # File shouldn't exist yet
    assert not expected_file.exists()
    
    # Start should create file with header
    await history.start()
    assert expected_file.exists()
    
    async with aiofiles.open(expected_file) as f:
        content = await f.read()
    
    assert content == "messages:\n"
    
    await history.stop()


@pytest.mark.asyncio
async def test_error_handling_corrupted_file(tmp_path):
    """Test that corrupted files don't break loading."""
    log_dir = tmp_path / "chat_logs"
    log_dir.mkdir()
    
    # Create a corrupted file
    bad_file = log_dir / "chat_2025-01-15.yaml"
    async with aiofiles.open(bad_file, 'w') as f:
        await f.write("{ invalid yaml content")
    
    history = MessageHistory(log_dir=str(log_dir))
    
    # Should return empty list and not crash
    context = await history.load_recent_context()
    assert context == []


@pytest.mark.asyncio
async def test_concurrent_writes(message_history):
    """Test that concurrent writes are handled correctly."""
    # Send many messages concurrently
    tasks = []
    for i in range(10):
        task = message_history.append_message_pair(f"Concurrent {i}", f"Response {i}")
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    await asyncio.sleep(0.2)
    
    # Verify all messages were written
    expected_file = message_history._filename
    async with aiofiles.open(expected_file) as f:
        content = await f.read()
        data = yaml.safe_load(content)
    
    assert len(data["messages"]) == 10
    user_messages = [msg["user"] for msg in data["messages"]]
    for i in range(10):
        assert f"Concurrent {i}" in user_messages


@pytest.mark.asyncio
async def test_non_blocking_writes(message_history, caplog):
    """Test that writes don't block the main execution."""
    import logging
    import time
    
    # Set log level to debug to capture debug messages
    caplog.set_level(logging.DEBUG, logger="kairix_engine.message_history")
    
    # Time how long append_message_pair takes
    start = time.time()
    await message_history.append_message_pair("Test", "Response")
    duration = time.time() - start
    
    # Should return almost immediately (< 10ms)
    assert duration < 0.01
    
    # Wait for write to complete
    await asyncio.sleep(0.1)
    
    # Check debug log was written
    assert "Writing message pair - User: Test | Assistant: Response" in caplog.text


@pytest.mark.asyncio
async def test_write_error_logging(tmp_path, caplog, monkeypatch):
    """Test that write errors log both messages separately."""
    import logging
    
    # Set log level to capture errors
    caplog.set_level(logging.ERROR)
    
    # Mock date
    fixed_date = datetime.date(2025, 1, 15)
    
    class MockDate:
        @staticmethod
        def today():
            return fixed_date
    
    monkeypatch.setattr("datetime.date", MockDate)
    
    history = MessageHistory(log_dir=str(tmp_path / "chat_logs"))
    await history.start()
    
    # Close the file to cause write error
    if history._file:
        await history._file.close()
    
    # Try to write - should fail but not crash
    await history.append_message_pair("Test message", "Test response")
    
    # Wait for write attempt
    await asyncio.sleep(0.1)
    
    # Check error logs
    assert "Failed to write message pair to file" in caplog.text
    assert "User message: Test message" in caplog.text
    assert "Assistant message: Test response" in caplog.text
    
    # Cleanup
    history._file = None
    await history.stop()