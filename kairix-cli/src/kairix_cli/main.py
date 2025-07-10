"""Main entry point for the Kairix CLI."""

import click

from kairix_cli.commands.system import system
from kairix_cli.commands.users import users


@click.group()
@click.version_option()
def cli() -> None:
    """Kairix CLI - Manage Kairix system infrastructure and users."""
    pass


cli.add_command(system)
cli.add_command(users)


if __name__ == "__main__":
    cli()
