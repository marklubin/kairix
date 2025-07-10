"""Additional tests for system commands to achieve 100% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kairix_cli.commands.system import (
    install_caddy,
    install_magg,
    install_sqlite_vss,
    setup_caddy_config,
    system,
)


class TestInstallCaddyEdgeCases:
    """Edge case tests for install_caddy."""

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_caddy_partial_failure(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test install_caddy when one command fails."""
        mock_run.side_effect = [
            (False, "", ""),  # which caddy - not found
            (True, "", ""),  # First command succeeds
            (False, "", "error"),  # Second command fails
        ]

        result = install_caddy()

        assert result is False


class TestInstallMaggEdgeCases:
    """Edge case tests for install_magg."""

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_magg_mkdir_fails(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test install_magg when mkdir fails."""
        mock_run.side_effect = [
            (False, "", ""),  # which magg - not found
            (True, "", ""),  # which cargo - found
            (True, "", ""),  # cargo install succeeds
            (False, "", "permission denied"),  # mkdir fails
        ]

        result = install_magg()

        assert result is False


class TestInstallSqliteVssEdgeCases:
    """Edge case tests for install_sqlite_vss."""

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_sqlite_vss_download_fails(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test install_sqlite_vss when download fails."""
        mock_run.side_effect = [
            (True, "", ""),  # mkdir succeeds
            (False, "", "download error"),  # curl fails
        ]

        result = install_sqlite_vss()

        assert result is False

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_install_sqlite_vss_bashrc_not_exists(
        self,
        mock_read: MagicMock,
        mock_exists: MagicMock,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test install_sqlite_vss when bashrc doesn't exist."""
        mock_run.return_value = (True, "", "")
        mock_exists.return_value = False

        result = install_sqlite_vss()

        assert result is True
        mock_read.assert_not_called()


class TestSetupCaddyConfigEdgeCases:
    """Edge case tests for setup_caddy_config."""

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    def test_setup_caddy_config_command_fails(
        self,
        mock_exists: MagicMock,
        mock_cwd: MagicMock,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test setup_caddy_config when command fails."""
        mock_cwd.return_value = Path("/Users/mark/kairix/kairix-cli")
        mock_exists.return_value = True
        mock_run.return_value = (False, "", "permission denied")

        result = setup_caddy_config()

        assert result is False


class TestSystemProvisionEdgeCases:
    """Edge case tests for system provision command."""

    @patch("kairix_cli.commands.system.install_uv")
    @patch("kairix_cli.commands.system.check_root_access")
    def test_provision_install_failure(
        self,
        mock_check_root: MagicMock,
        mock_install_uv: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test provision when an install step fails."""
        mock_check_root.return_value = True
        mock_install_uv.return_value = False  # First step fails

        with patch("kairix_cli.commands.system.install_just") as mock_just:
            mock_just.return_value = True
            with patch("kairix_cli.commands.system.install_caddy") as mock_caddy:
                mock_caddy.return_value = True
                with patch("kairix_cli.commands.system.install_doppler") as mock_doppler:
                    mock_doppler.return_value = True
                    with patch("kairix_cli.commands.system.install_magg") as mock_magg:
                        mock_magg.return_value = True
                        with patch("kairix_cli.commands.system.install_sqlite_vss") as mock_sqlite:
                            mock_sqlite.return_value = True
                            with patch("kairix_cli.commands.system.create_system_user") as mock_user:
                                mock_user.return_value = True
                                with patch("kairix_cli.commands.system.setup_caddy_config") as mock_caddy_config:
                                    mock_caddy_config.return_value = True
                                    with patch("kairix_cli.commands.system.setup_systemd_services") as mock_systemd:
                                        mock_systemd.return_value = True

                                        result = cli_runner.invoke(system, ["provision"])

        assert result.exit_code == 0
        assert "Provisioning completed with errors" in result.output
        assert "Installing dependencies" in result.output

    @patch("kairix_cli.commands.system.install_uv")
    @patch("kairix_cli.commands.system.check_root_access")
    def test_provision_with_exception(
        self,
        mock_check_root: MagicMock,
        mock_install_uv: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test provision when a step raises exception."""
        mock_check_root.return_value = True
        mock_install_uv.side_effect = Exception("Test exception")

        with patch("kairix_cli.commands.system.install_just") as mock_just:
            mock_just.return_value = True
            with patch("kairix_cli.commands.system.install_caddy") as mock_caddy:
                mock_caddy.return_value = True
                with patch("kairix_cli.commands.system.install_doppler") as mock_doppler:
                    mock_doppler.return_value = True
                    with patch("kairix_cli.commands.system.install_magg") as mock_magg:
                        mock_magg.return_value = True
                        with patch("kairix_cli.commands.system.install_sqlite_vss") as mock_sqlite:
                            mock_sqlite.return_value = True
                            with patch("kairix_cli.commands.system.create_system_user") as mock_user:
                                mock_user.return_value = True
                                with patch("kairix_cli.commands.system.setup_caddy_config") as mock_caddy_config:
                                    mock_caddy_config.return_value = True
                                    with patch("kairix_cli.commands.system.setup_systemd_services") as mock_systemd:
                                        mock_systemd.return_value = True

                                        result = cli_runner.invoke(system, ["provision"])

        assert result.exit_code == 0
        assert "Test exception" in result.output


class TestSystemCommandsFailures:
    """Test failure scenarios for system commands."""

    @patch("kairix_cli.commands.system.run_commands_parallel")
    def test_start_command_partial_failure(
        self,
        mock_parallel: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test start command with partial failure."""
        mock_parallel.return_value = [
            ("kairix-server", (True, "", "")),
            ("kairix-website", (False, "", "Failed to start")),
        ]

        result = cli_runner.invoke(system, ["start"])

        assert result.exit_code == 0
        assert "Failed to start kairix-website" in result.output
        assert "Some services failed to start" in result.output

    @patch("kairix_cli.commands.system.run_command")
    def test_logs_command_failure(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test logs command when journalctl fails."""
        mock_run.return_value = (False, "", "Permission denied")

        result = cli_runner.invoke(system, ["logs", "--service", "server"])

        assert result.exit_code == 0
        assert "Failed to get logs" in result.output

    @patch("kairix_cli.commands.system.run_commands_parallel")
    def test_restart_command_failure(
        self,
        mock_parallel: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test restart command with failures."""
        mock_parallel.return_value = [
            ("kairix-server", (False, "", "Service not found")),
            ("kairix-website", (False, "", "Permission denied")),
        ]

        result = cli_runner.invoke(system, ["restart"])

        assert result.exit_code == 0
        assert "Failed to restart kairix-server" in result.output
        assert "Failed to restart kairix-website" in result.output
        assert "Some services failed to restart" in result.output
