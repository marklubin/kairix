#!/usr/bin/env python3
"""
Comprehensive test runner for Apiana AI.

This script runs all test suites and provides a summary of results.
It handles environment setup checks and provides clear feedback.
"""

import subprocess
import sys
import time


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def run_command(cmd, description):
    """Run a command and return success status and output."""
    print(f"\n{Colors.BLUE}▶ {description}{Colors.RESET}")
    print(f"  Command: {cmd}")
    
    start_time = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    duration = time.time() - start_time
    
    success = result.returncode == 0
    
    if success:
        print(f"{Colors.GREEN}✓ Completed in {duration:.1f}s{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ Failed after {duration:.1f}s{Colors.RESET}")
        if result.stderr:
            print(f"{Colors.RED}Error output:{Colors.RESET}")
            print(result.stderr)
    
    return success, result.stdout, result.stderr


def check_environment():
    """Check if required services are running."""
    print(f"\n{Colors.BOLD}🔍 Checking Environment{Colors.RESET}")
    
    issues = []
    
    # Check Neo4j
    neo4j_check, _, _ = run_command(
        "docker ps | grep neo4j > /dev/null",
        "Checking Neo4j container"
    )
    if not neo4j_check:
        issues.append("Neo4j container is not running. Run: docker-compose up -d")
    
    # Check if Neo4j is accessible
    if neo4j_check:
        neo4j_access, _, _ = run_command(
            "docker exec apiana-neo4j cypher-shell -u neo4j -p password 'RETURN 1' > /dev/null 2>&1",
            "Checking Neo4j accessibility"
        )
        if not neo4j_access:
            issues.append("Neo4j is running but not accessible. It might still be starting up.")
    
    # Check Playwright browsers (check if the chromium directory exists)
    playwright_check, _, _ = run_command(
        "ls ~/.cache/ms-playwright/chromium* > /dev/null 2>&1",
        "Checking Playwright browsers"
    )
    if not playwright_check:
        # Try alternative check
        playwright_check2, _, _ = run_command(
            "uv run python -c 'from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop()' > /dev/null 2>&1",
            "Checking Playwright functionality"
        )
        if not playwright_check2:
            issues.append("Playwright browsers not installed. Run: uv run playwright install chromium")
    
    return issues


def run_tests():
    """Run all test suites and collect results."""
    print(f"\n{Colors.BOLD}🧪 Running Test Suites{Colors.RESET}")
    
    results = {}
    
    # 1. Unit Tests
    success, stdout, _ = run_command(
        "uv run pytest -v --tb=short",
        "Running Unit Tests"
    )
    results['unit'] = parse_pytest_output(stdout)
    
    # 2. UI Automation Tests
    success, stdout, _ = run_command(
        "uv run pytest tests/ui_automation/ -v -m 'ui_automation' -k ''",
        "Running UI Automation Tests"
    )
    results['ui'] = parse_pytest_output(stdout)
    
    # 3. Integration Tests
    success, stdout, _ = run_command(
        "uv run pytest -v -k 'integration' --ignore=scripts/",
        "Running Integration Tests"
    )
    results['integration'] = parse_pytest_output(stdout)
    
    return results


def parse_pytest_output(output):
    """Parse pytest output to extract test counts."""
    lines = output.split('\n')
    for line in lines:
        if 'passed' in line or 'failed' in line or 'skipped' in line:
            # Extract numbers from summary line
            passed = 0
            failed = 0
            skipped = 0
            errors = 0
            
            import re
            
            passed_match = re.search(r'(\d+) passed', line)
            if passed_match:
                passed = int(passed_match.group(1))
            
            failed_match = re.search(r'(\d+) failed', line)
            if failed_match:
                failed = int(failed_match.group(1))
            
            skipped_match = re.search(r'(\d+) skipped', line)
            if skipped_match:
                skipped = int(skipped_match.group(1))
            
            error_match = re.search(r'(\d+) error', line)
            if error_match:
                errors = int(error_match.group(1))
            
            return {
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'errors': errors,
                'total': passed + failed + skipped + errors
            }
    
    return {'passed': 0, 'failed': 0, 'skipped': 0, 'errors': 0, 'total': 0}


def print_summary(results, env_issues):
    """Print a comprehensive summary of test results."""
    print(f"\n{Colors.BOLD}📊 Test Results Summary{Colors.RESET}")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_errors = 0
    
    for suite, counts in results.items():
        total_passed += counts['passed']
        total_failed += counts['failed']
        total_skipped += counts['skipped']
        total_errors += counts['errors']
        
        status_symbol = "✅" if counts['failed'] == 0 and counts['errors'] == 0 else "❌"
        
        print(f"\n{status_symbol} {suite.upper()} Tests:")
        print(f"   Passed:  {Colors.GREEN}{counts['passed']:3d}{Colors.RESET}")
        print(f"   Failed:  {Colors.RED if counts['failed'] > 0 else ''}{counts['failed']:3d}{Colors.RESET}")
        print(f"   Errors:  {Colors.RED if counts['errors'] > 0 else ''}{counts['errors']:3d}{Colors.RESET}")
        print(f"   Skipped: {Colors.YELLOW}{counts['skipped']:3d}{Colors.RESET}")
        print(f"   Total:   {counts['total']:3d}")
    
    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}OVERALL:{Colors.RESET}")
    print(f"   Total Passed:  {Colors.GREEN}{total_passed}{Colors.RESET}")
    print(f"   Total Failed:  {Colors.RED if total_failed > 0 else ''}{total_failed}{Colors.RESET}")
    print(f"   Total Errors:  {Colors.RED if total_errors > 0 else ''}{total_errors}{Colors.RESET}")
    print(f"   Total Skipped: {Colors.YELLOW}{total_skipped}{Colors.RESET}")
    
    if env_issues:
        print(f"\n{Colors.YELLOW}⚠️  Environment Issues:{Colors.RESET}")
        for issue in env_issues:
            print(f"   - {issue}")
    
    if total_failed > 0 or total_errors > 0:
        print(f"\n{Colors.RED}❌ Some tests failed or had errors{Colors.RESET}")
        return 1
    else:
        print(f"\n{Colors.GREEN}✅ All tests passed!{Colors.RESET}")
        return 0


def main():
    """Main entry point."""
    import os
    
    print(f"{Colors.BOLD}🚀 Apiana AI Comprehensive Test Runner{Colors.RESET}")
    
    # Check environment
    env_issues = check_environment()
    
    if env_issues:
        print(f"\n{Colors.YELLOW}⚠️  Environment issues detected:{Colors.RESET}")
        for issue in env_issues:
            print(f"   - {issue}")
        
        # In CI or non-interactive mode, continue anyway
        if os.environ.get('CI') or not sys.stdin.isatty():
            print(f"\n{Colors.YELLOW}Running in non-interactive mode, continuing...{Colors.RESET}")
        else:
            response = input(f"\n{Colors.YELLOW}Continue anyway? (y/N):{Colors.RESET} ")
            if response.lower() != 'y':
                print("Aborting test run.")
                return 1
    
    # Run tests
    results = run_tests()
    
    # Print summary
    exit_code = print_summary(results, env_issues)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())