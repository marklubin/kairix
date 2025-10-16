"""Tests for MCPJungle manager."""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from kairix_apps.mcpjungle_manager import MCPJungleManager


@pytest.fixture
def mock_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    return tmp_path / "mcpjungle_test"


@pytest.fixture
def manager(mock_data_dir):
    """Create a MCPJungleManager instance for testing."""
    return MCPJungleManager(port=8081, data_dir=mock_data_dir)


def test_manager_initialization(manager, mock_data_dir):
    """Test that manager initializes with correct paths."""
    assert manager.port == 8081
    assert manager.data_dir == mock_data_dir
    assert manager.bin_dir == mock_data_dir / "bin"
    assert manager.binary_path == mock_data_dir / "bin" / "mcpjungle"
    assert manager.process is None


def test_get_download_url(manager):
    """Test that download URL is correctly formatted."""
    url = manager._get_download_url()
    assert "github.com" in url
    assert "mcpjungle" in url.lower()
    assert ".tar.gz" in url


def test_get_mcp_endpoint(manager):
    """Test MCP endpoint URL generation."""
    assert manager.get_mcp_endpoint() == "http://localhost:8081/mcp"


@pytest.mark.asyncio
async def test_health_check_no_process(manager):
    """Test health check when process is not running."""
    assert await manager.health_check() is False


@pytest.mark.asyncio
async def test_health_check_with_running_process(manager):
    """Test health check with a running process."""
    # Mock a running process
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Process is still running
    manager.process = mock_process

    assert await manager.health_check() is True


@pytest.mark.asyncio
async def test_health_check_with_terminated_process(manager):
    """Test health check with a terminated process."""
    # Mock a terminated process
    mock_process = MagicMock()
    mock_process.poll.return_value = 1  # Process has terminated
    manager.process = mock_process

    assert await manager.health_check() is False
    assert manager.process is None  # Should be cleared


@pytest.mark.asyncio
async def test_stop_when_not_running(manager):
    """Test stopping when MCPJungle is not running."""
    # Should not raise an error
    await manager.stop()


@pytest.mark.asyncio
async def test_stop_graceful(manager):
    """Test graceful shutdown of MCPJungle."""
    # Mock a running process
    mock_process = MagicMock()
    mock_process.wait = MagicMock()
    manager.process = mock_process

    await manager.stop()

    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once()
    assert manager.process is None


@pytest.mark.asyncio
async def test_stop_force_kill(manager):
    """Test force kill when graceful shutdown fails."""
    import subprocess

    # Mock a process that won't terminate gracefully
    mock_process = MagicMock()
    mock_process.wait.side_effect = subprocess.TimeoutExpired("mcpjungle", 10)
    manager.process = mock_process

    await manager.stop()

    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_called_once()
    assert manager.process is None


@pytest.mark.asyncio
@patch('kairix_apps.mcpjungle_manager.subprocess.Popen')
async def test_start_success(mock_popen, manager, mock_data_dir):
    """Test successful MCPJungle startup."""
    # Create binary file
    manager.binary_path.parent.mkdir(parents=True, exist_ok=True)
    manager.binary_path.touch()

    # Mock successful process start
    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Process is running
    mock_process.pid = 12345
    mock_popen.return_value = mock_process

    await manager.start()

    assert manager.process is not None
    assert manager.process.pid == 12345
    mock_popen.assert_called_once()


@pytest.mark.asyncio
async def test_start_already_running(manager):
    """Test starting when MCPJungle is already running."""
    # Set up a running process
    manager.process = MagicMock()

    await manager.start()

    # Process should remain the same
    assert manager.process is not None


@pytest.mark.asyncio
@patch('kairix_apps.mcpjungle_manager.subprocess.Popen')
async def test_start_immediate_failure(mock_popen, manager):
    """Test handling of immediate process failure."""
    # Create binary file
    manager.binary_path.parent.mkdir(parents=True, exist_ok=True)
    manager.binary_path.touch()

    # Mock process that terminates immediately
    mock_process = MagicMock()
    mock_process.poll.return_value = 1  # Process terminated
    mock_process.communicate.return_value = ("stdout", "stderr")
    mock_popen.return_value = mock_process

    with pytest.raises(RuntimeError, match="terminated immediately"):
        await manager.start()

    assert manager.process is None
