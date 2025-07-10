"""Tests for idempotent provisioning functionality."""

from unittest import mock

from kairix_cli.commands.system import (
    create_system_user,
    install_caddy,
    install_doppler,
    install_just,
    install_magg,
    install_uv,
)


class TestIdempotentProvisioning:
    """Test idempotent provisioning commands."""

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_create_system_user_already_exists(self, mock_run):
        """Test creating system user when it already exists."""
        # User exists check succeeds
        mock_run.side_effect = [
            (True, "", ""),  # id kairix - user exists
            (True, "", ""),  # mkdir -p /home/kairix
            (True, "", ""),  # chown -R kairix:kairix /home/kairix
            (True, "", ""),  # mkdir -p /var/kairix
            (True, "", ""),  # chown -R kairix:kairix /var/kairix
        ]

        result = create_system_user()
        assert result is True
        assert mock_run.call_count == 5
        # Verify it checked if user exists
        assert mock_run.call_args_list[0][0][0] == "id kairix"

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_create_system_user_new_user(self, mock_run):
        """Test creating system user when it doesn't exist."""
        # User doesn't exist, then creation succeeds
        mock_run.side_effect = [
            (False, "", "id: kairix: no such user"),  # id kairix - user doesn't exist
            (True, "", ""),  # useradd
            (True, "", ""),  # mkdir -p /home/kairix
            (True, "", ""),  # chown -R kairix:kairix /home/kairix
            (True, "", ""),  # mkdir -p /var/kairix
            (True, "", ""),  # chown -R kairix:kairix /var/kairix
        ]

        result = create_system_user()
        assert result is True
        assert mock_run.call_count == 6

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_install_uv_already_installed(self, mock_run):
        """Test installing uv when it's already installed."""
        mock_run.return_value = (True, "/usr/local/bin/uv", "")

        result = install_uv()
        assert result is True
        mock_run.assert_called_once_with("which uv")

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_install_uv_new_install(self, mock_run):
        """Test installing uv when it's not installed."""
        mock_run.side_effect = [
            (False, "", ""),  # which uv - not found
            (True, "", ""),   # curl install script
        ]

        result = install_uv()
        assert result is True
        assert mock_run.call_count == 2

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_install_just_already_installed(self, mock_run):
        """Test installing just when it's already installed."""
        mock_run.return_value = (True, "/usr/local/bin/just", "")

        result = install_just()
        assert result is True
        mock_run.assert_called_once_with("which just")

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_install_caddy_already_installed(self, mock_run):
        """Test installing caddy when it's already installed."""
        mock_run.return_value = (True, "/usr/bin/caddy", "")

        result = install_caddy()
        assert result is True
        mock_run.assert_called_once_with("which caddy")

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_install_caddy_new_install(self, mock_run):
        """Test installing caddy when it's not installed."""
        mock_run.side_effect = [
            (False, "", ""),  # which caddy - not found
            (True, "", ""),   # apt update & install deps
            (True, "", ""),   # add gpg key
            (True, "", ""),   # add repo
            (True, "", ""),   # apt update & install caddy
        ]

        result = install_caddy()
        assert result is True
        assert mock_run.call_count == 5

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_install_doppler_already_installed(self, mock_run):
        """Test installing doppler when it's already installed."""
        mock_run.return_value = (True, "/usr/local/bin/doppler", "")

        result = install_doppler()
        assert result is True
        mock_run.assert_called_once_with("which doppler")

    @mock.patch("kairix_cli.commands.system.run_command")
    @mock.patch("pathlib.Path.exists")
    def test_install_magg_already_installed(self, mock_exists, mock_run):
        """Test installing magg when it's already installed."""
        mock_exists.return_value = True  # config.json exists
        mock_run.side_effect = [
            (True, "/usr/local/bin/magg", ""),  # which magg - found
            (True, "", ""),  # mkdir -p ~/.config/magg
        ]

        result = install_magg()
        assert result is True
        assert mock_run.call_count == 2

    @mock.patch("kairix_cli.commands.system.run_command")
    @mock.patch("pathlib.Path.exists")
    def test_install_magg_already_installed_no_config(self, mock_exists, mock_run):
        """Test installing magg when it's installed but config missing."""
        mock_exists.return_value = False  # config.json doesn't exist
        mock_run.side_effect = [
            (True, "/usr/local/bin/magg", ""),  # which magg - found
            (True, "", ""),  # mkdir -p ~/.config/magg
            (True, "", ""),  # echo '{}' > config.json
        ]

        result = install_magg()
        assert result is True
        assert mock_run.call_count == 3

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_install_magg_new_install_no_cargo(self, mock_run):
        """Test installing magg when cargo is not installed."""
        mock_run.side_effect = [
            (False, "", ""),  # which magg - not found
            (False, "", ""),  # which cargo - not found
        ]

        result = install_magg()
        assert result is False
        assert mock_run.call_count == 2

    @mock.patch("kairix_cli.commands.system.run_command")
    def test_install_magg_new_install_with_cargo(self, mock_run):
        """Test installing magg when cargo is installed."""
        mock_run.side_effect = [
            (False, "", ""),  # which magg - not found
            (True, "/usr/local/bin/cargo", ""),  # which cargo - found
            (True, "", ""),   # cargo install magg
            (True, "", ""),   # mkdir -p ~/.config/magg
            (True, "", ""),   # echo '{}' > config.json
        ]

        result = install_magg()
        assert result is True
        assert mock_run.call_count == 5
