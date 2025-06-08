#!/usr/bin/env python3
"""Run a single test to verify everything works."""

import sys
import subprocess
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Run a simple test."""
    print("Running a single test to verify setup...\n")
    
    # Run the simplest test
    test_file = "tests/memory_pipeline/test_import_tab_ui.py::TestImportTabFileHandling::test_import_output_persistence"
    
    cmd = [
        sys.executable, "-m", "pytest",
        test_file,
        "-v",
        "--tb=short"
    ]
    
    print(f"Running: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    
    if result.returncode == 0:
        print("\n✅ Test passed! The setup is working correctly.")
        print("\nYou can now run all tests with:")
        print("  pytest tests/")
        print("  # or")
        print("  make test")
    else:
        print("\n❌ Test failed. Check the output above for errors.")
        print("\nCommon issues:")
        print("- Missing dependencies: run 'uv sync'")
        print("- Firefox not installed: run 'uv run playwright install firefox'")
        print("- Test data missing: run 'python verify_setup.py'")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())