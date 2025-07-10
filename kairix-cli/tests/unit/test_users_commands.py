"""Tests for user management commands."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import bcrypt
from click.testing import CliRunner

from kairix_cli.commands.users import (
    create_user_directories,
    generate_subdomain,
    get_next_port_set,
    get_user_config_path,
    hash_password,
    load_users,
    save_users,
    update_caddy_config,
    users,
)
from kairix_cli.models.user import User


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_generate_subdomain(self) -> None:
        """Test subdomain generation."""
        subdomain = generate_subdomain()
        assert len(subdomain) == 3
        assert subdomain.isalnum()
        assert subdomain.islower()

        # Test randomness
        subdomains = {generate_subdomain() for _ in range(100)}
        assert len(subdomains) > 50  # Should be unique most of the time

    def test_hash_password(self) -> None:
        """Test password hashing."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert hashed.startswith("$2b$14$") or hashed.startswith("$2a$14$")  # Both versions are valid
        assert len(hashed) == 60
        assert bcrypt.checkpw(password.encode(), hashed.encode())

    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.home")
    def test_get_user_config_path(self, mock_home: MagicMock, mock_mkdir: MagicMock) -> None:
        """Test getting user config path."""
        mock_home.return_value = Path("/home/testuser")

        path = get_user_config_path()

        assert path == Path("/home/testuser/.config/kairix/users.json")
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_get_next_port_set_empty(self) -> None:
        """Test getting ports with no users."""
        web, api, tools = get_next_port_set({})
        assert (web, api, tools) == (6010, 7010, 8010)

    def test_get_next_port_set_with_users(self, sample_user: User) -> None:
        """Test getting ports with existing users."""
        users_dict = {
            "user1": sample_user,
            "user2": User(
                subdomain="xyz",
                password_hash="hash",
                web_port=6011,
                api_port=7011,
                tools_port=8011,
            ),
        }

        web, api, tools = get_next_port_set(users_dict)
        assert (web, api, tools) == (6012, 7012, 8012)


class TestUserPersistence:
    """Tests for user loading and saving."""

    def test_load_users_empty(self, temp_config_dir: Path) -> None:
        """Test loading users when file doesn't exist."""
        users_dict = load_users()
        assert users_dict == {}

    def test_load_users_with_data(self, sample_users_config: dict[str, Any]) -> None:
        """Test loading users from file."""
        users_dict = load_users()

        assert len(users_dict) == 1
        assert "testuser" in users_dict
        assert users_dict["testuser"].subdomain == "abc"

    @patch("kairix_cli.commands.users.get_user_config_path")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open")
    def test_load_users_invalid_json(
        self,
        mock_open: MagicMock,
        mock_exists: MagicMock,
        mock_path: MagicMock,
    ) -> None:
        """Test loading users with invalid JSON."""
        mock_path.return_value = Path("/test/users.json")
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "invalid json"

        users_dict = load_users()

        assert users_dict == {}

    def test_save_users_success(self, temp_config_dir: Path, sample_user: User) -> None:
        """Test saving users successfully."""
        users_dict = {"testuser": sample_user}

        result = save_users(users_dict)

        assert result is True

        # Verify saved data
        config_file = temp_config_dir / "users.json"
        with config_file.open() as f:
            data = json.load(f)

        assert "testuser" in data
        assert data["testuser"]["subdomain"] == "abc"

    @patch("kairix_cli.commands.users.get_user_config_path")
    @patch("pathlib.Path.open")
    def test_save_users_failure(
        self,
        mock_open: MagicMock,
        mock_path: MagicMock,
        sample_user: User,
    ) -> None:
        """Test saving users with error."""
        mock_path.return_value = Path("/test/users.json")
        mock_open.side_effect = PermissionError("No write access")

        result = save_users({"testuser": sample_user})

        assert result is False


class TestUserDirectories:
    """Tests for user directory management."""

    @patch("kairix_cli.commands.users.run_command")
    def test_create_user_directories_success(self, mock_run: MagicMock) -> None:
        """Test successful directory creation."""
        mock_run.return_value = (True, "", "")

        result = create_user_directories("testuser")

        assert result is True
        assert mock_run.call_count == 3
        expected_commands = [
            "sudo mkdir -p /var/kairix/users/testuser",
            "sudo mkdir -p /var/kairix/users/testuser/sqlite",
            "sudo chown -R kairix:kairix /var/kairix/users/testuser",
        ]
        for cmd in expected_commands:
            mock_run.assert_any_call(cmd)

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.console")
    def test_create_user_directories_failure(
        self,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test directory creation failure."""
        mock_run.side_effect = [
            (True, "", ""),
            (False, "", "Permission denied"),
        ]

        result = create_user_directories("testuser")

        assert result is False
        mock_console.print.assert_any_call("[red]Error creating directories: Permission denied")


class TestCaddyConfig:
    """Tests for Caddy configuration updates."""

    @patch("kairix_cli.commands.users.run_command")
    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open", new_callable=mock_open, read_data="base config\n# Wildcard catch-all for unmapped subdomains\nwildcard config")
    def test_update_caddy_config_success(
        self,
        mock_file: MagicMock,
        mock_exists: MagicMock,
        mock_cwd: MagicMock,
        mock_run: MagicMock,
        sample_user: User,
    ) -> None:
        """Test successful Caddy config update."""
        mock_cwd.return_value = Path("/Users/mark/kairix/kairix-cli")
        mock_exists.return_value = True
        mock_run.side_effect = [
            (True, "", ""),  # caddy validate
            (True, "", ""),  # cp
            (True, "", ""),  # systemctl reload
        ]

        users_dict = {"testuser": sample_user}
        result = update_caddy_config(users_dict)

        assert result is True
        assert mock_run.call_count == 3

        # Verify the written config contains user subdomain
        written_content = ""
        for call_args in mock_file().write.call_args_list:
            written_content += call_args[0][0]

        assert "abc.kairix.net" in written_content
        assert "testuser" in written_content

    @patch("kairix_cli.commands.users.console")
    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    def test_update_caddy_config_no_base_file(
        self,
        mock_exists: MagicMock,
        mock_cwd: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test Caddy config update when base file missing."""
        mock_cwd.return_value = Path("/Users/mark/kairix/kairix-cli")
        mock_exists.return_value = False

        result = update_caddy_config({})

        assert result is False
        mock_console.print.assert_any_call("[red]Error: Base Caddyfile not found")

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.console")
    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open", new_callable=mock_open, read_data="invalid config without marker")
    def test_update_caddy_config_invalid_format(
        self,
        mock_file: MagicMock,
        mock_exists: MagicMock,
        mock_cwd: MagicMock,
        mock_console: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Test Caddy config update with invalid format."""
        mock_cwd.return_value = Path("/Users/mark/kairix/kairix-cli")
        mock_exists.return_value = True

        result = update_caddy_config({})

        assert result is False
        mock_console.print.assert_any_call("[red]Error: Caddyfile format not recognized")


class TestUserCommands:
    """Tests for user CLI commands."""

    @patch("kairix_cli.commands.users.update_caddy_config")
    @patch("kairix_cli.commands.users.save_users")
    @patch("kairix_cli.commands.users.create_systemd_service")
    @patch("kairix_cli.commands.users.create_user_directories")
    @patch("kairix_cli.commands.users.load_users")
    @patch("kairix_cli.commands.users.generate_subdomain")
    def test_create_user_success(
        self,
        mock_gen_subdomain: MagicMock,
        mock_load: MagicMock,
        mock_create_dirs: MagicMock,
        mock_create_service: MagicMock,
        mock_save: MagicMock,
        mock_update_caddy: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test successful user creation."""
        mock_gen_subdomain.return_value = "xyz"
        mock_load.return_value = {}
        mock_create_dirs.return_value = True
        mock_create_service.return_value = True
        mock_save.return_value = True
        mock_update_caddy.return_value = True

        result = cli_runner.invoke(
            users,
            ["create", "newuser"],
            input="password123\npassword123\n",
        )

        assert result.exit_code == 0
        assert "User 'newuser' created successfully" in result.output
        # Domain-agnostic check
        assert "Subdomain: xyz." in result.output

    @patch("kairix_cli.commands.users.load_users")
    def test_create_user_already_exists(
        self,
        mock_load: MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test creating user that already exists."""
        mock_load.return_value = {"existinguser": sample_user}

        result = cli_runner.invoke(
            users,
            ["create", "existinguser"],
            input="password123\npassword123\n",
        )

        assert result.exit_code == 0
        assert "User 'existinguser' already exists" in result.output

    @patch("kairix_cli.commands.users.load_users")
    def test_create_user_invalid_subdomain(
        self,
        mock_load: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test creating user with invalid subdomain."""
        mock_load.return_value = {}

        result = cli_runner.invoke(
            users,
            ["create", "newuser", "--subdomain", "invalid-subdomain"],
            input="password123\npassword123\n",
        )

        assert result.exit_code == 0
        assert "Subdomain must be exactly 3 alphanumeric characters" in result.output

    @patch("kairix_cli.commands.users.load_users")
    def test_list_users_empty(
        self,
        mock_load: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test listing users when none exist."""
        mock_load.return_value = {}

        result = cli_runner.invoke(users, ["list"])

        assert result.exit_code == 0
        assert "No users found" in result.output

    @patch("kairix_cli.commands.users.load_users")
    def test_list_users_with_data(
        self,
        mock_load: MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test listing users with data."""
        mock_load.return_value = {"testuser": sample_user}

        result = cli_runner.invoke(users, ["list"])

        assert result.exit_code == 0
        assert "testuser" in result.output
        assert "abc.kairix.net" in result.output
        assert "6010" in result.output

    @patch("kairix_cli.commands.users.update_caddy_config")
    @patch("kairix_cli.commands.users.save_users")
    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.load_users")
    def test_delete_user_success(
        self,
        mock_load: MagicMock,
        mock_run: MagicMock,
        mock_save: MagicMock,
        mock_update_caddy: MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test successful user deletion."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.return_value = (True, "", "")
        mock_save.return_value = True
        mock_update_caddy.return_value = True

        result = cli_runner.invoke(users, ["delete", "testuser"], input="y\n")

        assert result.exit_code == 0
        assert "User 'testuser' deleted successfully" in result.output

    @patch("kairix_cli.commands.users.load_users")
    def test_delete_user_not_found(
        self,
        mock_load: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test deleting non-existent user."""
        mock_load.return_value = {}

        result = cli_runner.invoke(users, ["delete", "nonexistent"], input="y\n")

        assert result.exit_code == 0
        assert "User 'nonexistent' not found" in result.output

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.load_users")
    def test_start_user_services(
        self,
        mock_load: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test starting user services."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.return_value = (True, "", "")

        result = cli_runner.invoke(users, ["start", "testuser"])

        assert result.exit_code == 0
        assert "Started kairix-testuser-server" in result.output
        assert "Started kairix-testuser-website" in result.output

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.load_users")
    def test_stop_user_services(
        self,
        mock_load: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test stopping user services."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.return_value = (True, "", "")

        result = cli_runner.invoke(users, ["stop", "testuser"])

        assert result.exit_code == 0
        assert "Stopped kairix-testuser-server" in result.output
        assert "Stopped kairix-testuser-website" in result.output

    @patch("kairix_cli.commands.users.run_command")
    @patch("kairix_cli.commands.users.load_users")
    def test_user_status(
        self,
        mock_load: MagicMock,
        mock_run: MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test user status command."""
        mock_load.return_value = {"testuser": sample_user}
        mock_run.side_effect = [
            (True, "active", ""),
            (True, "inactive", ""),
        ]

        result = cli_runner.invoke(users, ["status", "testuser"])

        assert result.exit_code == 0
        assert "Status for user 'testuser'" in result.output
        assert "Subdomain: abc.kairix.net" in result.output
        assert "kairix-testuser-server: active" in result.output
        assert "kairix-testuser-website: inactive" in result.output

    @patch("kairix_cli.commands.users.update_caddy_config")
    @patch("kairix_cli.commands.users.save_users")
    @patch("kairix_cli.commands.users.load_users")
    def test_toggle_user(
        self,
        mock_load: MagicMock,
        mock_save: MagicMock,
        mock_update_caddy: MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test toggling user enabled status."""
        mock_load.return_value = {"testuser": sample_user}
        mock_save.return_value = True
        mock_update_caddy.return_value = True

        # Test disabling
        result = cli_runner.invoke(users, ["toggle", "testuser", "--disable"])
        assert result.exit_code == 0
        assert "User 'testuser' disabled" in result.output

        # Test enabling
        result = cli_runner.invoke(users, ["toggle", "testuser", "--enable"])
        assert result.exit_code == 0
        assert "User 'testuser' enabled" in result.output
