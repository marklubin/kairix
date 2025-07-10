"""User management commands for Kairix."""

import json
import os
import random
import string
from pathlib import Path

import bcrypt
import click
from rich.console import Console
from rich.table import Table

from kairix_cli.models.user import User
from kairix_cli.utils.shell import run_command

console = Console()


def get_kairix_domain() -> str:
    """Get the Kairix domain from environment or default."""
    domain = os.environ.get("KAIRIX_DOMAIN", "kairix.net")
    return domain if domain else "kairix.net"


def generate_subdomain() -> str:
    """Generate a random 3-character subdomain."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=3))


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(14)).decode("utf-8")


def get_user_config_path() -> Path:
    """Get the path to the users configuration file."""
    config_dir = Path.home() / ".config" / "kairix"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "users.json"


def load_users() -> dict[str, User]:
    """Load users from configuration file."""
    config_path = get_user_config_path()
    if not config_path.exists():
        return {}

    try:
        with config_path.open("r") as f:
            data = json.load(f)
            return {
                username: User(**user_data)
                for username, user_data in data.items()
            }
    except Exception as e:
        console.print(f"[red]Error loading users: {e}")
        return {}


def save_users(users: dict[str, User]) -> bool:
    """Save users to configuration file."""
    config_path = get_user_config_path()
    try:
        data = {
            username: user.model_dump()
            for username, user in users.items()
        }
        with config_path.open("w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        console.print(f"[red]Error saving users: {e}")
        return False


def get_next_port_set(users: dict[str, User]) -> tuple[int, int, int]:
    """Get the next available port set for a new user."""
    if not users:
        return 6010, 7010, 8010

    max_web_port = max(user.web_port for user in users.values())
    base_index = (max_web_port - 6010) + 1

    return 6010 + base_index, 7010 + base_index, 8010 + base_index


def create_user_directories(username: str) -> bool:
    """Create user-specific directories."""
    user_dir = Path(f"/var/kairix/users/{username}")
    sqlite_dir = user_dir / "sqlite"

    commands = [
        f"sudo mkdir -p {user_dir}",
        f"sudo mkdir -p {sqlite_dir}",
        f"sudo chown -R kairix:kairix {user_dir}",
    ]

    for cmd in commands:
        success, _, stderr = run_command(cmd)
        if not success:
            console.print(f"[red]Error creating directories: {stderr}")
            return False

    return True


def update_caddy_config(users: dict[str, User]) -> bool:
    """Update Caddy configuration with user subdomains."""
    console.print("[bold blue]Updating Caddy configuration...")

    # Read the base Caddyfile
    kairix_root = Path.cwd().parent.parent  # Go up to kairix root
    base_caddyfile = kairix_root / "Caddyfile"

    if not base_caddyfile.exists():
        console.print("[red]Error: Base Caddyfile not found")
        return False

    # Read base config
    with base_caddyfile.open("r") as f:
        base_config = f.read()

    # Find the marker for user configs (before the wildcard catch-all)
    marker = "# Wildcard catch-all for unmapped subdomains"
    if marker not in base_config:
        console.print("[red]Error: Caddyfile format not recognized")
        return False

    base_part, wildcard_part = base_config.split(marker, 1)

    # Generate user configurations
    user_configs = []
    for username, user in users.items():
        if user.enabled:
            config = f"""
{user.subdomain}.{get_kairix_domain()} {{
	basic_auth {{
		{username} {user.password_hash}
	}}

	handle_path / {{
		reverse_proxy localhost:{user.web_port}
	}}

	handle_path /api/* {{
		reverse_proxy localhost:{user.api_port}
	}}

	handle_path /tools/* {{
		reverse_proxy localhost:{user.tools_port}
	}}
}}"""
            user_configs.append(config)

    # Combine all parts
    new_config = base_part.rstrip() + "\n"
    if user_configs:
        new_config += "\n".join(user_configs) + "\n\n"
    new_config += marker + wildcard_part

    # Write to temporary file and copy
    temp_file = Path("/tmp/Caddyfile.new")
    with temp_file.open("w") as f:
        f.write(new_config)

    # Validate and apply
    success, _, stderr = run_command("caddy validate --config /tmp/Caddyfile.new")
    if not success:
        console.print(f"[red]Caddy config validation failed: {stderr}")
        return False

    success, _, stderr = run_command("sudo cp /tmp/Caddyfile.new /etc/caddy/Caddyfile")
    if not success:
        console.print(f"[red]Failed to update Caddyfile: {stderr}")
        return False

    # Reload Caddy
    success, _, stderr = run_command("sudo systemctl reload caddy")
    if not success:
        console.print(f"[red]Failed to reload Caddy: {stderr}")
        return False

    console.print("[green]✓ Caddy configuration updated")
    return True


def create_doppler_config(username: str) -> bool:
    """Create user-specific Doppler configuration from mark template."""
    console.print(f"[bold blue]Setting up Doppler config for user '{username}'...")
    
    # Check if config already exists
    check_cmd = f"doppler configs get user-{username} -p kairix --json"
    success, _, _ = run_command(check_cmd)
    if success:
        console.print(f"[green]✓ Doppler config 'user-{username}' already exists")
        return True

    # Clone from mark environment (the template with all API keys)
    cmd = f"doppler configs clone mark --name user-{username} -p kairix"
    success, _, stderr = run_command(cmd)
    if not success:
        console.print(f"[red]Failed to clone Doppler config: {stderr}")
        return False

    console.print(f"[green]✓ Doppler config 'user-{username}' created from 'mark' template")
    
    # Set user-specific environment variables
    user_vars = {
        "KAIRIX_USER": username,
        "KAIRIX_DB_PATH": f"/var/kairix/users/{username}/sqlite/kairix.db",
    }
    
    for key, value in user_vars.items():
        set_cmd = f"doppler secrets set {key}={value} -c user-{username} -p kairix --silent"
        success, _, _ = run_command(set_cmd)
        if not success:
            console.print(f"[yellow]Warning: Failed to set {key}")
    
    return True


def create_systemd_service(username: str, user: User) -> bool:
    """Create systemd service files for a user."""
    service_template = """[Unit]
Description=Kairix {service_type} for {username}
After=network.target

[Service]
Type=simple
User=kairix
WorkingDirectory=/home/kairix/kairix
Environment="KAIRIX_USER={username}"
Environment="KAIRIX_PORT={port}"
Environment="KAIRIX_DB_PATH=/var/kairix/users/{username}/sqlite/kairix.db"
ExecStart={exec_start}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    services = [
        {
            "name": f"kairix-{username}-server",
            "service_type": "API Server",
            "port": user.api_port,
            "exec_start": f"/usr/bin/doppler run -c user-{username} -p kairix -- uv run python -m kairix_apps.server",
        },
        {
            "name": f"kairix-{username}-website",
            "service_type": "Website",
            "port": user.web_port,
            "exec_start": f"/usr/bin/doppler run -c user-{username} -p kairix -- npm run serve",
        },
    ]

    for svc in services:
        content = service_template.format(
            username=username,
            **svc
        )

        service_file = f"/tmp/{svc['name']}.service"
        with open(service_file, "w") as f:
            f.write(content)

        cmd = f"sudo cp {service_file} /etc/systemd/system/{svc['name']}.service"
        success, _, stderr = run_command(cmd)
        if not success:
            console.print(f"[red]Failed to create service {svc['name']}: {stderr}")
            return False

    # Reload systemd
    run_command("sudo systemctl daemon-reload")

    # Enable services
    for svc in services:
        cmd = f"sudo systemctl enable {svc['name']}"
        run_command(cmd)

    return True


@click.group()
def users() -> None:
    """Manage Kairix users."""
    pass


@users.command()
@click.argument("username")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--subdomain", help="Custom subdomain (3 chars, auto-generated if not provided)")
def create(username: str, password: str, subdomain: str | None) -> None:
    """Create a new Kairix user."""
    console.print(f"[bold blue]Creating user '{username}'...")

    # Load existing users
    users_dict = load_users()

    # Check if user already exists
    if username in users_dict:
        console.print(f"[red]Error: User '{username}' already exists")
        return

    # Generate or validate subdomain
    if subdomain:
        if len(subdomain) != 3 or not subdomain.isalnum():
            console.print("[red]Error: Subdomain must be exactly 3 alphanumeric characters")
            return
        if any(user.subdomain == subdomain for user in users_dict.values()):
            console.print("[red]Error: Subdomain already in use")
            return
    else:
        # Generate unique subdomain
        while True:
            subdomain = generate_subdomain()
            if not any(user.subdomain == subdomain for user in users_dict.values()):
                break

    # Get next available ports
    web_port, api_port, tools_port = get_next_port_set(users_dict)

    # Create user object
    user = User(
        subdomain=subdomain,
        password_hash=hash_password(password),
        web_port=web_port,
        api_port=api_port,
        tools_port=tools_port,
        enabled=True,
    )

    # Create user directories
    if not create_user_directories(username):
        console.print("[red]Failed to create user directories")
        return

    # Create Doppler config for user
    if not create_doppler_config(username):
        console.print("[red]Failed to create Doppler configuration")
        return

    # Create systemd services
    if not create_systemd_service(username, user):
        console.print("[red]Failed to create systemd services")
        return

    # Save user
    users_dict[username] = user
    if not save_users(users_dict):
        console.print("[red]Failed to save user configuration")
        return

    # Update Caddy configuration
    if not update_caddy_config(users_dict):
        console.print("[red]Failed to update Caddy configuration")
        return

    console.print(f"\n[bold green]✓ User '{username}' created successfully!")
    console.print("\n[bold]User Details:")
    console.print(f"  Username: {username}")
    console.print(f"  Subdomain: {subdomain}.{get_kairix_domain()}")
    console.print(f"  Web Port: {web_port}")
    console.print(f"  API Port: {api_port}")
    console.print(f"  Tools Port: {tools_port}")
    console.print(f"\n[yellow]Run 'kairix users start {username}' to start the user's services")


@users.command()
def list() -> None:
    """List all Kairix users."""
    users_dict = load_users()

    if not users_dict:
        console.print("[yellow]No users found")
        return

    table = Table(title="Kairix Users")
    table.add_column("Username", style="cyan")
    table.add_column("Subdomain", style="magenta")
    table.add_column("Web Port", justify="right")
    table.add_column("API Port", justify="right")
    table.add_column("Tools Port", justify="right")
    table.add_column("Status", style="green")

    for username, user in sorted(users_dict.items()):
        status = "Enabled" if user.enabled else "Disabled"
        table.add_row(
            username,
            f"{user.subdomain}.{get_kairix_domain()}",
            str(user.web_port),
            str(user.api_port),
            str(user.tools_port),
            status,
        )

    console.print(table)


@users.command()
@click.argument("username")
@click.confirmation_option(prompt="Are you sure you want to delete this user?")
def delete(username: str) -> None:
    """Delete a Kairix user."""
    console.print(f"[bold red]Deleting user '{username}'...")

    users_dict = load_users()

    if username not in users_dict:
        console.print(f"[red]Error: User '{username}' not found")
        return

    # Stop and disable services
    services = [f"kairix-{username}-server", f"kairix-{username}-website"]
    for service in services:
        run_command(f"sudo systemctl stop {service}")
        run_command(f"sudo systemctl disable {service}")
        run_command(f"sudo rm -f /etc/systemd/system/{service}.service")

    run_command("sudo systemctl daemon-reload")

    # Remove user directories
    user_dir = f"/var/kairix/users/{username}"
    success, _, stderr = run_command(f"sudo rm -rf {user_dir}")
    if not success:
        console.print(f"[yellow]Warning: Failed to remove user directory: {stderr}")

    # Remove from configuration
    del users_dict[username]
    save_users(users_dict)

    # Update Caddy configuration
    update_caddy_config(users_dict)

    console.print(f"[green]✓ User '{username}' deleted successfully")


@users.command()
@click.argument("username")
def start(username: str) -> None:
    """Start services for a user."""
    users_dict = load_users()

    if username not in users_dict:
        console.print(f"[red]Error: User '{username}' not found")
        return

    services = [f"kairix-{username}-server", f"kairix-{username}-website"]

    for service in services:
        success, _, stderr = run_command(f"sudo systemctl start {service}")
        if success:
            console.print(f"[green]✓ Started {service}")
        else:
            console.print(f"[red]✗ Failed to start {service}: {stderr}")


@users.command()
@click.argument("username")
def stop(username: str) -> None:
    """Stop services for a user."""
    users_dict = load_users()

    if username not in users_dict:
        console.print(f"[red]Error: User '{username}' not found")
        return

    services = [f"kairix-{username}-server", f"kairix-{username}-website"]

    for service in services:
        success, _, stderr = run_command(f"sudo systemctl stop {service}")
        if success:
            console.print(f"[green]✓ Stopped {service}")
        else:
            console.print(f"[yellow]⚠ {service}: {stderr}")


@users.command()
@click.argument("username")
def status(username: str) -> None:
    """Check status of a user's services."""
    users_dict = load_users()

    if username not in users_dict:
        console.print(f"[red]Error: User '{username}' not found")
        return

    user = users_dict[username]
    console.print(f"\n[bold]Status for user '{username}':")
    console.print(f"  Subdomain: {user.subdomain}.{get_kairix_domain()}")
    console.print(f"  Enabled: {user.enabled}")

    services = [f"kairix-{username}-server", f"kairix-{username}-website"]

    console.print("\n[bold]Services:")
    for service in services:
        cmd = f"systemctl is-active {service}"
        success, stdout, _ = run_command(cmd)

        status = stdout.strip()
        if status == "active":
            console.print(f"  [green]● {service}: active")
        elif status == "inactive":
            console.print(f"  [yellow]● {service}: inactive")
        else:
            console.print(f"  [red]● {service}: {status}")


@users.command()
@click.argument("username")
@click.option("--enable/--disable", default=True, help="Enable or disable the user")
def toggle(username: str, enable: bool) -> None:
    """Enable or disable a user."""
    users_dict = load_users()

    if username not in users_dict:
        console.print(f"[red]Error: User '{username}' not found")
        return

    users_dict[username].enabled = enable
    save_users(users_dict)
    update_caddy_config(users_dict)

    action = "enabled" if enable else "disabled"
    console.print(f"[green]✓ User '{username}' {action}")


@users.command()
@click.argument("username")
@click.option("--service", type=click.Choice(["server", "website", "all"]), default="all")
@click.option("-n", "--lines", default=50, help="Number of log lines to show")
def logs(username: str, service: str, lines: int) -> None:
    """View logs for a user's services."""
    users_dict = load_users()

    if username not in users_dict:
        console.print(f"[red]Error: User '{username}' not found")
        return

    console.print(f"[bold blue]Viewing last {lines} lines of logs for user '{username}'...")

    services = ["server", "website"] if service == "all" else [service]

    for svc in services:
        service_name = f"kairix-{username}-{svc}"
        console.print(f"\n[bold blue]Logs for {service_name}:")
        cmd = f"sudo journalctl -u {service_name} -n {lines} --no-pager"
        success, stdout, stderr = run_command(cmd)

        if success:
            console.print(stdout)
        else:
            console.print(f"[red]Error getting logs: {stderr}")


@users.command()
@click.argument("username")
def restart(username: str) -> None:
    """Restart services for a user."""
    users_dict = load_users()

    if username not in users_dict:
        console.print(f"[red]Error: User '{username}' not found")
        return

    console.print(f"[bold blue]Restarting services for user '{username}'...")

    services = [f"kairix-{username}-server", f"kairix-{username}-website"]

    all_success = True
    for service in services:
        cmd = f"sudo systemctl restart {service}"
        success, _, stderr = run_command(cmd)
        if success:
            console.print(f"[green]✓ Restarted {service}")
        else:
            console.print(f"[red]✗ Failed to restart {service}: {stderr}")
            all_success = False

    if all_success:
        console.print(f"\n[bold green]All services for user '{username}' restarted successfully!")
    else:
        console.print(f"\n[red]Some services failed to restart. Check logs with 'kairix users logs {username}'")


@users.command()
@click.argument("username")
@click.argument("key")
@click.argument("value")
def setenv(username: str, key: str, value: str) -> None:
    """Set environment variable for a user in Doppler."""
    users_dict = load_users()

    if username not in users_dict:
        console.print(f"[red]Error: User '{username}' not found")
        return

    console.print(f"[bold blue]Setting {key} for user '{username}'...")

    cmd = f"doppler secrets set {key}={value} -c user-{username} -p kairix --silent"
    success, _, stderr = run_command(cmd)

    if success:
        console.print(f"[green]✓ Set {key} for user '{username}'")
        console.print("[yellow]Note: Restart user services for changes to take effect")
    else:
        console.print(f"[red]Failed to set environment variable: {stderr}")


@users.command()
@click.argument("username")
def getenv(username: str) -> None:
    """Show environment variables for a user from Doppler."""
    users_dict = load_users()

    if username not in users_dict:
        console.print(f"[red]Error: User '{username}' not found")
        return

    console.print(f"[bold blue]Environment variables for user '{username}':")

    cmd = f"doppler secrets -c user-{username} -p kairix"
    success, stdout, stderr = run_command(cmd)

    if success:
        console.print(stdout)
    else:
        console.print(f"[red]Failed to get environment variables: {stderr}")
