"""Final tests to achieve 100% code coverage."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kairix_cli.commands.system import install_magg, system
from kairix_cli.commands.users import users


class TestFinalCoverage:
    """Final tests to cover remaining lines."""

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_magg_first_command_fails_no_cargo(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test install_magg when first command fails and cargo not found."""
        mock_run.side_effect = [
            (False, "", "command not found"),  # cargo install fails
            (False, "", "cargo not found"),  # which cargo fails
        ]

        result = install_magg()

        assert result is False
        mock_console.print.assert_any_call("[red]Error: cargo is not installed. Please install Rust first.")

    @patch("kairix_cli.commands.system.run_command")
    def test_system_status_non_standard_status(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test status command with non-standard service status."""
        mock_run.side_effect = [
            (True, "activating", ""),  # Not active or inactive
            (True, "deactivating", ""),
            (True, "failed", ""),
        ]

        result = cli_runner.invoke(system, ["status"])

        assert result.exit_code == 0
        assert "kairix-server: activating" in result.output
        assert "kairix-website: deactivating" in result.output
        assert "caddy: failed" in result.output

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.load_users")
    def test_user_status_other_service_status(
        self,
        mock_load: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test user status with other service statuses."""
        from kairix_cli.models.user import User

        user = User(
            subdomain="abc",
            password_hash="hash",
            web_port=6010,
            api_port=7010,
            tools_port=8010,
        )

        mock_load.return_value = {"testuser": user}
        mock_run.side_effect = [
            (True, "failed", ""),  # Different status
            (True, "activating", ""),
        ]

        result = cli_runner.invoke(users, ["status", "testuser"])

        assert result.exit_code == 0
        assert "kairix-testuser-server: failed" in result.output
        assert "kairix-testuser-website: activating" in result.output

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_magg_all_success(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test install_magg when all commands succeed."""
        mock_run.return_value = (True, "", "")

        result = install_magg()

        assert result is True
        assert mock_run.call_count == 3

    @patch("kairix_cli.commands.system.run_commands_parallel")
    def test_stop_command_with_stderr_output(
        self,
        mock_parallel: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test stop command when service outputs to stderr."""
        mock_parallel.return_value = [
            ("kairix-server", (True, "", "")),
            ("kairix-website", (False, "", "Warning: Service not running")),
        ]

        result = cli_runner.invoke(system, ["stop"])

        assert result.exit_code == 0
        assert "Stopped kairix-server" in result.output
        assert "kairix-website: Warning: Service not running" in result.output
