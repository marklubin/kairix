#!/usr/bin/env python
"""Helper script to run tests with proper configuration."""

import subprocess
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "unit":
        # Run only unit tests
        print("Running unit tests...")
        subprocess.run(["uv", "run", "pytest", "-m", "unit", "-v"])
    elif len(sys.argv) > 1 and sys.argv[1] == "integration":
        # Run only integration tests
        print("Running integration tests (requires Docker)...")
        subprocess.run(["uv", "run", "pytest", "-m", "integration", "-v"])
    else:
        # Run all tests
        print("Running all tests (requires Docker for integration tests)...")
        subprocess.run(["uv", "run", "pytest", "-v"])
