#!/usr/bin/env python
"""Run unit tests only."""
import subprocess
import sys

if __name__ == "__main__":
    cmd = ["uv", "run", "pytest", "tests/unit", "-v", "-m", "unit"] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))
