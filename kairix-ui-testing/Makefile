.PHONY: install test test-headless test-debug mock-ui mock-ui-fail mock-ui-slow mock-ui-timeout clean

# Install dependencies and Firefox for Playwright
install:
	uv sync
	uv run playwright install firefox
	uv run playwright install-deps firefox

# Run UI tests with Firefox (headed mode)
test:
	uv run pytest tests/ --headed -v

# Run UI tests with Firefox (headless)
test-headless:
	uv run pytest tests/ -v

# Run UI tests with Firefox in debug mode
test-debug:
	PWDEBUG=1 uv run pytest -s tests/

# Launch patched UI with different scenarios
test-ui-launch:
	uv run python -m kairix_ui_testing.test_runner.patched_ui_runner

test-ui-streaming:
	uv run python -m kairix_ui_testing.test_runner.patched_ui_runner --scenario streaming

test-ui-error:
	uv run python -m kairix_ui_testing.test_runner.patched_ui_runner --scenario error

test-ui-long:
	uv run python -m kairix_ui_testing.test_runner.patched_ui_runner --scenario long-output

# Run mock server for manual testing (deprecated - use test-ui-launch)
mock-ui:
	uv run python -m kairix_ui_testing.test_runner.mock_server

# Run mock with various scenarios (deprecated)
mock-ui-fail:
	uv run python -m kairix_ui_testing.test_runner.mock_server --fail-import --fail-summarize

mock-ui-slow:
	uv run python -m kairix_ui_testing.test_runner.mock_server --slow

mock-ui-timeout:
	uv run python -m kairix_ui_testing.test_runner.mock_server --timeout

# Generate test report
test-report:
	uv run pytest tests/ --html=reports/firefox-test-report.html --self-contained-html

# Run tests against mock
test-ui-mock:
	# Start mock in background
	uv run python -m kairix_ui_testing.test_runner.mock_server &
	sleep 2
	# Run tests
	uv run pytest tests/memory_pipeline/ -v
	# Kill mock server
	pkill -f mock_server || true

# Clean up
clean:
	rm -rf .pytest_cache
	rm -rf reports
	rm -rf screenshots
	find . -type d -name __pycache__ -exec rm -rf {} + || true