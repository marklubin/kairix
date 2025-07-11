"""Tests for shared system service commands."""

from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from kairix_cli.commands.system import setup_systemd_services, system


class TestSetupSystemdServices:
    """Test setup_systemd_services function."""

    @mock.patch("kairix_cli.commands.system.Path")
    @mock.patch("kairix_cli.commands.system.run_command")
    @mock.patch("kairix_cli.commands.system.console")
    def test_setup_systemd_services_magg_exists(self, mock_console, mock_run, mock_path):
        """Test setup when magg service already exists."""
        # Mock magg service exists
        mock_magg_service = mock.MagicMock()
        mock_magg_service.exists.return_value = True
        mock_path.return_value = mock_magg_service
        
        mock_run.return_value = (True, "", "")

        result = setup_systemd_services()

        assert result is True
        assert mock_run.call_count == 3  # Only daemon-reload and enable commands
        mock_run.assert_any_call("sudo systemctl daemon-reload")
        mock_run.assert_any_call("sudo systemctl enable magg")
        mock_run.assert_any_call("sudo systemctl enable caddy")

    @mock.patch("kairix_cli.commands.system.Path")
    @mock.patch("kairix_cli.commands.system.run_command")
    @mock.patch("kairix_cli.commands.system.console")
    def test_setup_systemd_services_create_magg(self, mock_console, mock_run, mock_path):
        """Test setup when magg service needs to be created."""
        # Mock magg service doesn't exist
        mock_magg_service = mock.MagicMock()
        mock_magg_service.exists.return_value = False
        mock_path.return_value = mock_magg_service
        
        mock_run.return_value = (True, "", "")

        result = setup_systemd_services()

        assert result is True
        assert mock_run.call_count == 4  # Create service + daemon-reload + enables
        # Check service file creation
        create_service_call = mock_run.call_args_list[0][0][0]
        assert "echo" in create_service_call
        assert "MCP Aggregator Service" in create_service_call
        assert "/home/kairix/.cargo/bin/magg" in create_service_call

    @mock.patch("kairix_cli.commands.system.Path")
    @mock.patch("kairix_cli.commands.system.run_command")
    @mock.patch("kairix_cli.commands.system.console")
    def test_setup_systemd_services_create_fails(self, mock_console, mock_run, mock_path):
        """Test setup when service creation fails."""
        mock_magg_service = mock.MagicMock()
        mock_magg_service.exists.return_value = False
        mock_path.return_value = mock_magg_service
        
        # Service creation fails
        mock_run.return_value = (False, "", "Permission denied")

        result = setup_systemd_services()

        assert result is False
        mock_console.print.assert_any_call("[red]Failed to create magg service")


class TestSharedSystemCommands:
    """Test shared system commands (start, stop, status, logs)."""

    @mock.patch("kairix_cli.commands.system.run_commands_parallel")
    def test_start_shared_services(self, mock_run_parallel, cli_runner):
        """Test starting shared services."""
        mock_run_parallel.return_value = [
            ("magg", (True, "", "")),
            ("caddy", (True, "", "")),
        ]

        result = cli_runner.invoke(system, ["start"])

        assert result.exit_code == 0
        assert "Starting shared Kairix services" in result.output
        assert "✓ Started magg" in result.output
        assert "✓ Started caddy" in result.output
        assert "All shared services started successfully" in result.output
        assert "User-specific services are managed with" in result.output

    @mock.patch("kairix_cli.commands.system.run_commands_parallel")
    def test_stop_shared_services(self, mock_run_parallel, cli_runner):
        """Test stopping shared services."""
        mock_run_parallel.return_value = [
            ("magg", (True, "", "")),
            ("caddy", (True, "", "")),
        ]

        result = cli_runner.invoke(system, ["stop"])

        assert result.exit_code == 0
        assert "Stopping shared Kairix services" in result.output
        assert "✓ Stopped magg" in result.output
        assert "✓ Stopped caddy" in result.output

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_status_shared_services(self, mock_run, cli_runner):
        """Test checking status of shared services."""
        mock_run.side_effect = [
            (True, "active", ""),  # magg status
            (True, "inactive", ""),  # caddy status
        ]

        result = cli_runner.invoke(system, ["status"])

        assert result.exit_code == 0
        assert "Checking shared Kairix services status" in result.output
        assert "● magg: active" in result.output
        assert "● caddy: inactive" in result.output

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_logs_all_shared_services(self, mock_run, cli_runner):
        """Test viewing logs for all shared services."""
        mock_run.return_value = (True, "log output", "")

        result = cli_runner.invoke(system, ["logs"])

        assert result.exit_code == 0
        assert "Viewing last 50 lines of shared service logs" in result.output
        assert mock_run.call_count == 2
        mock_run.assert_any_call("sudo journalctl -u magg -n 50 --no-pager")
        mock_run.assert_any_call("sudo journalctl -u caddy -n 50 --no-pager")
        assert "For user-specific logs, use" in result.output

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_logs_specific_service(self, mock_run, cli_runner):
        """Test viewing logs for specific shared service."""
        mock_run.return_value = (True, "magg logs", "")

        result = cli_runner.invoke(system, ["logs", "--service", "magg", "-n", "100"])

        assert result.exit_code == 0
        assert mock_run.call_count == 1
        mock_run.assert_called_with("sudo journalctl -u magg -n 100 --no-pager")

    @mock.patch("kairix_cli.commands.system.run_commands_parallel")
    def test_restart_shared_services(self, mock_run_parallel, cli_runner):
        """Test restarting shared services."""
        mock_run_parallel.return_value = [
            ("magg", (True, "", "")),
            ("caddy", (True, "", "")),
        ]

        result = cli_runner.invoke(system, ["restart"])

        assert result.exit_code == 0
        assert "Restarting shared Kairix services" in result.output
        assert "✓ Restarted magg" in result.output
        assert "✓ Restarted caddy" in result.output
        assert "All shared services restarted successfully" in result.output