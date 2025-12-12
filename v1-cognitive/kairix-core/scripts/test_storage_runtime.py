#!/usr/bin/env python3
"""Test StorageRuntime initialization and usage."""
import sys
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_storage_runtime():
    """Test different ways to initialize StorageRuntime."""
    print("Testing StorageRuntime initialization...\n")
    
    try:
        from kairix_core.runtime.storage import StorageRuntime
        
        # Test 1: Default initialization
        print("1. Testing default initialization:")
        try:
            storage = StorageRuntime()
            print("   ✓ Default init successful")
            print(f"   Database path: {storage.db_path}")
        except Exception as e:
            print(f"   ✗ Default init failed: {e}")
            traceback.print_exc()
            
        # Test 2: With explicit db_path
        print("\n2. Testing with explicit db_path:")
        try:
            storage = StorageRuntime(db_path="../.sqlite/test.db")
            print("   ✓ Explicit path init successful")
            print(f"   Database path: {storage.db_path}")
        except Exception as e:
            print(f"   ✗ Explicit path init failed: {e}")
            traceback.print_exc()
            
        # Test 3: Check what parameters StorageRuntime actually accepts
        print("\n3. Checking StorageRuntime signature:")
        import inspect
        sig = inspect.signature(StorageRuntime.__init__)
        print(f"   Parameters: {sig}")
        
        # Test 4: Look at the actual StorageRuntime class
        print("\n4. StorageRuntime class info:")
        print(f"   Module: {StorageRuntime.__module__}")
        print(f"   File: {inspect.getfile(StorageRuntime)}")
        
    except ImportError as e:
        print(f"Failed to import StorageRuntime: {e}")
        traceback.print_exc()

def check_storage_runtime_source():
    """Check the actual StorageRuntime implementation."""
    print("\n\nChecking StorageRuntime source code...")
    
    try:
        storage_file = Path(__file__).parent.parent / "src" / "kairix_core" / "runtime" / "storage.py"
        if storage_file.exists():
            print(f"Found storage.py at: {storage_file}")
            # Read first 50 lines to see the class definition
            with open(storage_file, 'r') as f:
                lines = f.readlines()[:100]
                
            # Find StorageRuntime class definition
            in_class = False
            for i, line in enumerate(lines):
                if 'class StorageRuntime' in line:
                    in_class = True
                    print(f"\nStorageRuntime class definition (starting at line {i+1}):")
                    
                if in_class and line.strip() and not line.startswith(' '):
                    # End of class definition
                    break
                    
                if in_class:
                    print(f"{i+1:4d}: {line.rstrip()}")
                    
                if in_class and '__init__' in line:
                    # Print next 10 lines after __init__
                    for j in range(min(10, len(lines) - i - 1)):
                        print(f"{i+j+2:4d}: {lines[i+j+1].rstrip()}")
                    break
        else:
            print(f"Storage.py not found at expected location: {storage_file}")
            
    except Exception as e:
        print(f"Error reading source: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_storage_runtime()
    check_storage_runtime_source()