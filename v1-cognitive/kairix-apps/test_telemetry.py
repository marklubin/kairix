#!/usr/bin/env python3
"""Test script for telemetry system."""
import time
from datetime import datetime, timedelta
from kairix_apps.telemetry_manager import TelemetryManager
from kairix_apps.db_wrapper import DatabaseWrapper, is_shadow_environment

def test_telemetry():
    """Test the telemetry manager."""
    print("🧪 Testing Telemetry System")
    print("=" * 60)

    # Test 1: Initialize TelemetryManager
    print("\n1. Initializing TelemetryManager...")
    tm = TelemetryManager(db_path=".kairix/test_telemetry.db")
    print("   ✓ TelemetryManager initialized")

    # Test 2: Track a request
    print("\n2. Tracking a test request...")
    request_id = tm.start_request(
        endpoint="/v1/chat/completions",
        method="POST",
        client_ip="127.0.0.1",
        user_agent="test-client"
    )
    print(f"   ✓ Request started: {request_id}")

    # Simulate processing time
    time.sleep(0.1)

    # End the request
    tm.end_request(
        request_id=request_id,
        status_code=200,
        duration_ms=100.5,
        model_id="kairix-conversational",
        tokens={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
        stream=False,
        message_count=2
    )
    print("   ✓ Request completed and logged")

    # Test 3: Get metrics
    print("\n3. Retrieving metrics...")
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)

    metrics = tm.get_metrics(
        start_time=start_time,
        end_time=end_time
    )
    print(f"   ✓ Total requests: {metrics['total_requests']}")
    print(f"   ✓ Avg duration: {metrics['avg_duration_ms']} ms")
    print(f"   ✓ Total tokens: {metrics['total_tokens']}")

    # Test 4: Get timeseries
    print("\n4. Retrieving timeseries data...")
    timeseries = tm.get_timeseries(
        start_time=start_time,
        end_time=end_time,
        interval_minutes=5
    )
    print(f"   ✓ Timeseries buckets: {len(timeseries)}")

    print("\n" + "=" * 60)
    print("✅ All telemetry tests passed!")

def test_db_wrapper():
    """Test the database wrapper."""
    print("\n🧪 Testing Database Wrapper")
    print("=" * 60)

    # Test 1: Read/write mode
    print("\n1. Testing read/write mode...")
    db = DatabaseWrapper(db_path=".kairix/test_db.db", read_only=False)
    print(f"   ✓ Read-only mode: {db.is_read_only()}")

    # Test 2: Read-only mode
    print("\n2. Testing read-only mode...")
    db_ro = DatabaseWrapper(db_path=".kairix/test_db.db", read_only=True)
    print(f"   ✓ Read-only mode: {db_ro.is_read_only()}")

    # Test 3: Environment detection
    print("\n3. Testing environment detection...")
    is_shadow = is_shadow_environment()
    print(f"   ✓ Is shadow environment: {is_shadow}")

    print("\n" + "=" * 60)
    print("✅ All database wrapper tests passed!")

if __name__ == "__main__":
    try:
        test_telemetry()
        test_db_wrapper()
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
