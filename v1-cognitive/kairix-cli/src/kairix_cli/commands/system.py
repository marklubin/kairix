"""System management commands for Kairix."""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress

from kairix_cli.utils.shell import run_command, run_commands_parallel

console = Console()


@click.group()
def system() -> None:
    """Manage Kairix system infrastructure."""
    pass


def check_root_access() -> bool:
    """Check if the user has root access."""
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True, check=False)
        return result.returncode == 0
    except Exception:
        return False


def create_system_user() -> bool:
    """Create the kairix system user."""
    console.print("[bold blue]Creating system user 'kairix'...")

    # Check if user already exists
    success, _, _ = run_command("id kairix")
    if success:
        console.print("[green]✓ System user 'kairix' already exists")
        # Still ensure directories exist with correct permissions
        commands = [
            "sudo mkdir -p /home/kairix",
            "sudo chown -R kairix:kairix /home/kairix",
            "sudo mkdir -p /var/kairix",
            "sudo chown -R kairix:kairix /var/kairix",
        ]
        for cmd in commands:
            run_command(cmd)
        return True

    commands = [
        "sudo useradd -m -s /usr/sbin/nologin kairix",
        "sudo mkdir -p /home/kairix",
        "sudo chown -R kairix:kairix /home/kairix",
        "sudo mkdir -p /var/kairix",
        "sudo chown -R kairix:kairix /var/kairix",
    ]

    for cmd in commands:
        success, stdout, stderr = run_command(cmd)
        if not success and "already exists" not in stderr:
            return False
    return True


def install_uv() -> bool:
    """Install the uv package manager."""
    console.print("[bold blue]Installing uv package manager...")
    # First check if uv is already installed
    success, _, _ = run_command("which uv")
    if success:
        console.print("[green]✓ uv is already installed")
        return True

    cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"
    return run_command(cmd, shell=True)[0]


def install_just() -> bool:
    """Install just command runner."""
    console.print("[bold blue]Installing just command runner...")
    # First check if just is already installed
    success, _, _ = run_command("which just")
    if success:
        console.print("[green]✓ just is already installed")
        return True

    cmd = "curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | sudo bash -s -- --to /usr/local/bin"
    return run_command(cmd, shell=True)[0]


def install_caddy() -> bool:
    """Install Caddy web server."""
    console.print("[bold blue]Installing Caddy web server...")
    # First check if caddy is already installed
    success, _, _ = run_command("which caddy")
    if success:
        console.print("[green]✓ caddy is already installed")
        return True

    commands = [
        "sudo apt update && sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl",
        "curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg",
        "curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list",
        "sudo apt update && sudo apt install -y caddy",
    ]

    for cmd in commands:
        success, _, _ = run_command(cmd, shell=True)
        if not success:
            return False
    return True


def install_doppler() -> bool:
    """Install Doppler CLI."""
    console.print("[bold blue]Installing Doppler CLI...")
    # First check if doppler is already installed
    success, _, _ = run_command("which doppler")
    if success:
        console.print("[green]✓ doppler is already installed")
        return True

    cmd = "curl -Ls --tlsv1.2 --proto '=https' --retry 3 https://cli.doppler.com/install.sh | sudo sh"
    success, _, _ = run_command(cmd, shell=True)
    if success:
        console.print("[yellow]Please run 'doppler login' to authenticate")
    return success


def install_magg() -> bool:
    """Install MCP Aggregator."""
    console.print("[bold blue]Installing MCP Aggregator (magg)...")
    # First check if magg is already installed
    success, _, _ = run_command("which magg")
    if success:
        console.print("[green]✓ magg is already installed")
        # Still ensure config directory exists
        run_command("mkdir -p ~/.config/magg", shell=True)
        if not Path("~/.config/magg/config.json").expanduser().exists():
            run_command("echo '{}' > ~/.config/magg/config.json", shell=True)
        return True

    # Check if cargo is installed first
    cargo_check, _, _ = run_command("which cargo")
    if not cargo_check:
        console.print("[red]Error: cargo is not installed. Please install Rust first.")
        return False

    commands = [
        "cargo install magg",
        "mkdir -p ~/.config/magg",
        "echo '{}' > ~/.config/magg/config.json",
    ]

    for cmd in commands:
        success, _, _ = run_command(cmd, shell=True)
        if not success:
            return False
    return True


def install_sqlite_vss() -> bool:
    """Install SQLite VSS extension."""
    console.print("[bold blue]Installing SQLite VSS extension...")
    commands = [
        "mkdir -p ~/.local/lib",
        "curl -L https://github.com/asg017/sqlite-vss/releases/latest/download/sqlite-vss-linux-x86_64.zip -o /tmp/sqlite-vss.zip",
        "unzip -o /tmp/sqlite-vss.zip -d ~/.local/lib/",
        "rm -f /tmp/sqlite-vss.zip",
    ]

    for cmd in commands:
        success, _, _ = run_command(cmd, shell=True)
        if not success:
            return False

    # Add to bashrc if not already present
    bashrc_path = Path.home() / ".bashrc"
    export_line = "export LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH"

    if bashrc_path.exists():
        content = bashrc_path.read_text()
        if export_line not in content:
            with bashrc_path.open("a") as f:
                f.write(f"\n{export_line}\n")
            console.print("[yellow]Added LD_LIBRARY_PATH to ~/.bashrc. Please restart your shell or run: source ~/.bashrc")

    return True


def setup_caddy_config() -> bool:
    """Set up Caddy configuration."""
    console.print("[bold blue]Setting up Caddy configuration...")
    kairix_root = Path.cwd().parent  # Assuming we're running from kairix-cli
    caddyfile_src = kairix_root / "Caddyfile"

    if not caddyfile_src.exists():
        console.print(f"[red]Error: Caddyfile not found at {caddyfile_src}")
        return False

    cmd = f"sudo cp {caddyfile_src} /etc/caddy/Caddyfile && sudo systemctl reload caddy"
    return run_command(cmd, shell=True)[0]


def setup_systemd_services() -> bool:
    """Set up shared systemd services (magg, caddy)."""
    console.print("[bold blue]Setting up shared systemd services...")

    # Create magg service if it doesn't exist
    magg_service = Path("/etc/systemd/system/magg.service")
    if not magg_service.exists():
        magg_content = """[Unit]
Description=MCP Aggregator Service
After=network.target

[Service]
Type=simple
User=kairix
ExecStart=/home/kairix/.cargo/bin/magg
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        success, _, _ = run_command(f"echo '{magg_content}' | sudo tee {magg_service}", shell=True)
        if not success:
            console.print("[red]Failed to create magg service")
            return False

    # Enable services
    commands = [
        "sudo systemctl daemon-reload",
        "sudo systemctl enable magg",
        "sudo systemctl enable caddy",
    ]

    for cmd in commands:
        success, _, _ = run_command(cmd)
        if not success:
            console.print(f"[yellow]Warning: Command failed: {cmd}")
            return False

    console.print("[green]✓ Shared services configured")
    return True


@system.command()
@click.option("--skip-checks", is_flag=True, help="Skip preliminary checks")
def provision(skip_checks: bool) -> None:
    """Provision a new host for Kairix."""
    console.print("[bold green]Starting Kairix system provisioning...")

    if not skip_checks and not check_root_access():
        console.print("[red]Error: This command requires sudo access. Please run with appropriate privileges.")
        sys.exit(1)

    steps = [
        ("Installing dependencies", install_uv),
        ("Installing just", install_just),
        ("Installing Caddy", install_caddy),
        ("Installing Doppler", install_doppler),
        ("Installing MCP Aggregator", install_magg),
        ("Installing SQLite VSS", install_sqlite_vss),
        ("Creating system user", create_system_user),
        ("Setting up Caddy", setup_caddy_config),
        ("Setting up services", setup_systemd_services),
    ]

    failed_steps = []

    with Progress() as progress:
        task = progress.add_task("[cyan]Provisioning system...", total=len(steps))

        for step_name, step_func in steps:
            progress.update(task, description=f"[cyan]{step_name}...")

            try:
                if step_func():
                    console.print(f"[green]✓ {step_name}")
                else:
                    console.print(f"[red]✗ {step_name}")
                    failed_steps.append(step_name)
            except Exception as e:
                console.print(f"[red]✗ {step_name}: {e}")
                failed_steps.append(step_name)

            progress.advance(task)

    if failed_steps:
        console.print("\n[red]Provisioning completed with errors:")
        for step in failed_steps:
            console.print(f"  - {step}")
        console.print("\n[yellow]Please check the errors above and run provision again.")
    else:
        console.print("\n[bold green]✓ System provisioned successfully!")
        console.print("\n[yellow]Next steps:")
        console.print("1. Run 'doppler login' to authenticate with Doppler")
        console.print("2. Configure your environment variables")
        console.print("3. Run 'kairix system start' to start services")


@system.command()
def start() -> None:
    """Start shared Kairix services."""
    console.print("[bold blue]Starting shared Kairix services...")

    commands = [
        ("magg", "sudo systemctl start magg"),
        ("caddy", "sudo systemctl start caddy"),
    ]

    results = run_commands_parallel(commands)

    all_success = True
    for name, (success, _stdout, stderr) in results:
        if success:
            console.print(f"[green]✓ Started {name}")
        else:
            console.print(f"[red]✗ Failed to start {name}: {stderr}")
            all_success = False

    if all_success:
        console.print("\n[bold green]All shared services started successfully!")
        console.print("[yellow]Note: User-specific services are managed with 'kairix users start <username>'")
    else:
        console.print("\n[red]Some services failed to start. Check logs with 'kairix system status'")


@system.command()
def stop() -> None:
    """Stop shared Kairix services."""
    console.print("[bold blue]Stopping shared Kairix services...")

    commands = [
        ("magg", "sudo systemctl stop magg"),
        ("caddy", "sudo systemctl stop caddy"),
    ]

    results = run_commands_parallel(commands)

    for name, (success, _stdout, stderr) in results:
        if success:
            console.print(f"[green]✓ Stopped {name}")
        else:
            console.print(f"[yellow]⚠ {name}: {stderr}")


@system.command()
def status() -> None:
    """Check status of shared Kairix services."""
    console.print("[bold blue]Checking shared Kairix services status...\n")

    services = ["magg", "caddy"]

    for service in services:
        cmd = f"systemctl is-active {service}"
        success, stdout, _ = run_command(cmd)

        if stdout.strip() == "active":
            console.print(f"[green]● {service}: active")
        elif stdout.strip() == "inactive":
            console.print(f"[yellow]● {service}: inactive")
        else:
            console.print(f"[red]● {service}: {stdout.strip()}")

    console.print("\n[dim]Use 'systemctl status <service>' for detailed information")


@system.command()
@click.option("--service", type=click.Choice(["magg", "caddy", "all"]), default="all")
@click.option("--lines", "-n", default=50, help="Number of log lines to show")
def logs(service: str, lines: int) -> None:
    """View logs for shared Kairix services."""
    console.print(f"[bold blue]Viewing last {lines} lines of shared service logs...")

    services = ["magg", "caddy"] if service == "all" else [service]

    for svc in services:
        console.print(f"\n[bold blue]Logs for {svc}:")
        cmd = f"sudo journalctl -u {svc} -n {lines} --no-pager"
        success, stdout, stderr = run_command(cmd)

        if success:
            console.print(stdout)
        else:
            console.print(f"[red]Failed to get logs: {stderr}")

    console.print("\n[yellow]Note: For user-specific logs, use 'kairix users logs <username>'")


@system.command()
def restart() -> None:
    """Restart shared Kairix services."""
    console.print("[bold blue]Restarting shared Kairix services...")

    commands = [
        ("magg", "sudo systemctl restart magg"),
        ("caddy", "sudo systemctl restart caddy"),
    ]

    results = run_commands_parallel(commands)

    all_success = True
    for name, (success, _stdout, stderr) in results:
        if success:
            console.print(f"[green]✓ Restarted {name}")
        else:
            console.print(f"[red]✗ Failed to restart {name}: {stderr}")
            all_success = False

    if all_success:
        console.print("\n[bold green]All shared services restarted successfully!")
    else:
        console.print("\n[red]Some services failed to restart. Check logs with 'kairix system logs'")
