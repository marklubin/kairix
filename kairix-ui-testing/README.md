# Kairix UI Testing Suite

Black-box browser automation testing suite for Kairix project interfaces using Playwright and Firefox.

## Features

- Firefox-only testing for consistency
- Tests the real Gradio UI with patched dependencies
- Page Object Model pattern
- Configurable test scenarios
- HTML test reports with screenshots

## Installation

```bash
# Install dependencies and Firefox
make install
```

## Usage

### Running Tests

```bash
# Run all tests (headed mode)
make test

# Run tests in headless mode
make test-headless

# Debug mode with Playwright Inspector
make test-debug

# Generate HTML report
make test-report
```

### Using Patched UI

Run the real UI with mocked dependencies:

```bash
# Run with default scenario
make test-ui-launch

# Run with streaming test scenario
make test-ui-streaming

# Run with error scenario
make test-ui-error

# Run with long output for scroll testing
make test-ui-long
```

### Running Tests Against Mock

```bash
# Automatically starts mock server and runs tests
make test-ui-mock
```

## Project Structure

```
kairix-ui-testing/
├── src/kairix_ui_testing/
│   ├── core/               # Base test framework
│   ├── config/             # Test configuration
│   ├── interfaces/         # Interface-specific tests
│   ├── mocked_apps/        # Mock UI implementations
│   └── test_runner/        # Test execution utilities
└── tests/                  # Test cases
    ├── memory_pipeline/    # Memory pipeline UI tests
    └── smoke/              # Quick smoke tests
```

## Development

### Adding New Tests

1. Create test files in `tests/memory_pipeline/`
2. Use the base test class from `core/base_test.py`
3. Follow the Page Object pattern

### Configuring Mock Behaviors

Edit `MockConfig` in `mocked_apps/mock_behaviors.py` to add new mock scenarios.

## Environment Variables

Create a `.env` file:

```bash
# Test configuration
MEMORY_PIPELINE_URL=http://localhost:7860
TEST_TIMEOUT=30
HEADLESS=false
```