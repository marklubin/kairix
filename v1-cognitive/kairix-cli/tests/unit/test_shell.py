"""Tests for shell utilities."""

import subprocess
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

from kairix_cli.utils.shell import (
    check_command_exists,
    get_system_info,
    run_command,
    run_commands_parallel,
)


class TestRunCommand:
    """Tests for run_command function."""

    def test_run_command_success(self, mock_subprocess: MagicMock) -> None:
        """Test successful command execution."""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "output"
        mock_subprocess.return_value.stderr = ""

        success, stdout, stderr = run_command("echo test")

        assert success is True
        assert stdout == "output"
        assert stderr == ""
        mock_subprocess.assert_called_once()

    def test_run_command_failure(self, mock_subprocess: MagicMock) -> None:
        """Test failed command execution."""
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = "error"

        success, stdout, stderr = run_command("false")

        assert success is False
        assert stdout == ""
        assert stderr == "error"

    def test_run_command_with_shell(self, mock_subprocess: MagicMock) -> None:
        """Test command execution with shell=True."""
        mock_subprocess.return_value.returncode = 0

        success, _, _ = run_command("echo test | grep test", shell=True)

        assert success is True
        mock_subprocess.assert_called_with(
            "echo test | grep test",
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )

    def test_run_command_timeout(self, mock_subprocess: MagicMock) -> None:
        """Test command timeout."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired("cmd", 5)

        success, stdout, stderr = run_command("sleep 10", timeout=5)

        assert success is False
        assert stdout == ""
        assert "timed out" in stderr

    def test_run_command_exception(self, mock_subprocess: MagicMock) -> None:
        """Test command with exception."""
        mock_subprocess.side_effect = Exception("Test error")

        success, stdout, stderr = run_command("invalid")

        assert success is False
        assert stdout == ""
        assert "Test error" in stderr

    def test_run_command_no_capture(self, mock_subprocess: MagicMock) -> None:
        """Test command without output capture."""
        mock_subprocess.return_value.returncode = 0

        success, stdout, stderr = run_command("echo test", capture_output=False)

        assert success is True
        assert stdout == ""
        assert stderr == ""


class TestRunCommandsParallel:
    """Tests for run_commands_parallel function."""

    @patch("kairix_cli.utils.shell.ThreadPoolExecutor")
    def test_run_commands_parallel_success(self, mock_executor: MagicMock) -> None:
        """Test parallel command execution success."""
        # Mock the executor context manager
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance

        # Create mock futures
        future1 = MagicMock(spec=Future)
        future1.result.return_value = (True, "output1", "")

        future2 = MagicMock(spec=Future)
        future2.result.return_value = (True, "output2", "")

        # Mock submit to return our futures
        mock_executor_instance.submit.side_effect = [future1, future2]

        # Mock as_completed to return futures in order
        with patch("kairix_cli.utils.shell.as_completed") as mock_completed:
            mock_completed.return_value = [future1, future2]

            commands = [("cmd1", "echo 1"), ("cmd2", "echo 2")]
            results = run_commands_parallel(commands)

        assert len(results) == 2
        assert results[0] == ("cmd1", (True, "output1", ""))
        assert results[1] == ("cmd2", (True, "output2", ""))

    @patch("kairix_cli.utils.shell.ThreadPoolExecutor")
    def test_run_commands_parallel_with_exception(self, mock_executor: MagicMock) -> None:
        """Test parallel command execution with exception."""
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance

        future1 = MagicMock(spec=Future)
        future1.result.side_effect = Exception("Test error")

        mock_executor_instance.submit.return_value = future1

        with patch("kairix_cli.utils.shell.as_completed") as mock_completed:
            mock_completed.return_value = [future1]

            commands = [("cmd1", "echo 1")]
            results = run_commands_parallel(commands)

        assert len(results) == 1
        assert results[0][0] == "cmd1"
        assert results[0][1] == (False, "", "Test error")


class TestCheckCommandExists:
    """Tests for check_command_exists function."""

    @patch("kairix_cli.utils.shell.run_command")
    def test_command_exists(self, mock_run: MagicMock) -> None:
        """Test when command exists."""
        mock_run.return_value = (True, "/usr/bin/ls", "")

        result = check_command_exists("ls")

        assert result is True
        mock_run.assert_called_once_with("which ls")

    @patch("kairix_cli.utils.shell.run_command")
    def test_command_not_exists(self, mock_run: MagicMock) -> None:
        """Test when command doesn't exist."""
        mock_run.return_value = (False, "", "command not found")

        result = check_command_exists("nonexistent")

        assert result is False


class TestGetSystemInfo:
    """Tests for get_system_info function."""

    @patch("kairix_cli.utils.shell.run_command")
    def test_get_system_info_linux(self, mock_run: MagicMock) -> None:
        """Test getting system info on Linux."""
        # Mock uname response
        mock_run.side_effect = [
            (True, "Linux hostname 5.15.0 x86_64", ""),
            (True, "Distributor ID: Ubuntu\nDescription: Ubuntu 22.04\nRelease: 22.04", ""),
        ]

        info = get_system_info()

        assert "system" in info
        assert "Linux" in info["system"]
        assert "distributor id" in info
        assert info["distributor id"] == "Ubuntu"

    @patch("kairix_cli.utils.shell.run_command")
    def test_get_system_info_no_lsb_release(self, mock_run: MagicMock) -> None:
        """Test getting system info when lsb_release is not available."""
        mock_run.side_effect = [
            (True, "Darwin hostname 21.6.0", ""),
            (False, "", "command not found"),
        ]

        info = get_system_info()

        assert "system" in info
        assert "Darwin" in info["system"]
        assert "distributor id" not in info

    @patch("kairix_cli.utils.shell.run_command")
    def test_get_system_info_all_failures(self, mock_run: MagicMock) -> None:
        """Test getting system info when all commands fail."""
        mock_run.return_value = (False, "", "error")

        info = get_system_info()

        assert info == {}
