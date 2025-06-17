#!/usr/bin/env python
"""Run integration tests for the talk.py audio pipeline."""

import subprocess
import sys


def run_smoke_tests():
    """Run quick smoke tests."""
    print("Running smoke tests...")
    result = subprocess.run(
        ["uv", "run", "pytest", "tests/integration/test_talk_smoke.py", "-v"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode


def run_full_integration_tests():
    """Run full integration tests."""
    print("\nRunning full integration tests...")
    result = subprocess.run(
        [
            "uv", "run", "pytest", 
            "tests/integration/test_talk_integration.py", 
            "-v", "-s"
        ],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode


def main():
    """Run integration tests."""
    print("ElevenLabs TTS Integration Tests")
    print("=" * 50)
    
    # Run smoke tests first
    smoke_result = run_smoke_tests()
    if smoke_result != 0:
        print("\n❌ Smoke tests failed! Check your API key and connection.")
        sys.exit(1)
    
    print("\n✅ Smoke tests passed!")
    
    # Ask if user wants to run full tests
    response = input("\nRun full integration tests? (y/n): ").lower()
    if response == "y":
        full_result = run_full_integration_tests()
        if full_result != 0:
            print("\n❌ Some integration tests failed.")
            sys.exit(1)
        print("\n✅ All integration tests passed!")
    else:
        print("Skipping full integration tests.")


if __name__ == "__main__":
    main()