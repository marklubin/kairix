#!/bin/bash
# Quick test runner for Kairix server

set -e

echo "🧪 Kairix Server Test Runner"
echo "=============================="
echo ""

# Check if server is running
if ! curl -s http://localhost:8888/health > /dev/null 2>&1; then
    echo "❌ Server is not running on port 8888"
    echo "   Start it with: doppler run -p kairix -c mark -- uv run python src/kairix_apps/server.py"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Run the Python test suite
echo "Running automated tests..."
echo ""

uv run python test_server.py

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "⚠️  Some tests failed (exit code: $exit_code)"
    echo "   Check TESTING.md for known issues and workarounds"
fi

exit $exit_code
