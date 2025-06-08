#!/usr/bin/env python3
"""Fix auto-fixable issues with ruff across the workspace."""
import subprocess
import sys
from pathlib import Path

def run_command(cmd: list[str], cwd: Path = Path.cwd()) -> int:
    """Run a command and return exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode

def main() -> int:
    """Run ruff fix and format across workspace."""
    workspace_root = Path(__file__).parent.parent
    packages = ["kairix-core", "kairix-offline", "kairix-server"]
    
    # Track if any command failed
    exit_code = 0
    
    # Run ruff check with fix
    print("\n🔧 Running ruff check --fix...")
    for package in packages:
        src_path = workspace_root / package / "src"
        if src_path.exists():
            code = run_command(["uv", "run", "ruff", "check", "--fix", str(src_path)])
            if code != 0:
                exit_code = code
    
    # Run ruff format
    print("\n✨ Running ruff format...")
    for package in packages:
        src_path = workspace_root / package / "src"
        if src_path.exists():
            code = run_command(["uv", "run", "ruff", "format", str(src_path)])
            if code != 0:
                exit_code = code
    
    if exit_code == 0:
        print("\n✅ All fixes applied!")
    else:
        print(f"\n❌ Some fixes failed (exit code: {exit_code})")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())