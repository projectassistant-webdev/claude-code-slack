# Testing Guide

Comprehensive guide for testing the Claude Code Slack Integration.

## Table of Contents
- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Mock Slack Server](#mock-slack-server)
- [Manual Testing](#manual-testing)
- [Continuous Testing](#continuous-testing)
- [Coverage Reports](#coverage-reports)

## Quick Start

### Run All Tests
```bash
# Using the test runner
python3 tests/run_tests.py

# Verbose output
python3 tests/run_tests.py --verbose
```

### Run Specific Categories
```bash
# Unit tests only
python3 tests/run_tests.py unit

# Integration tests only
python3 tests/run_tests.py integration

# System tests only
python3 tests/run_tests.py system
```

### Quick Validation
```bash
# Dry run to check structure
python3 tests/run_tests.py --dry-run

# Run with debug output
export SLACK_DEBUG=1
python3 tests/run_tests.py
```

## Test Structure

```
tests/
├── run_tests.py              # Main test runner
├── conftest.py              # Shared test configuration
├── requirements.txt         # Test dependencies (optional)
├── unit/                    # Unit tests
│   ├── test_url_validation.py
│   ├── test_webhook_formatting.py
│   ├── test_configuration.py
│   └── test_*_command.py   # Command handler tests
├── integration/             # Integration tests
│   ├── test_stop_hook.py
│   ├── test_notification_hook.py
│   └── test_posttooluse_hook.py
├── system/                  # System tests
│   ├── test_installation_flow.py
│   ├── test_cross_platform.py
│   └── test_uninstallation.py
└── fixtures/                # Test data and mocks
```

## Running Tests

### Prerequisites

No external dependencies required! Tests use Python standard library only.

```bash
# Verify Python version (3.6+ required)
python3 --version

# Set Python path if needed
export PYTHONPATH="$PYTHONPATH:$(pwd)"
```

### Command Line Options

```bash
# Run all tests
python3 tests/run_tests.py

# Run specific category
python3 tests/run_tests.py unit
python3 tests/run_tests.py integration
python3 tests/run_tests.py system

# Verbose output
python3 tests/run_tests.py --verbose

# Dry run (no execution)
python3 tests/run_tests.py --dry-run

# With pattern matching
python3 tests/run_tests.py --pattern "test_webhook*"
```

### Environment Variables

```bash
# Enable debug output
export SLACK_DEBUG=1

# Use dry run mode (no actual webhook sends)
export SLACK_DRY_RUN=1

# Custom test configuration
export SLACK_TEST_WEBHOOK="https://hooks.slack.com/services/TEST/WEBHOOK"

# Disable color output
export NO_COLOR=1
```

## Test Categories

### Unit Tests

Test individual functions and methods in isolation.

#### What They Test
- URL validation logic
- Block Kit message formatting
- Configuration file handling
- Command argument parsing
- Error handling

#### Example Test
```python
# tests/unit/test_url_validation.py
import unittest
from commands.slack import slack_utils

class TestWebhookValidation(unittest.TestCase):
    def test_valid_incoming_webhook(self):
        url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
        self.assertTrue(slack_utils.validate_webhook_url(url))

    def test_invalid_webhook_url(self):
        url = "https://example.com/webhook"
        with self.assertRaises(ValueError):
            slack_utils.validate_webhook_url(url)
```

#### Running Unit Tests
```bash
# All unit tests
python3 tests/run_tests.py unit

# Specific test file
python3 tests/unit/test_url_validation.py

# Specific test class
python3 -m unittest tests.unit.test_url_validation.TestWebhookValidation

# Specific test method
python3 -m unittest tests.unit.test_url_validation.TestWebhookValidation.test_valid_incoming_webhook
```

### Integration Tests

Test component interactions and hook functionality.

#### What They Test
- Hook script execution
- JSON input/output handling
- Configuration loading
- Webhook sending (mocked)
- Error propagation

#### Example Test
```python
# tests/integration/test_stop_hook.py
import json
import subprocess
import tempfile

def test_stop_hook_execution():
    # Create test input
    test_input = {
        "session_id": "test-123",
        "transcript_path": "/tmp/test.md",
        "stop_hook_active": True
    }

    # Execute hook
    result = subprocess.run(
        ["python3", "hooks/stop-slack.py"],
        input=json.dumps(test_input),
        capture_output=True,
        text=True
    )

    # Verify execution
    assert result.returncode == 0
```

#### Running Integration Tests
```bash
# All integration tests
python3 tests/run_tests.py integration

# With mock server
python3 tests/mock_slack_server.py &
SERVER_PID=$!
python3 tests/run_tests.py integration
kill $SERVER_PID
```

### System Tests

Test complete workflows and installation procedures.

#### What They Test
- Installation script execution
- Hook registration in settings.json
- Command availability
- Cross-platform compatibility
- Uninstallation cleanup

#### Example Test
```python
# tests/system/test_installation_flow.py
import os
import tempfile
import shutil

def test_local_installation():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy installation script
        shutil.copy("install.sh", tmpdir)

        # Run installation
        os.system(f"cd {tmpdir} && ./install.sh")

        # Verify structure
        assert os.path.exists(f"{tmpdir}/.claude/hooks/stop-slack.py")
        assert os.path.exists(f"{tmpdir}/.claude/commands/slack/")
```

#### Running System Tests
```bash
# All system tests
python3 tests/run_tests.py system

# Specific workflow
python3 tests/system/test_installation_flow.py
```

## Mock Slack Server

Test webhook functionality without sending real Slack messages.

### Starting Mock Server

```bash
# Start in foreground
python3 tests/mock_slack_server.py

# Start in background
python3 tests/mock_slack_server.py --background

# Custom port
python3 tests/mock_slack_server.py --port 9999
```

### Mock Server Features
- Accepts webhook POST requests
- Validates JSON payloads
- Simulates rate limiting (429)
- Simulates server errors (500)
- Logs all received webhooks
- Returns appropriate responses

### Using Mock Server in Tests

```python
import requests

# Configure to use mock server
MOCK_WEBHOOK = "http://localhost:8888/services/TEST/WEBHOOK"

def test_webhook_delivery():
    payload = {
        "blocks": [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Test message"}
        }]
    }

    response = requests.post(MOCK_WEBHOOK, json=payload)
    assert response.status_code == 200
```

### Viewing Mock Server Logs

```bash
# View received webhooks
cat /tmp/webhook_logs.json

# Monitor in real-time
tail -f /tmp/webhook_logs.json | python3 -m json.tool
```

## Manual Testing

### Testing Installation

```bash
# Test local installation
cd /tmp/test-project
curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash

# Verify installation
ls -la .claude/hooks/*slack*
ls -la .claude/commands/slack/
cat .claude/settings.json | grep slack
```

### Testing Commands

```bash
# Test each command
/user:slack:setup https://hooks.slack.com/services/TEST/WEBHOOK
/user:slack:status
/user:slack:start
/user:slack:stop
/user:slack:remove
```

### Testing Hooks Manually

```bash
# Test Stop hook
echo '{"session_id":"test","transcript_path":"/tmp/test.md"}' | \
  python3 .claude/hooks/stop-slack.py

# Test Notification hook
echo '{"session_id":"test","message":"Input needed"}' | \
  python3 .claude/hooks/notification-slack.py

# Test PostToolUse hook
echo '{"session_id":"test","tool_name":"Edit","tool_response":"OK"}' | \
  python3 .claude/hooks/posttooluse-slack.py
```

### Testing with Real Slack

1. **Create test webhook**:
   - Go to Slack App settings
   - Create test webhook for #test-channel
   - Copy webhook URL

2. **Configure integration**:
```bash
/user:slack:setup YOUR_TEST_WEBHOOK_URL
/user:slack:start
```

3. **Trigger notifications**:
```bash
# Use Claude Code normally
# Notifications should appear in #test-channel
```

## Continuous Testing

### Pre-commit Hook

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
python3 tests/run_tests.py unit
if [ $? -ne 0 ]; then
    echo "Unit tests failed. Commit aborted."
    exit 1
fi
```

### GitHub Actions (Future)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: python3 tests/run_tests.py
```

## Coverage Reports

### Generate Coverage Report

```bash
# If coverage.py is available
pip install coverage
coverage run tests/run_tests.py
coverage report
coverage html
open htmlcov/index.html
```

### Manual Coverage Check

```bash
# List all functions
grep -r "^def " commands/slack/*.py hooks/*.py | wc -l

# List tested functions
grep -r "test_" tests/unit/*.py tests/integration/*.py | wc -l

# Calculate percentage
echo "scale=2; (tested/total)*100" | bc
```

### Coverage Targets
- **Overall**: 80% minimum
- **Critical paths**: 95% minimum
- **Error handling**: 90% minimum
- **Commands**: 100% minimum

## Test Best Practices

### Writing Good Tests
1. **Test one thing** - Each test should verify a single behavior
2. **Use descriptive names** - `test_webhook_validation_rejects_http_urls`
3. **Follow AAA pattern** - Arrange, Act, Assert
4. **Mock external dependencies** - Don't rely on network/filesystem
5. **Test edge cases** - Empty inputs, None values, invalid data

### Test Data Management
```python
# Use fixtures for test data
TEST_WEBHOOK = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
TEST_SESSION = {"session_id": "test-123"}

# Create temporary files
with tempfile.NamedTemporaryFile() as tmp:
    tmp.write(b"test content")
    tmp.seek(0)
    # Use tmp.name for file path
```

### Debugging Tests
```bash
# Run with Python debugger
python3 -m pdb tests/unit/test_url_validation.py

# Add breakpoints in code
import pdb; pdb.set_trace()

# Verbose test output
python3 tests/run_tests.py --verbose

# Print debug info
export SLACK_DEBUG=1
```

## Troubleshooting Tests

### Common Issues

#### ImportError
```bash
# Fix Python path
export PYTHONPATH="$PYTHONPATH:$(pwd)"

# Or run from project root
cd /path/to/claude-code-slack
python3 tests/run_tests.py
```

#### Permission Denied
```bash
# Make scripts executable
chmod +x tests/run_tests.py
chmod +x hooks/*.py
```

#### Mock Server Port in Use
```bash
# Find process using port
lsof -i :8888
# Kill if needed
kill -9 PID

# Or use different port
python3 tests/mock_slack_server.py --port 9999
```

## Test Validation Checklist

Before release, ensure:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All system tests pass
- [ ] Mock server tests complete
- [ ] Manual installation tested
- [ ] Commands work correctly
- [ ] Hooks execute properly
- [ ] Cross-platform verified
- [ ] Coverage > 80%
- [ ] No hardcoded test values

---

**Testing Status**: Complete test suite with ~80% coverage
**Last Updated**: 2025-09-29