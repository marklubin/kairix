"""Tests for new user management commands (logs, restart, setenv, getenv)."""

from unittest import mock

import pytest
from click.testing import CliRunner

from kairix_cli.commands.users import users
from kairix_cli.models.user import User


class TestUserLogsCommand:
    """Test the users logs command."""

    @pytest.fixture
    def sample_user(self) -> User:
        """Create a sample user."""
        return User(
            subdomain="abc",
            password_hash="hashed",
            web_port=6010,
            api_port=6011,
            tools_port=6012,
            enabled=True,
        )

    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch("kairix_cli.commands.users.run_command")
    def test_logs_all_services(self, mock_run, mock_load, cli_runner, sample_user):
        """Test viewing logs for all services."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.return_value = (True, "log output", "")

        result = cli_runner.invoke(users, ["logs", "testuser"])

        assert result.exit_code == 0
        assert "Viewing last 50 lines of logs for user 'testuser'" in result.output
        assert mock_run.call_count == 2
        mock_run.assert_any_call("sudo journalctl -u kairix-testuser-server -n 50 --no-pager")
        mock_run.assert_any_call("sudo journalctl -u kairix-testuser-website -n 50 --no-pager")

    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch("kairix_cli.commands.users.run_command")
    def test_logs_specific_service(self, mock_run, mock_load, cli_runner, sample_user):
        """Test viewing logs for specific service."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.return_value = (True, "server logs", "")

        result = cli_runner.invoke(users, ["logs", "testuser", "--service", "server", "-n", "100"])

        assert result.exit_code == 0
        assert mock_run.call_count == 1
        mock_run.assert_called_with("sudo journalctl -u kairix-testuser-server -n 100 --no-pager")

    @mock.patch("kairix_cli.commands.users.load_users")
    def test_logs_user_not_found(self, mock_load, cli_runner):
        """Test logs command when user not found."""
        mock_load.return_value = {}

        result = cli_runner.invoke(users, ["logs", "nonexistent"])

        assert result.exit_code == 0
        assert "Error: User 'nonexistent' not found" in result.output


class TestUserRestartCommand:
    """Test the users restart command."""

    @pytest.fixture
    def sample_user(self) -> User:
        """Create a sample user."""
        return User(
            subdomain="abc",
            password_hash="hashed",
            web_port=6010,
            api_port=6011,
            tools_port=6012,
            enabled=True,
        )

    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch("kairix_cli.commands.users.run_command")
    def test_restart_success(self, mock_run, mock_load, cli_runner, sample_user):
        """Test successful restart of user services."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.return_value = (True, "", "")

        result = cli_runner.invoke(users, ["restart", "testuser"])

        assert result.exit_code == 0
        assert "Restarting services for user 'testuser'" in result.output
        assert "All services for user 'testuser' restarted successfully" in result.output
        assert mock_run.call_count == 2
        mock_run.assert_any_call("sudo systemctl restart kairix-testuser-server")
        mock_run.assert_any_call("sudo systemctl restart kairix-testuser-website")

    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch("kairix_cli.commands.users.run_command")
    def test_restart_partial_failure(self, mock_run, mock_load, cli_runner, sample_user):
        """Test restart when one service fails."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.side_effect = [
            (True, "", ""),  # server restart succeeds
            (False, "", "Failed to restart"),  # website restart fails
        ]

        result = cli_runner.invoke(users, ["restart", "testuser"])

        assert result.exit_code == 0
        assert "Failed to restart kairix-testuser-website" in result.output
        assert "Some services failed to restart" in result.output


class TestUserSetenvCommand:
    """Test the users setenv command."""

    @pytest.fixture
    def sample_user(self) -> User:
        """Create a sample user."""
        return User(
            subdomain="abc",
            password_hash="hashed",
            web_port=6010,
            api_port=6011,
            tools_port=6012,
            enabled=True,
        )

    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch("kairix_cli.commands.users.run_command")
    def test_setenv_success(self, mock_run, mock_load, cli_runner, sample_user):
        """Test setting environment variable successfully."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.return_value = (True, "", "")

        result = cli_runner.invoke(users, ["setenv", "testuser", "MY_VAR", "my_value"])

        assert result.exit_code == 0
        assert "Setting MY_VAR for user 'testuser'" in result.output
        assert "✓ Set MY_VAR for user 'testuser'" in result.output
        assert "Restart user services for changes to take effect" in result.output
        mock_run.assert_called_once_with("doppler secrets set MY_VAR=my_value -c user-testuser -p kairix --silent")

    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch("kairix_cli.commands.users.run_command")
    def test_setenv_failure(self, mock_run, mock_load, cli_runner, sample_user):
        """Test setenv when Doppler command fails."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.return_value = (False, "", "Permission denied")

        result = cli_runner.invoke(users, ["setenv", "testuser", "MY_VAR", "my_value"])

        assert result.exit_code == 0
        assert "Failed to set environment variable: Permission denied" in result.output

    @mock.patch("kairix_cli.commands.users.load_users")
    def test_setenv_user_not_found(self, mock_load, cli_runner):
        """Test setenv when user not found."""
        mock_load.return_value = {}

        result = cli_runner.invoke(users, ["setenv", "nonexistent", "MY_VAR", "value"])

        assert result.exit_code == 0
        assert "Error: User 'nonexistent' not found" in result.output


class TestUserGetenvCommand:
    """Test the users getenv command."""

    @pytest.fixture
    def sample_user(self) -> User:
        """Create a sample user."""
        return User(
            subdomain="abc",
            password_hash="hashed",
            web_port=6010,
            api_port=6011,
            tools_port=6012,
            enabled=True,
        )

    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch("kairix_cli.commands.users.run_command")
    def test_getenv_success(self, mock_run, mock_load, cli_runner, sample_user):
        """Test getting environment variables successfully."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.return_value = (True, "MY_VAR=value\nAPI_KEY=secret", "")

        result = cli_runner.invoke(users, ["getenv", "testuser"])

        assert result.exit_code == 0
        assert "Environment variables for user 'testuser'" in result.output
        assert "MY_VAR=value" in result.output
        assert "API_KEY=secret" in result.output
        mock_run.assert_called_once_with("doppler secrets -c user-testuser -p kairix")

    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch("kairix_cli.commands.users.run_command")
    def test_getenv_failure(self, mock_run, mock_load, cli_runner, sample_user):
        """Test getenv when Doppler command fails."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.return_value = (False, "", "Config not found")

        result = cli_runner.invoke(users, ["getenv", "testuser"])

        assert result.exit_code == 0
        assert "Failed to get environment variables: Config not found" in result.output