"""Tests for the main CLI entry point."""

from click.testing import CliRunner

from kairix_cli.main import cli


def test_cli_help(cli_runner: CliRunner) -> None:
    """Test CLI help message."""
    result = cli_runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Kairix CLI - Manage Kairix system infrastructure and users." in result.output
    assert "system" in result.output
    assert "users" in result.output


def test_cli_version(cli_runner: CliRunner) -> None:
    """Test CLI version option."""
    result = cli_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output


def test_cli_no_args(cli_runner: CliRunner) -> None:
    """Test CLI with no arguments shows help."""
    result = cli_runner.invoke(cli, [])
    assert result.exit_code == 0 or result.exit_code == 2  # Click returns 2 for missing command
    assert "Usage:" in result.output


def test_cli_invalid_command(cli_runner: CliRunner) -> None:
    """Test CLI with invalid command."""
    result = cli_runner.invoke(cli, ["invalid"])
    assert result.exit_code != 0
    assert "Error" in result.output or "Usage" in result.output


def test_system_command_exists(cli_runner: CliRunner) -> None:
    """Test that system command exists."""
    result = cli_runner.invoke(cli, ["system", "--help"])
    assert result.exit_code == 0
    assert "Manage Kairix system infrastructure." in result.output


def test_users_command_exists(cli_runner: CliRunner) -> None:
    """Test that users command exists."""
    result = cli_runner.invoke(cli, ["users", "--help"])
    assert result.exit_code == 0
    assert "Manage Kairix users." in result.output
