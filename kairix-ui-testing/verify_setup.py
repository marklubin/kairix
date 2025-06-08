#!/usr/bin/env python3
"""Verify the test setup is working correctly."""

import sys
from pathlib import Path

def check_imports():
    """Check that all required imports work."""
    print("Checking imports...")
    try:
        import gradio
        print("✓ Gradio imported")
    except ImportError as e:
        print(f"✗ Failed to import gradio: {e}")
        return False
        
    try:
        import playwright
        print("✓ Playwright imported")
    except ImportError as e:
        print(f"✗ Failed to import playwright: {e}")
        return False
        
    try:
        from kairix_ui_testing.mocked_apps.test_memory_pipeline_ui import create_test_ui
        print("✓ Test UI module imported")
    except ImportError as e:
        print(f"✗ Failed to import test UI: {e}")
        return False
        
    try:
        from kairix_ui_testing.core.test_server import TestServer
        print("✓ Test server imported")
    except ImportError as e:
        print(f"✗ Failed to import test server: {e}")
        return False
        
    return True

def check_test_data():
    """Check test data directory exists."""
    print("\nChecking test data...")
    test_data_dir = Path("test_data")
    if not test_data_dir.exists():
        print("Creating test_data directory...")
        test_data_dir.mkdir(exist_ok=True)
        
    # Create test file
    test_file = test_data_dir / "test-convos.json"
    if not test_file.exists():
        print("Creating test-convos.json...")
        import json
        dummy_data = {
            "conversations": [{
                "id": "test-1",
                "title": "Test Conversation",
                "create_time": 1704067200,
                "mapping": {
                    "msg1": {
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["Test message"]},
                            "create_time": 1704067200
                        }
                    }
                }
            }]
        }
        with open(test_file, "w") as f:
            json.dump(dummy_data, f, indent=2)
    
    print("✓ Test data ready")
    return True

def test_server_launch():
    """Test that the server can launch."""
    print("\nTesting server launch...")
    try:
        from kairix_ui_testing.core.test_server import TestServer
        from kairix_ui_testing.test_scenarios import TestScenarios
        
        server = TestServer(TestScenarios.default(), port=7863)
        server.start()
        
        if server.is_running:
            print("✓ Test server launched successfully")
            server.stop()
            return True
        else:
            print("✗ Server failed to start")
            return False
            
    except Exception as e:
        print(f"✗ Server launch failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all checks."""
    print("=== Kairix UI Testing Setup Verification ===\n")
    
    # Add src to path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))
    
    all_good = True
    
    if not check_imports():
        all_good = False
        
    if not check_test_data():
        all_good = False
        
    if not test_server_launch():
        all_good = False
        
    print("\n" + "="*40)
    if all_good:
        print("✅ All checks passed! Ready to run tests.")
        print("\nRun tests with: pytest tests/")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())