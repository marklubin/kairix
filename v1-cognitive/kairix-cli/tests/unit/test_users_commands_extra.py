"""Additional tests for users commands to achieve 100% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from click.testing import CliRunner

from kairix_cli.commands.users import (
    create_systemd_service,
    update_caddy_config,
    users,
)
from kairix_cli.models.user import User


class TestCreateSystemdService:
    """Tests for create_systemd_service function."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("kairix_cli.commands.users.run_command")
    def test_create_systemd_service_success(
        self,
        mock_run: MagicMock,
        mock_file: MagicMock,
    ) -> None:
        """Test successful systemd service creation."""
        mock_run.return_value = (True, "", "")

        user = User(
            subdomain="abc",
            password_hash="hash",
            web_port=6010,
            api_port=7010,
            tools_port=8010,
        )

        result = create_systemd_service("testuser", user)

        assert result is True
        assert mock_file.call_count == 2  # Two service files
        assert mock_run.call_count >= 5  # cp commands, daemon-reload, enable commands

    @patch("builtins.open", new_callable=mock_open)
    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.console")
    def test_create_systemd_service_copy_failure(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
        mock_file: MagicMock,
    ) -> None:
        """Test systemd service creation with copy failure."""
        mock_run.side_effect = [
            (False, "", "Permission denied"),  # First cp fails
        ]

        user = User(
            subdomain="abc",
            password_hash="hash",
            web_port=6010,
            api_port=7010,
            tools_port=8010,
        )

        result = create_systemd_service("testuser", user)

        assert result is False
        mock_console.print.assert_any_call("[red]Failed to create service kairix-testuser-server: Permission denied")


class TestUpdateCaddyConfigFailures:
    """Test failure scenarios for update_caddy_config."""

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.console")
    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open", new_callable=mock_open, read_data="base config\n# Wildcard catch-all for unmapped subdomains\nwildcard config")
    def test_update_caddy_config_validation_failure(
        self,
        mock_file: MagicMock,
        mock_exists: MagicMock,
        mock_cwd: MagicMock,
        mock_console: MagicMock,
        mock_run: MagicMock,
        sample_user: User,
    ) -> None:
        """Test Caddy config update with validation failure."""
        mock_cwd.return_value = Path("/Users/mark/kairix/kairix-cli")
        mock_exists.return_value = True
        mock_run.side_effect = [
            (False, "", "Invalid configuration"),  # caddy validate fails
        ]

        users_dict = {"testuser": sample_user}
        result = update_caddy_config(users_dict)

        assert result is False
        mock_console.print.assert_any_call("[red]Caddy config validation failed: Invalid configuration")

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.console")
    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open", new_callable=mock_open, read_data="base config\n# Wildcard catch-all for unmapped subdomains\nwildcard config")
    def test_update_caddy_config_copy_failure(
        self,
        mock_file: MagicMock,
        mock_exists: MagicMock,
        mock_cwd: MagicMock,
        mock_console: MagicMock,
        mock_run: MagicMock,
        sample_user: User,
    ) -> None:
        """Test Caddy config update with copy failure."""
        mock_cwd.return_value = Path("/Users/mark/kairix/kairix-cli")
        mock_exists.return_value = True
        mock_run.side_effect = [
            (True, "", ""),  # caddy validate succeeds
            (False, "", "Permission denied"),  # cp fails
        ]

        users_dict = {"testuser": sample_user}
        result = update_caddy_config(users_dict)

        assert result is False
        mock_console.print.assert_any_call("[red]Failed to update Caddyfile: Permission denied")

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.console")
    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open", new_callable=mock_open, read_data="base config\n# Wildcard catch-all for unmapped subdomains\nwildcard config")
    def test_update_caddy_config_reload_failure(
        self,
        mock_file: MagicMock,
        mock_exists: MagicMock,
        mock_cwd: MagicMock,
        mock_console: MagicMock,
        mock_run: MagicMock,
        sample_user: User,
    ) -> None:
        """Test Caddy config update with reload failure."""
        mock_cwd.return_value = Path("/Users/mark/kairix/kairix-cli")
        mock_exists.return_value = True
        mock_run.side_effect = [
            (True, "", ""),  # caddy validate succeeds
            (True, "", ""),  # cp succeeds
            (False, "", "Service not running"),  # systemctl reload fails
        ]

        users_dict = {"testuser": sample_user}
        result = update_caddy_config(users_dict)

        assert result is False
        mock_console.print.assert_any_call("[red]Failed to reload Caddy: Service not running")

    @patch("kairix_cli.commands.users.console")
    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open", new_callable=mock_open, read_data="base config\n# Wildcard catch-all for unmapped subdomains\nwildcard config")
    def test_update_caddy_config_with_disabled_users(
        self,
        mock_file: MagicMock,
        mock_exists: MagicMock,
        mock_cwd: MagicMock,
        mock_console: MagicMock,
        sample_user: User,
    ) -> None:
        """Test Caddy config update with disabled users."""
        mock_cwd.return_value = Path("/Users/mark/kairix/kairix-cli")
        mock_exists.return_value = True

        # Create a disabled user
        disabled_user = User(
            subdomain="xyz",
            password_hash="hash",
            web_port=6011,
            api_port=7011,
            tools_port=8011,
            enabled=False,
        )

        with patch("kairix_cli.commands.users.run_command") as mock_run:
            mock_run.return_value = (True, "", "")

            users_dict = {
                "enableduser": sample_user,
                "disableduser": disabled_user,
            }
            result = update_caddy_config(users_dict)

        assert result is True

        # Verify disabled user is not in config
        written_content = ""
        for call_args in mock_file().write.call_args_list:
            written_content += call_args[0][0]

        assert "abc.kairix.net" in written_content  # Enabled user
        assert "xyz.kairix.net" not in written_content  # Disabled user


class TestUserCommandsFailures:
    """Test failure scenarios for user commands."""

    @patch("kairix_cli.commands.users.load_users")
    def test_create_user_subdomain_already_used(
        self,
        mock_load: MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test creating user with already used subdomain."""
        mock_load.return_value = {"existinguser": sample_user}

        result = cli_runner.invoke(
            users,
            ["create", "newuser", "--subdomain", "abc"],  # abc is already used
            input="password123\npassword123\n",
        )

        assert result.exit_code == 0
        assert "Subdomain already in use" in result.output

    @patch("kairix_cli.commands.users.create_user_directories")
    @patch("kairix_cli.commands.users.load_users")
    def test_create_user_directory_failure(
        self,
        mock_load: MagicMock,
        mock_create_dirs: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test user creation when directory creation fails."""
        mock_load.return_value = {}
        mock_create_dirs.return_value = False

        result = cli_runner.invoke(
            users,
            ["create", "newuser"],
            input="password123\npassword123\n",
        )

        assert result.exit_code == 0
        assert "Failed to create user directories" in result.output

    @patch("kairix_cli.commands.users.create_systemd_service")
    @patch("kairix_cli.commands.users.create_user_directories")
    @patch("kairix_cli.commands.users.load_users")
    def test_create_user_service_failure(
        self,
        mock_load: MagicMock,
        mock_create_dirs: MagicMock,
        mock_create_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test user creation when service creation fails."""
        mock_load.return_value = {}
        mock_create_dirs.return_value = True
        mock_create_service.return_value = False

        result = cli_runner.invoke(
            users,
            ["create", "newuser"],
            input="password123\npassword123\n",
        )

        assert result.exit_code == 0
        assert "Failed to create systemd services" in result.output

    @patch("kairix_cli.commands.users.save_users")
    @patch("kairix_cli.commands.users.create_systemd_service")
    @patch("kairix_cli.commands.users.create_user_directories")
    @patch("kairix_cli.commands.users.load_users")
    def test_create_user_save_failure(
        self,
        mock_load: MagicMock,
        mock_create_dirs: MagicMock,
        mock_create_service: MagicMock,
        mock_save: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test user creation when saving fails."""
        mock_load.return_value = {}
        mock_create_dirs.return_value = True
        mock_create_service.return_value = True
        mock_save.return_value = False

        result = cli_runner.invoke(
            users,
            ["create", "newuser"],
            input="password123\npassword123\n",
        )

        assert result.exit_code == 0
        assert "Failed to save user configuration" in result.output

    @patch("kairix_cli.commands.users.update_caddy_config")
    @patch("kairix_cli.commands.users.save_users")
    @patch("kairix_cli.commands.users.create_systemd_service")
    @patch("kairix_cli.commands.users.create_user_directories")
    @patch("kairix_cli.commands.users.load_users")
    def test_create_user_caddy_failure(
        self,
        mock_load: MagicMock,
        mock_create_dirs: MagicMock,
        mock_create_service: MagicMock,
        mock_save: MagicMock,
        mock_update_caddy: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test user creation when Caddy update fails."""
        mock_load.return_value = {}
        mock_create_dirs.return_value = True
        mock_create_service.return_value = True
        mock_save.return_value = True
        mock_update_caddy.return_value = False

        result = cli_runner.invoke(
            users,
            ["create", "newuser"],
            input="password123\npassword123\n",
        )

        assert result.exit_code == 0
        assert "Failed to update Caddy configuration" in result.output

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.load_users")
    def test_start_user_service_failure(
        self,
        mock_load: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test starting user services with failure."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.side_effect = [
            (False, "", "Service not found"),
            (True, "", ""),
        ]

        result = cli_runner.invoke(users, ["start", "testuser"])

        assert result.exit_code == 0
        assert "Failed to start kairix-testuser-server" in result.output
        assert "Started kairix-testuser-website" in result.output

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.load_users")
    def test_stop_user_service_warning(
        self,
        mock_load: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test stopping user services with warning."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.side_effect = [
            (True, "", ""),
            (False, "", "Already stopped"),
        ]

        result = cli_runner.invoke(users, ["stop", "testuser"])

        assert result.exit_code == 0
        assert "Stopped kairix-testuser-server" in result.output
        assert "kairix-testuser-website: Already stopped" in result.output

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.save_users")
    @patch("kairix_cli.commands.users.load_users")
    def test_delete_user_with_rm_warning(
        self,
        mock_load: MagicMock,
        mock_save: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test deleting user with directory removal warning."""
        mock_load.return_value = {"testuser": sample_user}
        mock_save.return_value = True

        # Mock run_command to simulate rm failure
        def run_side_effect(cmd: str) -> tuple[bool, str, str]:
            if "rm -rf" in cmd:
                return False, "", "Directory not empty"
            return True, "", ""

        mock_run.side_effect = run_side_effect

        with patch("kairix_cli.commands.users.update_caddy_config") as mock_caddy:
            mock_caddy.return_value = True

            result = cli_runner.invoke(users, ["delete", "testuser"], input="y\n")

        assert result.exit_code == 0
        assert "Warning: Failed to remove user directory" in result.output
        assert "User 'testuser' deleted successfully" in result.output
