#!/usr/bin/env python
"""Run agent configuration tests across different environments."""

import os
import subprocess
import sys


def run_tests_for_env(env_name: str, test_file: str | None = None):
    """Run agent tests for a specific environment."""
    print(f"\n{'='*60}")
    print(f"Testing environment: {env_name}")
    print(f"{'='*60}")
    
    # Check if env file exists
    env_path = f"env/{env_name}.env"
    if not os.path.exists(env_path):
        print(f"❌ Environment file not found: {env_path}")
        return False
    
    # Prepare test command
    if test_file:
        test_path = test_file
    else:
        test_path = (
            "tests/integration/test_chat_configurations.py::"
            "TestChatConfigurations::test_environment_info"
        )
    
    cmd = [
        "uv", "run", "pytest",
        test_path,
        "-v", "-s",
        "--tb=short"
    ]
    
    # Run tests with environment
    env = os.environ.copy()
    env["ENV"] = env_name
    
    result = subprocess.run(cmd, env=env)
    return result.returncode == 0


def main():
    """Run agent tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run agent configuration tests")
    parser.add_argument(
        "--env",
        choices=["mac", "cayucos", "all"],
        default="all",
        help="Environment to test"
    )
    parser.add_argument(
        "--test",
        choices=["info", "basic", "full", "discovery"],
        default="info",
        help="Test suite to run"
    )
    
    args = parser.parse_args()
    
    # Map test choices to test files/methods
    test_map = {
        "info": (
            "tests/integration/test_chat_configurations.py::"
            "TestChatConfigurations::test_environment_info"
        ),
        "basic": (
            "tests/integration/test_chat_configurations.py::"
            "TestChatConfigurations::test_basic_chat_interaction"
        ),
        "full": "tests/integration/test_chat_configurations.py",
        "discovery": (
            "tests/integration/test_agent_configurations.py::"
            "TestAgentConfigurations::test_model_discovery_endpoints"
        ),
    }
    
    test_path = test_map[args.test]
    
    # Run tests
    environments = ["mac", "cayucos"] if args.env == "all" else [args.env]
    
    results = []
    for env in environments:
        success = run_tests_for_env(env, test_path)
        results.append((env, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    for env, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{env}: {status}")
    
    # Exit with failure if any tests failed
    if not all(success for _, success in results):
        sys.exit(1)


if __name__ == "__main__":
    main()