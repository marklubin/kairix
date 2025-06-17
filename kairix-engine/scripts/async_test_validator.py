#!/usr/bin/env python3
"""
Async Test Validator

This script analyzes the codebase to:
1. Find all async methods and functions
2. Find all await usages
3. Validate that each async method has corresponding unit tests
4. Check that tests cover common async error scenarios
"""

import ast
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


class AsyncMethodFinder(ast.NodeVisitor):
    """Find all async methods and await statements in a Python file."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.async_methods: list[dict[str, any]] = []
        self.await_usages: list[dict[str, any]] = []
        self.current_class: str | None = None
        self.current_function: str | None = None
        self.function_stack: list[str] = []
        
    def visit_ClassDef(self, node: ast.ClassDef):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Record async function definitions."""
        full_name = self._get_full_name(node.name)
        
        # Check for async generators
        is_async_generator = any(
            isinstance(child, ast.Yield | ast.YieldFrom)
            for child in ast.walk(node)
        )
        
        # Check for async context managers (async with)
        has_async_with = any(
            isinstance(child, ast.AsyncWith)
            for child in ast.walk(node)
        )
        
        # Check for async for loops
        has_async_for = any(
            isinstance(child, ast.AsyncFor)
            for child in ast.walk(node)
        )
        
        self.async_methods.append({
            'name': full_name,
            'line': node.lineno,
            'is_method': self.current_class is not None,
            'class_name': self.current_class,
            'is_async_generator': is_async_generator,
            'has_async_with': has_async_with,
            'has_async_for': has_async_for,
            'docstring': ast.get_docstring(node),
            'decorators': [
                d.id if isinstance(d, ast.Name) else ast.dump(d)
                for d in node.decorator_list
            ]
        })
        
        # Visit children
        old_function = self.current_function
        self.current_function = full_name
        self.function_stack.append(full_name)
        self.generic_visit(node)
        self.function_stack.pop()
        if old_function:
            self.current_function = old_function
        else:
            self.current_function = (
                self.function_stack[-1] if self.function_stack else None
            )
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track regular functions to provide context for await usages."""
        old_function = self.current_function
        full_name = self._get_full_name(node.name)
        self.current_function = full_name
        self.function_stack.append(full_name)
        self.generic_visit(node)
        self.function_stack.pop()
        if old_function:
            self.current_function = old_function
        else:
            self.current_function = (
                self.function_stack[-1] if self.function_stack else None
            )
        
    def visit_Await(self, node: ast.Await):
        """Record await expressions."""
        # Get the expression being awaited
        awaited_expr = ast.dump(node.value)
        
        self.await_usages.append({
            'line': node.lineno,
            'in_function': self.current_function,
            'in_class': self.current_class,
            'expression': awaited_expr[:100],  # Truncate long expressions
        })
        self.generic_visit(node)
        
    def _get_full_name(self, name: str) -> str:
        """Get the fully qualified name including class."""
        if self.current_class:
            return f"{self.current_class}.{name}"
        return name


class TestCoverageFinder(ast.NodeVisitor):
    """Find test methods and analyze their coverage of async scenarios."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.test_methods: list[dict[str, any]] = []
        self.current_class: str | None = None
        
    def visit_ClassDef(self, node: ast.ClassDef):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Find test functions."""
        if node.name.startswith('test_'):
            self._analyze_test_method(node, is_async=False)
        self.generic_visit(node)
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Find async test functions."""
        if node.name.startswith('test_'):
            self._analyze_test_method(node, is_async=True)
        self.generic_visit(node)
        
    def _analyze_test_method(self, node, is_async: bool):
        """Analyze a test method for async testing patterns."""
        test_info = {
            'name': node.name,
            'class_name': self.current_class,
            'line': node.lineno,
            'is_async': is_async,
            'decorators': [
                d.id if isinstance(d, ast.Name) else ast.dump(d)
                for d in node.decorator_list
            ],
            'tests_error_handling': False,
            'tests_timeout': False,
            'tests_cancellation': False,
            'uses_mock': False,
            'uses_asyncmock': False,
            'has_assertions': False,
            'docstring': ast.get_docstring(node),
        }
        
        # Analyze the test body for common patterns
        for child in ast.walk(node):
            # Check for error handling tests
            if isinstance(child, ast.Raise | ast.ExceptHandler):
                test_info['tests_error_handling'] = True
            
            # Check for pytest.raises or assertRaises
            if isinstance(child, ast.Call) and hasattr(child.func, 'attr'):
                if child.func.attr in ['raises', 'assertRaises', 'assertRaisesRegex']:
                    test_info['tests_error_handling'] = True
                elif child.func.attr in ['fail_after', 'timeout', 'wait_for']:
                    test_info['tests_timeout'] = True
                        
            # Check for mock usage
            if isinstance(child, ast.Name):
                if child.id in ['Mock', 'MagicMock', 'patch', 'mock']:
                    test_info['uses_mock'] = True
                elif child.id in ['AsyncMock', 'CoroutineMock']:
                    test_info['uses_asyncmock'] = True
                    
            # Check for assertions
            if isinstance(child, ast.Assert) or (isinstance(child, ast.Call) and 
                hasattr(child.func, 'id') and child.func.id == 'assert'):
                test_info['has_assertions'] = True
                
            # Check for cancellation tests
            if (isinstance(child, ast.Attribute) and 
                    child.attr in ['cancel', 'cancelled']):
                test_info['tests_cancellation'] = True
                
        self.test_methods.append(test_info)


def find_python_files(
    directory: Path, exclude_dirs: set[str] | None = None
) -> list[Path]:
    """Find all Python files in a directory, excluding certain directories."""
    if exclude_dirs is None:
        exclude_dirs = {
            '.venv', '__pycache__', '.git', 'build', 'dist', '.pytest_cache'
        }
    
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Remove excluded directories from search
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
                
    return python_files


def analyze_file(filepath: Path) -> tuple[list[dict], list[dict]]:
    """Analyze a Python file for async methods and await usages."""
    try:
        with open(filepath, encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(filepath))
            
        finder = AsyncMethodFinder(str(filepath))
        finder.visit(tree)
        
        return finder.async_methods, finder.await_usages
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}", file=sys.stderr)
        return [], []


def analyze_test_file(filepath: Path) -> list[dict]:
    """Analyze a test file for test coverage."""
    try:
        with open(filepath, encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(filepath))
            
        finder = TestCoverageFinder(str(filepath))
        finder.visit(tree)
        
        return finder.test_methods
    except Exception as e:
        print(f"Error analyzing test file {filepath}: {e}", file=sys.stderr)
        return []


def find_test_for_method(
    method_name: str, class_name: str | None, test_methods: list[dict]
) -> list[dict]:
    """Find test methods that likely test the given async method."""
    matching_tests = []
    
    # Normalize method name for matching
    method_parts = method_name.lower().replace('_', '').replace('.', '')
    
    for test in test_methods:
        test_name_normalized = test['name'].lower().replace('_', '')
        
        # Check if test name contains method name
        if method_parts in test_name_normalized or (
            class_name and class_name.lower() in test_name_normalized
            and test.get('docstring') and method_name in test['docstring']
        ):
            matching_tests.append(test)
                
    return matching_tests


def generate_report(src_dir: Path, test_dir: Path) -> dict:
    """Generate a comprehensive report on async method test coverage."""
    # Find all source and test files
    src_files = find_python_files(src_dir)
    test_files = find_python_files(test_dir)
    
    # Analyze source files
    all_async_methods = []
    all_await_usages = []
    
    for filepath in src_files:
        if 'test' not in str(filepath):  # Skip test files in src
            methods, awaits = analyze_file(filepath)
            for method in methods:
                method['filepath'] = str(filepath.relative_to(src_dir.parent))
            for await_usage in awaits:
                await_usage['filepath'] = str(filepath.relative_to(src_dir.parent))
            all_async_methods.extend(methods)
            all_await_usages.extend(awaits)
    
    # Analyze test files
    all_test_methods = []
    for filepath in test_files:
        tests = analyze_test_file(filepath)
        for test in tests:
            test['filepath'] = str(filepath.relative_to(test_dir.parent))
        all_test_methods.extend(tests)
    
    # Match async methods with their tests
    coverage_report = {
        'summary': {
            'total_async_methods': len(all_async_methods),
            'total_await_usages': len(all_await_usages),
            'total_test_methods': len(all_test_methods),
            'async_methods_with_tests': 0,
            'async_methods_without_tests': 0,
            'tests_with_error_handling': 0,
            'tests_with_timeout_handling': 0,
            'tests_with_cancellation': 0,
        },
        'async_methods': [],
        'uncovered_methods': [],
        'await_usage_summary': defaultdict(int),
    }
    
    # Analyze coverage
    for method in all_async_methods:
        matching_tests = find_test_for_method(
            method['name'], 
            method.get('class_name'),
            all_test_methods
        )
        
        method_report = {
            'method': method,
            'tests': matching_tests,
            'has_tests': len(matching_tests) > 0,
            'test_quality': {
                'has_async_tests': any(t['is_async'] for t in matching_tests),
                'tests_errors': any(t['tests_error_handling'] for t in matching_tests),
                'tests_timeout': any(t['tests_timeout'] for t in matching_tests),
                'tests_cancellation': any(
                    t['tests_cancellation'] for t in matching_tests
                ),
                'uses_async_mock': any(t['uses_asyncmock'] for t in matching_tests),
            }
        }
        
        coverage_report['async_methods'].append(method_report)
        
        if method_report['has_tests']:
            coverage_report['summary']['async_methods_with_tests'] += 1
        else:
            coverage_report['summary']['async_methods_without_tests'] += 1
            coverage_report['uncovered_methods'].append(method)
    
    # Summarize await usage
    for await_usage in all_await_usages:
        location = await_usage.get('in_function', 'module_level')
        coverage_report['await_usage_summary'][location] += 1
    
    # Count test quality metrics
    for test in all_test_methods:
        if test['tests_error_handling']:
            coverage_report['summary']['tests_with_error_handling'] += 1
        if test['tests_timeout']:
            coverage_report['summary']['tests_with_timeout_handling'] += 1
        if test['tests_cancellation']:
            coverage_report['summary']['tests_with_cancellation'] += 1
    
    return coverage_report


def print_report(report: dict, verbose: bool = False):
    """Print a human-readable report."""
    print("=" * 80)
    print("ASYNC METHOD TEST COVERAGE REPORT")
    print("=" * 80)
    print()
    
    # Summary
    summary = report['summary']
    print("SUMMARY:")
    print(f"  Total async methods found: {summary['total_async_methods']}")
    print(f"  Total await usages: {summary['total_await_usages']}")
    print(f"  Async methods with tests: {summary['async_methods_with_tests']}")
    print(f"  Async methods WITHOUT tests: {summary['async_methods_without_tests']}")
    coverage_pct = (
        summary['async_methods_with_tests'] / 
        max(summary['total_async_methods'], 1) * 100
    )
    print(f"  Coverage: {coverage_pct:.1f}%")
    print()
    print("TEST QUALITY METRICS:")
    print(f"  Tests with error handling: {summary['tests_with_error_handling']}")
    print(f"  Tests with timeout handling: {summary['tests_with_timeout_handling']}")
    print(f"  Tests with cancellation: {summary['tests_with_cancellation']}")
    print()
    
    # Uncovered methods
    if report['uncovered_methods']:
        print("ASYNC METHODS WITHOUT TEST COVERAGE:")
        for method in report['uncovered_methods']:
            print(f"  - {method['filepath']}:{method['line']} - {method['name']}")
            if method['is_async_generator']:
                print("    ⚠️  Async generator - needs streaming test")
            if method['has_async_with']:
                print("    ⚠️  Uses async with - needs context manager test")
            if method['has_async_for']:
                print("    ⚠️  Uses async for - needs async iteration test")
        print()
    
    # Methods with insufficient test coverage
    print("ASYNC METHODS WITH INSUFFICIENT TEST COVERAGE:")
    insufficient_count = 0
    for method_report in report['async_methods']:
        if method_report['has_tests']:
            quality = method_report['test_quality']
            issues = []
            
            if not quality['has_async_tests']:
                issues.append("No async tests")
            if not quality['tests_errors']:
                issues.append("No error handling tests")
            if (
                method_report['method']['has_async_for'] 
                and not quality['tests_timeout']
            ):
                issues.append("Has async for but no timeout tests")
                
            if issues:
                insufficient_count += 1
                method = method_report['method']
                print(f"  - {method['filepath']}:{method['line']} - {method['name']}")
                for issue in issues:
                    print(f"    ⚠️  {issue}")
    
    if insufficient_count == 0:
        print("  ✅ All tested async methods have adequate test coverage")
    print()
    
    # Await usage summary
    if verbose and report['await_usage_summary']:
        print("AWAIT USAGE BY FUNCTION:")
        sorted_items = sorted(
            report['await_usage_summary'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        for func, count in sorted_items[:10]:
            print(f"  {func}: {count} await expressions")
        print()
    
    # Return exit code based on coverage
    uncovered = summary['async_methods_without_tests']
    if uncovered > 0:
        print(f"❌ FAILED: {uncovered} async methods lack test coverage")
        return 1
    else:
        print("✅ PASSED: All async methods have test coverage")
        return 0


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate async method test coverage')
    parser.add_argument(
        '--src', type=Path, default=Path('src'), help='Source directory'
    )
    parser.add_argument(
        '--tests', type=Path, default=Path('tests'), help='Tests directory'
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--json', type=Path, help='Output JSON report to file')
    parser.add_argument(
        '--strict', action='store_true', 
        help='Fail if any async method lacks quality tests'
    )
    
    args = parser.parse_args()
    
    # Validate directories exist
    if not args.src.exists():
        print(f"Error: Source directory {args.src} does not exist", file=sys.stderr)
        sys.exit(1)
    if not args.tests.exists():
        print(f"Error: Tests directory {args.tests} does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Generate report
    report = generate_report(args.src, args.tests)
    
    # Output JSON if requested
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"JSON report written to {args.json}")
    
    # Print report and get exit code
    exit_code = print_report(report, verbose=args.verbose)
    
    # In strict mode, also fail if quality is insufficient
    if args.strict and exit_code == 0:
        for method_report in report['async_methods']:
            if method_report['has_tests']:
                quality = method_report['test_quality']
                if not quality['tests_errors'] or not quality['has_async_tests']:
                    print(
                        "\n❌ FAILED in strict mode: "
                        "Some async methods lack quality tests"
                    )
                    exit_code = 1
                    break
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()