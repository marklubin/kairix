"""Tests for users commands with domain configuration."""

import os
from unittest import mock

import pytest
from click.testing import CliRunner

from kairix_cli.commands.users import users
from kairix_cli.models.user import User


class TestUsersWithDomainConfig:
    """Test users commands with different domain configurations."""

    @pytest.fixture
    def sample_user(self) -> User:
        """Create a sample user."""
        return User(
            subdomain="abc",
            password_hash="hashed_password",
            web_port=6010,
            api_port=6011,
            tools_port=6012,
            enabled=True,
        )

    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch("kairix_cli.commands.users.save_users")
    @mock.patch("kairix_cli.commands.users.update_caddy_config")
    @mock.patch.dict(os.environ, {"KAIRIX_DOMAIN": "dev.example.com"})
    def test_list_users_with_custom_domain(
        self,
        mock_update_caddy: mock.MagicMock,
        mock_save: mock.MagicMock,
        mock_load: mock.MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test listing users with custom domain."""
        mock_load.return_value = {"testuser": sample_user}

        result = cli_runner.invoke(users, ["list"])

        assert result.exit_code == 0
        assert "abc.dev.example.com" in result.output
        assert "kairix.net" not in result.output

    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch("kairix_cli.commands.users.generate_subdomain")
    @mock.patch("kairix_cli.commands.users.create_user_directories")
    @mock.patch("kairix_cli.commands.users.create_systemd_service")
    @mock.patch("kairix_cli.commands.users.save_users")
    @mock.patch("kairix_cli.commands.users.update_caddy_config")
    @mock.patch.dict(os.environ, {"KAIRIX_DOMAIN": "localhost"})
    def test_create_user_with_localhost_domain(
        self,
        mock_update_caddy: mock.MagicMock,
        mock_save: mock.MagicMock,
        mock_create_service: mock.MagicMock,
        mock_create_dirs: mock.MagicMock,
        mock_generate: mock.MagicMock,
        mock_load: mock.MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test creating user with localhost domain."""
        mock_load.return_value = {}
        mock_generate.return_value = "xyz"
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
        assert "Subdomain: xyz.localhost" in result.output

    @mock.patch("kairix_cli.commands.users.Path.cwd")
    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch("kairix_cli.commands.users.run_command")
    @mock.patch.dict(os.environ, {"KAIRIX_DOMAIN": "test.domain.io"})
    def test_update_caddy_config_with_custom_domain(
        self,
        mock_run: mock.MagicMock,
        mock_load: mock.MagicMock,
        mock_cwd: mock.MagicMock,
        sample_user: User,
    ) -> None:
        """Test updating Caddy config with custom domain."""
        # Create a temporary directory structure
        import tempfile

        from kairix_cli.commands.users import update_caddy_config
        with tempfile.TemporaryDirectory() as tmpdir:
            from pathlib import Path

            # Create directory structure
            kairix_root = Path(tmpdir) / "kairix"
            kairix_root.mkdir()
            cli_dir = kairix_root / "kairix-cli" / "src"
            cli_dir.mkdir(parents=True)

            # Create base Caddyfile
            base_caddyfile = kairix_root / "Caddyfile"
            base_caddyfile.write_text("# Base Caddyfile\n\n# Wildcard catch-all for unmapped subdomains\n*.kairix.net {\n}\n")

            # User Caddyfile would be created at kairix_root / "Caddyfile.users"

            # Mock cwd to return our temp structure
            mock_cwd.return_value = cli_dir

            mock_run.return_value = (True, "", "")

            result = update_caddy_config({"testuser": sample_user})

            assert result is True

            # Check that caddy commands were called with correct config
            mock_run.assert_any_call("caddy validate --config /tmp/Caddyfile.new")

            # We can check the temp file was written by examining the Path calls
            # The update_caddy_config function should have succeeded

    @mock.patch("kairix_cli.commands.users.load_users")
    @mock.patch.dict(os.environ, {})  # No KAIRIX_DOMAIN set
    def test_user_status_with_default_domain(
        self,
        mock_load: mock.MagicMock,
        cli_runner: CliRunner,
        sample_user: User,
    ) -> None:
        """Test user status with default domain."""
        mock_load.return_value = {"testuser": sample_user}

        result = cli_runner.invoke(users, ["status", "testuser"])

        assert result.exit_code == 0
        assert "Subdomain: abc.kairix.net" in result.output
