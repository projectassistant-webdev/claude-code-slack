# Claude Code Slack Integration Tests

This directory contains comprehensive integration tests for the three Claude Code Slack hook scripts.

## Test Files Created

### 1. `test_stop_hook.py` (617 lines)
Tests for the Stop hook functionality including:

- **test_stop_hook_with_valid_input()** - Valid JSON input, successful notification
- **test_stop_hook_with_empty_transcript()** - Handle empty session
- **test_stop_hook_when_already_active()** - Skip when stop_hook_active is true
- **test_stop_hook_webhook_failure()** - Handle webhook send failure
- **test_stop_hook_exit_codes()** - Verify correct exit codes
- **test_stop_hook_missing_config()** - Handle missing configuration
- **test_stop_hook_malformed_json_input()** - Handle invalid JSON input
- **test_stop_hook_transcript_parsing()** - Parse transcript for session summary

### 2. `test_notification_hook.py` (615 lines)
Tests for the Notification hook including:

- **test_notification_hook_permission_request()** - Permission needed message
- **test_notification_hook_idle_waiting()** - Idle waiting message
- **test_notification_hook_custom_message()** - Custom notification
- **test_notification_hook_missing_config()** - No configuration, silent exit
- **test_notification_hook_malformed_input()** - Invalid JSON input
- **test_notification_hook_webhook_failure()** - Handle webhook failures
- **test_notification_hook_disabled_integration()** - Disabled integration handling
- **test_notification_message_types_classification()** - Message type classification
- **test_notification_hook_large_message()** - Large message handling

### 3. `test_posttooluse_hook.py` (825 lines)
Tests for the PostToolUse hook including:

- **test_posttooluse_write_tool()** - Write tool notification
- **test_posttooluse_edit_tool()** - Edit tool notification
- **test_posttooluse_bash_tool()** - Bash command notification
- **test_posttooluse_aggregation()** - Multiple tools aggregated
- **test_posttooluse_filtering()** - Tool filtering by matcher
- **test_posttooluse_failed_tool()** - Failed tool operation handling
- **test_posttooluse_missing_config()** - Missing configuration handling
- **test_posttooluse_malformed_input()** - Invalid JSON input handling
- **test_posttooluse_tool_description_generation()** - Tool-specific descriptions
- **test_posttooluse_rate_limiting()** - Rate limiting to avoid spam

## Test Design Principles

### JSON Input Simulation
Each test simulates the JSON input that Claude Code hooks receive via stdin:

```json
{
  "session_id": "abc123",
  "transcript_path": "~/.claude/projects/.../session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "Stop|Notification|PostToolUse",
  // event-specific fields
}
```

### Exit Code Verification
Tests verify the hooks return correct exit codes:
- **Exit Code 0**: Success - Notification sent successfully
- **Exit Code 2**: Block - Shows stderr to Claude for processing (Stop hook only)
- **Other Exit Codes**: Non-blocking error - Shows stderr to user

### Mock Infrastructure
All tests use comprehensive mocking for:
- **stdin JSON input** - Simulated with test data
- **Slack webhook requests** - Mocked with `requests.post`
- **Configuration loading** - Mocked `.claude/slack-config.json`
- **Environment variables** - `CLAUDE_PROJECT_DIR` simulation
- **slack_utils module** - Complete mock implementation

### Slack Block Kit Validation
Tests verify Slack message formatting:
- Block structure conforms to Slack Block Kit specification
- Text content is properly escaped and formatted
- Message length is within Slack limits
- Appropriate emojis and formatting for different notification types

## Expected Behavior

### Configuration Loading
All hooks should:
1. Check for `.claude/slack-config.json` configuration file
2. Exit silently (code 0) if no configuration exists
3. Respect the `enabled` flag in configuration
4. Use project-specific settings when available

### Slack Message Formatting
Different hook types create different message formats:

#### Stop Hook Messages
```
🎯 Claude Code Session Complete
Session ID: abc123...
Project: /path/to/project
Summary: Tools used: 5, Files modified: 3
```

#### Notification Hook Messages
```
⚠️ Permission Required
Claude needs your permission to use Bash
Session: abc123...
```

```
⏳ Waiting for Input
Claude is waiting for your input (idle for 60+ seconds)
Session: abc123...
```

#### PostToolUse Hook Messages
```
📝 File Created
Created: main.py
Session: abc123...
Tool: Write
```

```
⚡ Command Executed
Ran: npm test ✅
Session: abc123...
Exit Code: 0
```

## Running the Tests

These tests are designed to **fail initially** since the actual hook scripts don't exist yet. This follows Test-Driven Development (TDD) principles.

To run the integration tests:

```bash
# Run all integration tests
python -m pytest tests/integration/ -v

# Run specific hook tests
python -m pytest tests/integration/test_stop_hook.py -v
python -m pytest tests/integration/test_notification_hook.py -v
python -m pytest tests/integration/test_posttooluse_hook.py -v

# Run with coverage
python -m pytest tests/integration/ --cov=hooks --cov-report=html
```

## Dependencies

The tests require:
- `pytest` - Test framework
- `requests` - HTTP library (mocked)
- `unittest.mock` - Mocking framework (built-in)

## Implementation Notes

1. **Hook Scripts Location**: Tests expect hook scripts to be in:
   - `hooks/stop-slack.py`
   - `hooks/notification-slack.py`
   - `hooks/posttooluse-slack.py`

2. **Configuration File**: Tests expect configuration at:
   - `.claude/slack-config.json`

3. **Environment Variables**: Tests simulate:
   - `CLAUDE_PROJECT_DIR` - Project root directory

4. **Slack Utils Module**: Tests expect a `slack_utils` module with functions:
   - `send_webhook(url, payload)`
   - `create_session_complete_message(...)`
   - `create_notification_message(...)`
   - `create_posttooluse_message(...)`
   - `load_config()`

## Security Considerations

Tests verify that the hooks:
- Validate and sanitize all input data
- Handle malformed JSON gracefully
- Protect against path traversal attacks
- Mask sensitive information in logs
- Implement proper error handling

These comprehensive tests ensure the Slack integration hooks will be robust, secure, and reliable when implemented.