"""Additional tests to achieve 100% code coverage."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kairix_cli.commands.system import install_magg, setup_systemd_services
from kairix_cli.commands.users import users


class TestSystemCoverageExtras:
    """Additional tests for system commands coverage."""

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_magg_echo_fails(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test install_magg when echo to config fails."""
        mock_run.side_effect = [
            (False, "", ""),  # which magg - not found
            (True, "/usr/bin/cargo", ""),  # which cargo - found
            (True, "", ""),  # cargo install succeeds
            (True, "", ""),  # mkdir succeeds
            (False, "", "permission denied"),  # echo fails
        ]

        result = install_magg()

        assert result is False

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_setup_systemd_services_warning_case(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test setup_systemd_services when services not found."""
        mock_run.side_effect = [
            (True, "", ""),  # daemon-reload succeeds
            (False, "", "Failed to enable unit: Unit file kairix-server.service does not exist"),  # enable fails
        ]

        result = setup_systemd_services()

        assert result is False
        mock_console.print.assert_any_call("[yellow]Warning: systemd services not found. You may need to create them first.")


class TestUsersCoverageExtras:
    """Additional tests for users commands coverage."""

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.load_users")
    def test_user_status_not_found(
        self,
        mock_load: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test status command for non-existent user."""
        mock_load.return_value = {}

        result = cli_runner.invoke(users, ["status", "nonexistent"])

        assert result.exit_code == 0
        assert "User 'nonexistent' not found" in result.output

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.load_users")
    def test_start_user_not_found(
        self,
        mock_load: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test start command for non-existent user."""
        mock_load.return_value = {}

        result = cli_runner.invoke(users, ["start", "nonexistent"])

        assert result.exit_code == 0
        assert "User 'nonexistent' not found" in result.output

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.load_users")
    def test_stop_user_not_found(
        self,
        mock_load: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test stop command for non-existent user."""
        mock_load.return_value = {}

        result = cli_runner.invoke(users, ["stop", "nonexistent"])

        assert result.exit_code == 0
        assert "User 'nonexistent' not found" in result.output

    @patch("kairix_cli.commands.users.load_users")
    def test_toggle_user_not_found(
        self,
        mock_load: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test toggle command for non-existent user."""
        mock_load.return_value = {}

        result = cli_runner.invoke(users, ["toggle", "nonexistent"])

        assert result.exit_code == 0
        assert "User 'nonexistent' not found" in result.output
