#!/usr/bin/env python3
"""Kairix User Management CLI Tool."""

import random
import string
from pathlib import Path
import click
import bcrypt


def generate_subdomain(username: str) -> str:
    """Generate a 3-character subdomain from username."""
    # Try first 3 chars
    if len(username) >= 3:
        base = username[:3].lower()
        if base.isalnum():
            return base
    
    # Generate random 3-char subdomain
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=3))


def generate_password_hash(password: str) -> str:
    """Generate bcrypt hash for Caddy basic_auth."""
    # Caddy uses bcrypt with cost 14
    salt = bcrypt.gensalt(rounds=14)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def find_next_port_base() -> int:
    """Find the next available port base by reading Caddyfile."""
    caddyfile_path = Path.home() / "kairix" / "caddyfile"
    if not caddyfile_path.exists():
        return 6010  # Default starting point
    
    max_port = 6009
    with open(caddyfile_path, 'r') as f:
        content = f.read()
        # Look for all port numbers in the 6000 range
        import re
        ports = re.findall(r'localhost:(\d{4})', content)
        for port in ports:
            port_num = int(port)
            if 6000 <= port_num < 7000:
                max_port = max(max_port, port_num)
    
    # Return next available base (increment by 1)
    return max_port + 1


@click.group()
def cli():
    """Kairix infrastructure management tools."""
    pass


@cli.command()
@click.option('--username', prompt='Username', help='Username for the new user')
@click.option('--display-name', prompt='Display name (optional)', default='', help='Display name for the user')
@click.option('--subdomain', prompt='Subdomain (3 chars, or auto-generate)', default='', help='3-character subdomain')
@click.option('--port-base', type=int, help='Base port number (auto-detect if not specified)')
@click.option('--db-template', default='base_template.db', help='Path to template database')
@click.option('--password', prompt='Password', default='kairix', help='User password')
@click.option('--hash-password/--no-hash-password', default=True, help='Hash the password for Caddy')
def new_user(username, display_name, subdomain, port_base, db_template, password, hash_password):
    """Create configuration for a new Kairix user."""
    
    # Generate subdomain if not provided
    if not subdomain or len(subdomain) != 3:
        subdomain = generate_subdomain(username)
        click.secho(f"📝 Generated subdomain: {subdomain}", fg='yellow')
    
    # Auto-detect port base if not provided
    if port_base is None:
        port_base = find_next_port_base()
        click.secho(f"🔍 Auto-detected next port base: {port_base}", fg='cyan')
    
    # Validate port base
    if not (6000 <= port_base < 7000):
        click.secho("❌ Port base must be between 6000-6999", fg='red')
        return
    
    # Calculate service ports
    ui_port = port_base
    api_port = port_base + 1000  # 7xxx range
    tools_port = port_base + 2000  # 8xxx range
    
    # Hash password if requested
    if hash_password:
        password_hash = generate_password_hash(password)
    else:
        password_hash = password
    
    # Generate Caddyfile block
    caddy_config = f"""http://{subdomain}.kairix.net, {subdomain}.localhost {{
\tbasic_auth {{
\t\t{username} {password_hash}
\t}}

\thandle_path / {{
\t\treverse_proxy localhost:{ui_port}
\t}}

\thandle_path /api/* {{
\t\treverse_proxy localhost:{api_port}
\t}}

\thandle_path /tools/* {{
\t\treverse_proxy localhost:{tools_port}
\t}}
}}"""
    
    # Display results
    click.echo()
    click.secho("✅ Caddy config for {}.kairix.net generated.".format(subdomain), fg='green', bold=True)
    click.secho("➡️  Add the following block to your Caddyfile:", fg='yellow')
    click.echo("-" * 50)
    click.echo(caddy_config)
    click.echo("-" * 50)
    
    # Database command
    click.echo()
    click.secho("📁 Suggested DB command:", fg='blue')
    db_path = f"/data/dbs/{username}.db"
    click.echo(f"cp {db_template} {db_path}")
    
    # Environment setup
    click.echo()
    click.secho("🧠 Run:", fg='blue')
    click.echo(f"just set-env {username}")
    
    # Test command
    click.echo()
    click.secho("🧪 Test:", fg='magenta')
    click.echo(f"curl -u {username}:{password} https://{subdomain}.kairix.net:2727/api/status")
    
    # Final steps
    click.echo()
    click.secho("🧼 Final Step:", fg='yellow')
    click.echo("Run 'caddy reload --config ./Caddyfile --adapter caddyfile' to apply changes")
    
    # Checklist
    click.echo()
    click.secho("📋 Checklist:", fg='cyan', bold=True)
    click.secho("  ✅ Config generated", fg='green')
    click.secho("  ❗ Add config to Caddyfile", fg='yellow')
    click.secho("  ❗ Copy database template", fg='yellow')
    click.secho("  ❗ Set up user environment", fg='yellow')
    click.secho("  ❗ Start user services", fg='yellow')
    click.secho("  ❗ Reload Caddy", fg='yellow')
    click.secho("  🧪 Test the new instance", fg='magenta')
    
    # Summary for copy-paste
    click.echo()
    click.secho("📄 Summary for documentation:", fg='blue')
    click.echo(f"User: {username}")
    if display_name:
        click.echo(f"Display Name: {display_name}")
    click.echo(f"Subdomain: {subdomain}")
    click.echo(f"Ports: UI={ui_port}, API={api_port}, Tools={tools_port}")


@cli.command()
def list_users():
    """List all configured users from Caddyfile."""
    from sre_agent.caddyfile_parser import CaddyfileParser
    
    parser = CaddyfileParser()
    services = parser.parse_services()
    
    if not services:
        click.secho("No users found in Caddyfile", fg='yellow')
        return
    
    click.secho(f"Found {len(services)} users:", fg='green', bold=True)
    click.echo()
    
    # Create table
    click.echo("{:<15} {:<10} {:<10} {:<10} {:<10}".format(
        "Username", "Subdomain", "UI Port", "API Port", "Tools Port"
    ))
    click.echo("-" * 65)
    
    for service in services:
        username = service['username']
        subdomain = service['subdomain']
        ports = service['ports']
        
        click.echo("{:<15} {:<10} {:<10} {:<10} {:<10}".format(
            username,
            subdomain,
            ports.get('ui', 'N/A'),
            ports.get('api', 'N/A'),
            ports.get('tools', 'N/A')
        ))


@cli.command()
@click.argument('username')
def check_user(username):
    """Check if a user exists and show their configuration."""
    from sre_agent.caddyfile_parser import CaddyfileParser
    
    parser = CaddyfileParser()
    services = parser.parse_services()
    
    user_service = None
    for service in services:
        if service['username'] == username:
            user_service = service
            break
    
    if not user_service:
        click.secho(f"❌ User '{username}' not found in Caddyfile", fg='red')
        return
    
    click.secho(f"✅ User '{username}' configuration:", fg='green', bold=True)
    click.echo(f"  Subdomain: {user_service['subdomain']}.kairix.net")
    click.echo(f"  UI Port: {user_service['ports'].get('ui', 'N/A')}")
    click.echo(f"  API Port: {user_service['ports'].get('api', 'N/A')}")
    click.echo(f"  Tools Port: {user_service['ports'].get('tools', 'N/A')}")
    
    # Check service health
    click.echo()
    click.secho("🔍 Checking service status...", fg='yellow')
    
    import subprocess
    for service_type, port in user_service['ports'].items():
        try:
            result = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', f'http://localhost:{port}/'],
                capture_output=True,
                text=True,
                timeout=2
            )
            status_code = result.stdout.strip()
            if status_code == "200":
                click.secho(f"  ✅ {service_type.upper()}: Running (port {port})", fg='green')
            else:
                click.secho(f"  ❌ {service_type.upper()}: Not responding (port {port}, status: {status_code})", fg='red')
        except Exception:
            click.secho(f"  ❌ {service_type.upper()}: Down (port {port})", fg='red')


if __name__ == '__main__':
    cli()