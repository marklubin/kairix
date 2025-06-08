#!/usr/bin/env python3
"""Run all code quality checks (ruff + mypy) across the workspace."""
import subprocess
import sys
from pathlib import Path

def run_command(cmd: list[str], cwd: Path = Path.cwd()) -> int:
    """Run a command and return exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode

def main() -> int:
    """Run all checks and return combined exit code."""
    workspace_root = Path(__file__).parent.parent
    packages = ["kairix-core", "kairix-offline", "kairix-server"]
    
    # Track if any command failed
    exit_code = 0
    
    # Run ruff check
    print("\n🔍 Running ruff check...")
    for package in packages:
        src_path = workspace_root / package / "src"
        if src_path.exists():
            code = run_command(["uv", "run", "ruff", "check", str(src_path)])
            if code != 0:
                exit_code = code
    
    # Run ruff format check
    print("\n📐 Running ruff format check...")
    for package in packages:
        src_path = workspace_root / package / "src"
        if src_path.exists():
            code = run_command(["uv", "run", "ruff", "format", "--check", str(src_path)])
            if code != 0:
                exit_code = code
    
    # Run mypy
    print("\n🔎 Running mypy...")
    for package in packages:
        src_path = workspace_root / package / "src"
        if src_path.exists():
            code = run_command(["uv", "run", "mypy", str(src_path)])
            if code != 0:
                exit_code = code
    
    if exit_code == 0:
        print("\n✅ All checks passed!")
    else:
        print(f"\n❌ Some checks failed (exit code: {exit_code})")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())