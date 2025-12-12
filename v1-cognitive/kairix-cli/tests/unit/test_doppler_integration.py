"""Tests for Doppler integration in user management."""

from unittest import mock

import pytest

from kairix_cli.commands.users import create_doppler_config


class TestDopplerConfig:
    """Test Doppler configuration creation."""

    @mock.patch("kairix_cli.commands.users.run_command")
    @mock.patch("kairix_cli.commands.users.console")
    def test_create_doppler_config_already_exists(self, mock_console, mock_run):
        """Test creating Doppler config when it already exists."""
        # Config already exists
        mock_run.side_effect = [
            (True, '{"name": "user-testuser"}', ""),  # doppler configs get - exists
        ]

        result = create_doppler_config("testuser")

        assert result is True
        assert mock_run.call_count == 1
        mock_run.assert_called_with("doppler configs get user-testuser -p kairix --json")
        mock_console.print.assert_any_call("[green]✓ Doppler config 'user-testuser' already exists")

    @mock.patch("kairix_cli.commands.users.run_command")
    @mock.patch("kairix_cli.commands.users.console")
    def test_create_doppler_config_new_success(self, mock_console, mock_run):
        """Test creating new Doppler config successfully."""
        # Config doesn't exist, then clone succeeds, then set vars succeed
        mock_run.side_effect = [
            (False, "", "not found"),  # doppler configs get - doesn't exist
            (True, "", ""),  # doppler configs clone
            (True, "", ""),  # set KAIRIX_USER
            (True, "", ""),  # set KAIRIX_DB_PATH
        ]

        result = create_doppler_config("testuser")

        assert result is True
        assert mock_run.call_count == 4
        
        # Check clone command uses 'mark' as source
        mock_run.assert_any_call("doppler configs clone mark --name user-testuser -p kairix")
        
        # Check user-specific vars are set
        mock_run.assert_any_call("doppler secrets set KAIRIX_USER=testuser -c user-testuser -p kairix --silent")
        mock_run.assert_any_call("doppler secrets set KAIRIX_DB_PATH=/var/kairix/users/testuser/sqlite/kairix.db -c user-testuser -p kairix --silent")
        
        mock_console.print.assert_any_call("[green]✓ Doppler config 'user-testuser' created from 'mark' template")

    @mock.patch("kairix_cli.commands.users.run_command")
    @mock.patch("kairix_cli.commands.users.console")
    def test_create_doppler_config_clone_fails(self, mock_console, mock_run):
        """Test when Doppler clone fails."""
        mock_run.side_effect = [
            (False, "", "not found"),  # doppler configs get - doesn't exist
            (False, "", "permission denied"),  # doppler configs clone fails
        ]

        result = create_doppler_config("testuser")

        assert result is False
        assert mock_run.call_count == 2
        mock_console.print.assert_any_call("[red]Failed to clone Doppler config: permission denied")

    @mock.patch("kairix_cli.commands.users.run_command")
    @mock.patch("kairix_cli.commands.users.console")
    def test_create_doppler_config_set_vars_fails(self, mock_console, mock_run):
        """Test when setting user variables fails."""
        mock_run.side_effect = [
            (False, "", "not found"),  # doppler configs get - doesn't exist
            (True, "", ""),  # doppler configs clone succeeds
            (False, "", ""),  # set KAIRIX_USER fails
            (True, "", ""),  # set KAIRIX_DB_PATH succeeds
        ]

        result = create_doppler_config("testuser")

        assert result is True  # Still returns True, just warns
        assert mock_run.call_count == 4
        mock_console.print.assert_any_call("[yellow]Warning: Failed to set KAIRIX_USER")

    @mock.patch("kairix_cli.commands.users.run_command")
    @mock.patch("kairix_cli.commands.users.console")
    def test_create_doppler_config_preserves_api_keys(self, mock_console, mock_run):
        """Test that API keys are preserved from mark template."""
        # This test verifies the clone command uses 'mark' as source
        # which should contain all API keys (11 Labs, OpenAI, etc.)
        mock_run.side_effect = [
            (False, "", "not found"),  # doppler configs get - doesn't exist
            (True, "", ""),  # doppler configs clone
            (True, "", ""),  # set KAIRIX_USER
            (True, "", ""),  # set KAIRIX_DB_PATH
        ]

        result = create_doppler_config("newuser")

        assert result is True
        # Verify it clones from 'mark' environment which has the API keys
        clone_call = mock_run.call_args_list[1][0][0]
        assert "doppler configs clone mark --name user-newuser -p kairix" == clone_call