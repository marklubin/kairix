"""Integration tests for the Kairix CLI."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from kairix_cli.main import cli


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def test_full_cli_workflow(self, cli_runner: CliRunner) -> None:
        """Test a full CLI workflow from help to commands."""
        # Test help
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "system" in result.output
        assert "users" in result.output

        # Test system help
        result = cli_runner.invoke(cli, ["system", "--help"])
        assert result.exit_code == 0
        assert "provision" in result.output
        assert "start" in result.output
        assert "stop" in result.output

        # Test users help
        result = cli_runner.invoke(cli, ["users", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output
        assert "delete" in result.output

    @patch("kairix_cli.commands.system.run_command")
    def test_system_status_integration(
        self,
        mock_run: pytest.MonkeyPatch,
        cli_runner: CliRunner,
    ) -> None:
        """Test system status command integration."""
        mock_run.side_effect = [
            (True, "active", ""),
            (True, "active", ""),
            (True, "active", ""),
        ]

        result = cli_runner.invoke(cli, ["system", "status"])

        assert result.exit_code == 0
        assert "kairix-server" in result.output
        assert "kairix-website" in result.output
        assert "caddy" in result.output
        assert "active" in result.output

    def test_user_workflow_integration(self, cli_runner: CliRunner) -> None:
        """Test user management workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".config" / "kairix" / "users.json"
            config_path.parent.mkdir(parents=True)

            with patch("kairix_cli.commands.users.get_user_config_path") as mock_path:
                mock_path.return_value = config_path

                # List users (should be empty)
                result = cli_runner.invoke(cli, ["users", "list"])
                assert result.exit_code == 0
                assert "No users found" in result.output

                # Create a user (mocking the actual creation steps)
                with (
                    patch("kairix_cli.commands.users.create_user_directories") as mock_dirs,
                    patch("kairix_cli.commands.users.create_systemd_service") as mock_service,
                    patch("kairix_cli.commands.users.update_caddy_config") as mock_caddy,
                ):
                    mock_dirs.return_value = True
                    mock_service.return_value = True
                    mock_caddy.return_value = True

                    result = cli_runner.invoke(
                        cli,
                        ["users", "create", "testuser", "--subdomain", "xyz"],
                        input="password123\npassword123\n",
                    )

                    assert result.exit_code == 0
                    assert "User 'testuser' created successfully" in result.output
                    assert "xyz.kairix.net" in result.output

                # List users again (should have one)
                result = cli_runner.invoke(cli, ["users", "list"])
                assert result.exit_code == 0
                assert "testuser" in result.output
                assert "xyz.kairix.net" in result.output

    def test_error_handling_integration(self, cli_runner: CliRunner) -> None:
        """Test error handling in the CLI."""
        # Invalid command
        result = cli_runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0

        # Invalid subcommand
        result = cli_runner.invoke(cli, ["system", "invalid-subcommand"])
        assert result.exit_code != 0

        # Missing required arguments
        result = cli_runner.invoke(cli, ["users", "create"])
        assert result.exit_code != 0
