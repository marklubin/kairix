#!/usr/bin/env python
"""Run integration tests only."""
import subprocess
import sys

if __name__ == "__main__":
    cmd = ["uv", "run", "pytest", "tests/integration", "-v", "-m", "integration"] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))