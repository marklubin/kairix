"""Shell command execution utilities."""

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console

console = Console()


def run_command(
    command: str,
    shell: bool = False,
    capture_output: bool = True,
    timeout: int | None = 300,
) -> tuple[bool, str, str]:
    """
    Run a shell command and return success status, stdout, and stderr.

    Args:
        command: Command to run
        shell: Whether to run through shell
        capture_output: Whether to capture output
        timeout: Command timeout in seconds

    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        if shell:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False,
            )
        else:
            result = subprocess.run(
                command.split(),
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False,
            )

        return (
            result.returncode == 0,
            result.stdout if capture_output else "",
            result.stderr if capture_output else "",
        )
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return False, "", str(e)


def run_commands_parallel(
    commands: list[tuple[str, str]], max_workers: int = 5
) -> list[tuple[str, tuple[bool, str, str]]]:
    """
    Run multiple commands in parallel.

    Args:
        commands: List of (name, command) tuples
        max_workers: Maximum number of parallel workers

    Returns:
        List of (name, (success, stdout, stderr)) tuples
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_name = {
            executor.submit(run_command, cmd): name
            for name, cmd in commands
        }

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result = future.result()
                results.append((name, result))
            except Exception as e:
                results.append((name, (False, "", str(e))))

    return results


def check_command_exists(command: str) -> bool:
    """Check if a command exists in the system PATH."""
    success, _, _ = run_command(f"which {command}")
    return success


def get_system_info() -> dict[str, str]:
    """Get basic system information."""
    info = {}

    # OS information
    success, stdout, _ = run_command("uname -a")
    if success:
        info["system"] = stdout.strip()

    # Distribution information (for Linux)
    success, stdout, _ = run_command("lsb_release -a", capture_output=True)
    if success:
        for line in stdout.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip().lower()] = value.strip()

    return info
