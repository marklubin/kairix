"""Pytest configuration and fixtures."""

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kairix_cli.models.user import User


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_subprocess() -> Generator[MagicMock, None, None]:
    """Mock subprocess module."""
    with patch("subprocess.run") as mock:
        mock.return_value.returncode = 0
        mock.return_value.stdout = ""
        mock.return_value.stderr = ""
        yield mock


@pytest.fixture
def mock_console() -> Generator[MagicMock, None, None]:
    """Mock rich console."""
    with patch("kairix_cli.commands.system.console") as mock:
        yield mock


@pytest.fixture
def temp_config_dir() -> Generator[Path, None, None]:
    """Create a temporary configuration directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".config" / "kairix"
        config_dir.mkdir(parents=True)
        with patch("kairix_cli.commands.users.get_user_config_path") as mock:
            mock.return_value = config_dir / "users.json"
            yield config_dir


@pytest.fixture
def sample_user() -> User:
    """Create a sample user for testing."""
    return User(
        subdomain="abc",
        password_hash="$2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNmpkT/5qqR7hx4IjWJPDhjvG",
        web_port=6010,
        api_port=7010,
        tools_port=8010,
        enabled=True,
    )


@pytest.fixture
def sample_users_config(temp_config_dir: Path, sample_user: User) -> dict[str, Any]:
    """Create a sample users configuration file."""
    users = {
        "testuser": sample_user.model_dump(),
    }

    config_file = temp_config_dir / "users.json"
    with config_file.open("w") as f:
        json.dump(users, f)

    return users


@pytest.fixture
def mock_run_command() -> Generator[MagicMock, None, None]:
    """Mock the run_command utility."""
    with patch("kairix_cli.utils.shell.run_command") as mock:
        mock.return_value = (True, "", "")
        yield mock


@pytest.fixture
def mock_path_exists() -> Generator[MagicMock, None, None]:
    """Mock Path.exists method."""
    with patch("pathlib.Path.exists") as mock:
        mock.return_value = True
        yield mock
