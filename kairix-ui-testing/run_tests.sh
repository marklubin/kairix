#!/bin/bash
# Run UI tests with proper setup

set -e

echo "=== Kairix UI Testing Suite ==="
echo

# Check if in correct directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Must run from kairix-ui-testing directory"
    exit 1
fi

# Create test data directory if needed
mkdir -p test_data
mkdir -p screenshots
mkdir -p reports

# Create test data file if missing
if [ ! -f "test_data/test-convos.json" ]; then
    echo "Creating test data file..."
    cat > test_data/test-convos.json << 'EOF'
{
  "conversations": [
    {
      "id": "test-1",
      "title": "Test Conversation 1",
      "create_time": 1704067200,
      "mapping": {
        "msg1": {
          "message": {
            "author": {"role": "user"},
            "content": {"parts": ["Hello, this is a test"]},
            "create_time": 1704067200
          }
        },
        "msg2": {
          "message": {
            "author": {"role": "assistant"},
            "content": {"parts": ["Hello! This is a test response."]},
            "create_time": 1704067260
          }
        }
      }
    }
  ]
}
EOF
fi

# Parse command line arguments
TEST_ARGS=""
HEADED="--headed"
VERBOSE="-v"

while [[ $# -gt 0 ]]; do
    case $1 in
        --headless)
            HEADED=""
            shift
            ;;
        --debug)
            export PWDEBUG=1
            shift
            ;;
        -q|--quiet)
            VERBOSE=""
            shift
            ;;
        *)
            TEST_ARGS="$TEST_ARGS $1"
            shift
            ;;
    esac
done

# Run the tests
echo "Running tests..."
echo "Options: $HEADED $VERBOSE"
echo

if [ -z "$TEST_ARGS" ]; then
    # Run all tests
    uv run pytest tests/ $HEADED $VERBOSE
else
    # Run specific tests
    uv run pytest $TEST_ARGS $HEADED $VERBOSE
fi

# Check if tests passed
if [ $? -eq 0 ]; then
    echo
    echo "✅ All tests passed!"
else
    echo
    echo "❌ Some tests failed. Check screenshots/ directory for failure screenshots."
fi