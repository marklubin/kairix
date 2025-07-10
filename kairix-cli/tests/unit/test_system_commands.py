"""Tests for system management commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kairix_cli.commands.system import (
    check_root_access,
    create_system_user,
    install_caddy,
    install_doppler,
    install_just,
    install_magg,
    install_sqlite_vss,
    install_uv,
    setup_caddy_config,
    setup_systemd_services,
    system,
)


class TestCheckRootAccess:
    """Tests for check_root_access function."""

    @patch("subprocess.run")
    def test_has_root_access(self, mock_run: MagicMock) -> None:
        """Test when user has root access."""
        mock_run.return_value.returncode = 0
        assert check_root_access() is True
        mock_run.assert_called_once_with(["sudo", "-n", "true"], capture_output=True, check=False)

    @patch("subprocess.run")
    def test_no_root_access(self, mock_run: MagicMock) -> None:
        """Test when user doesn't have root access."""
        mock_run.return_value.returncode = 1
        assert check_root_access() is False

    @patch("subprocess.run")
    def test_root_access_exception(self, mock_run: MagicMock) -> None:
        """Test when checking root access raises exception."""
        mock_run.side_effect = Exception("Test error")
        assert check_root_access() is False


class TestCreateSystemUser:
    """Tests for create_system_user function."""

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_create_user_success(self, mock_console: MagicMock, mock_run: MagicMock) -> None:
        """Test successful system user creation."""
        mock_run.side_effect = [
            (False, "", ""),  # id kairix - user doesn't exist
            (True, "", ""),  # useradd succeeds
            (True, "", ""),  # mkdir succeeds
            (True, "", ""),  # chown succeeds
            (True, "", ""),  # mkdir succeeds
            (True, "", ""),  # chown succeeds
        ]

        result = create_system_user()

        assert result is True
        assert mock_run.call_count == 6
        expected_commands = [
            "id kairix",
            "sudo useradd -m -s /usr/sbin/nologin kairix",
            "sudo mkdir -p /home/kairix",
            "sudo chown -R kairix:kairix /home/kairix",
            "sudo mkdir -p /var/kairix",
            "sudo chown -R kairix:kairix /var/kairix",
        ]
        for cmd in expected_commands:
            mock_run.assert_any_call(cmd)

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_create_user_already_exists(self, mock_console: MagicMock, mock_run: MagicMock) -> None:
        """Test when user already exists."""
        mock_run.side_effect = [
            (True, "", ""),  # id kairix - user exists
            (True, "", ""),  # mkdir succeeds
            (True, "", ""),  # chown succeeds
            (True, "", ""),  # mkdir succeeds
            (True, "", ""),  # chown succeeds
        ]

        result = create_system_user()

        assert result is True

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_create_user_failure(self, mock_console: MagicMock, mock_run: MagicMock) -> None:
        """Test system user creation failure."""
        mock_run.side_effect = [
            (False, "", ""),  # id kairix - user doesn't exist
            (False, "", "permission denied"),  # useradd fails
        ]

        result = create_system_user()

        assert result is False


class TestInstallCommands:
    """Tests for install command functions."""

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_uv(self, mock_console: MagicMock, mock_run: MagicMock) -> None:
        """Test installing uv."""
        mock_run.side_effect = [
            (False, "", ""),  # which uv - not found
            (True, "", ""),   # curl install
        ]

        result = install_uv()

        assert result is True
        assert mock_run.call_count == 2
        mock_run.assert_any_call("which uv")
        mock_run.assert_any_call(
            "curl -LsSf https://astral.sh/uv/install.sh | sh",
            shell=True
        )

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_just_already_installed(self, mock_console: MagicMock, mock_run: MagicMock) -> None:
        """Test installing just when already installed."""
        mock_run.return_value = (True, "/usr/local/bin/just", "")

        result = install_just()

        assert result is True
        mock_run.assert_called_once_with("which just")

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_just_new_install(self, mock_console: MagicMock, mock_run: MagicMock) -> None:
        """Test installing just when not installed."""
        mock_run.side_effect = [
            (False, "", "command not found"),  # which just fails
            (True, "", ""),  # install succeeds
        ]

        result = install_just()

        assert result is True
        assert mock_run.call_count == 2

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_caddy(self, mock_console: MagicMock, mock_run: MagicMock) -> None:
        """Test installing Caddy."""
        mock_run.side_effect = [
            (False, "", ""),  # which caddy - not found
            (True, "", ""),   # apt update
            (True, "", ""),   # add gpg key
            (True, "", ""),   # add repo
            (True, "", ""),   # apt install
        ]

        result = install_caddy()

        assert result is True
        assert mock_run.call_count == 5

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_doppler(self, mock_console: MagicMock, mock_run: MagicMock) -> None:
        """Test installing Doppler."""
        mock_run.side_effect = [
            (False, "", ""),  # which doppler - not found
            (True, "", ""),   # curl install
        ]

        result = install_doppler()

        assert result is True
        mock_console.print.assert_any_call("[yellow]Please run 'doppler login' to authenticate")

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_install_magg_no_cargo(self, mock_console: MagicMock, mock_run: MagicMock) -> None:
        """Test installing magg when cargo is not installed."""
        mock_run.side_effect = [
            (False, "", "cargo not found"),  # cargo install fails
            (False, "", "command not found"),  # which cargo fails
        ]

        result = install_magg()

        assert result is False
        mock_console.print.assert_any_call("[red]Error: cargo is not installed. Please install Rust first.")

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    @patch("pathlib.Path.open")
    def test_install_sqlite_vss(
        self,
        mock_open: MagicMock,
        mock_read: MagicMock,
        mock_exists: MagicMock,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test installing SQLite VSS."""
        mock_run.return_value = (True, "", "")
        mock_exists.return_value = True
        mock_read.return_value = "existing content"
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = install_sqlite_vss()

        assert result is True
        assert mock_run.call_count == 4
        mock_file.write.assert_called_once()


class TestSetupCommands:
    """Tests for setup command functions."""

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    def test_setup_caddy_config_success(
        self,
        mock_exists: MagicMock,
        mock_cwd: MagicMock,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test successful Caddy config setup."""
        mock_cwd.return_value = Path("/Users/mark/kairix/kairix-cli")
        mock_exists.return_value = True
        mock_run.return_value = (True, "", "")

        result = setup_caddy_config()

        assert result is True

    @patch("kairix_cli.commands.system.console")
    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    def test_setup_caddy_config_file_not_found(
        self,
        mock_exists: MagicMock,
        mock_cwd: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test Caddy config when file not found."""
        mock_cwd.return_value = Path("/Users/mark/kairix/kairix-cli")
        mock_exists.return_value = False

        result = setup_caddy_config()

        assert result is False
        mock_console.print.assert_any_call("[red]Error: Caddyfile not found at /Users/mark/kairix/Caddyfile")

    @patch("kairix_cli.commands.system.run_command")
    @patch("kairix_cli.commands.system.console")
    def test_setup_systemd_services(self, mock_console: MagicMock, mock_run: MagicMock) -> None:
        """Test setting up systemd services."""
        mock_run.return_value = (True, "", "")

        result = setup_systemd_services()

        assert result is True
        assert mock_run.call_count == 2


class TestSystemCommands:
    """Tests for system CLI commands."""

    @patch("kairix_cli.commands.system.check_root_access")
    def test_provision_no_root_access(
        self,
        mock_check_root: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test provision command without root access."""
        mock_check_root.return_value = False

        result = cli_runner.invoke(system, ["provision"])

        assert result.exit_code == 1
        assert "requires sudo access" in result.output

    @patch("kairix_cli.commands.system.install_uv")
    @patch("kairix_cli.commands.system.check_root_access")
    def test_provision_with_skip_checks(
        self,
        mock_check_root: MagicMock,
        mock_install_uv: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test provision command with --skip-checks."""
        mock_install_uv.return_value = True

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

                                        result = cli_runner.invoke(system, ["provision", "--skip-checks"])

        assert result.exit_code == 0
        assert "System provisioned successfully" in result.output
        mock_check_root.assert_not_called()

    @patch("kairix_cli.commands.system.run_commands_parallel")
    def test_start_command(self, mock_parallel: MagicMock, cli_runner: CliRunner) -> None:
        """Test start command."""
        mock_parallel.return_value = [
            ("kairix-server", (True, "", "")),
            ("kairix-website", (True, "", "")),
        ]

        result = cli_runner.invoke(system, ["start"])

        assert result.exit_code == 0
        assert "All services started successfully" in result.output

    @patch("kairix_cli.commands.system.run_commands_parallel")
    def test_stop_command(self, mock_parallel: MagicMock, cli_runner: CliRunner) -> None:
        """Test stop command."""
        mock_parallel.return_value = [
            ("kairix-server", (True, "", "")),
            ("kairix-website", (True, "", "")),
        ]

        result = cli_runner.invoke(system, ["stop"])

        assert result.exit_code == 0
        assert "Stopped kairix-server" in result.output
        assert "Stopped kairix-website" in result.output

    @patch("kairix_cli.commands.system.run_command")
    def test_status_command(self, mock_run: MagicMock, cli_runner: CliRunner) -> None:
        """Test status command."""
        mock_run.side_effect = [
            (True, "active", ""),
            (True, "inactive", ""),
            (True, "failed", ""),
        ]

        result = cli_runner.invoke(system, ["status"])

        assert result.exit_code == 0
        assert "kairix-server: active" in result.output
        assert "kairix-website: inactive" in result.output
        assert "caddy: failed" in result.output

    @patch("kairix_cli.commands.system.run_command")
    def test_logs_command_all(self, mock_run: MagicMock, cli_runner: CliRunner) -> None:
        """Test logs command for all services."""
        mock_run.return_value = (True, "Log output", "")

        result = cli_runner.invoke(system, ["logs"])

        assert result.exit_code == 0
        assert "Logs for kairix-server" in result.output
        assert "Logs for kairix-website" in result.output

    @patch("kairix_cli.commands.system.run_command")
    def test_logs_command_specific_service(self, mock_run: MagicMock, cli_runner: CliRunner) -> None:
        """Test logs command for specific service."""
        mock_run.return_value = (True, "Server logs", "")

        result = cli_runner.invoke(system, ["logs", "--service", "server", "--lines", "100"])

        assert result.exit_code == 0
        assert "Logs for kairix-server" in result.output
        mock_run.assert_called_once_with("sudo journalctl -u kairix-server -n 100 --no-pager")

    @patch("kairix_cli.commands.system.run_commands_parallel")
    def test_restart_command(self, mock_parallel: MagicMock, cli_runner: CliRunner) -> None:
        """Test restart command."""
        mock_parallel.return_value = [
            ("kairix-server", (True, "", "")),
            ("kairix-website", (True, "", "")),
        ]

        result = cli_runner.invoke(system, ["restart"])

        assert result.exit_code == 0
        assert "All services restarted successfully" in result.output
