# Development Guide

Guide for developers who want to contribute to or extend the Claude Code Slack Integration.

## Table of Contents
- [Development Setup](#development-setup)
- [Architecture Overview](#architecture-overview)
- [Code Structure](#code-structure)
- [Testing](#testing)
- [Adding Features](#adding-features)
- [Hook Development](#hook-development)
- [Command Development](#command-development)
- [Contributing](#contributing)

## Development Setup

### Prerequisites

- Python 3.6+ with development headers
- Git
- Claude Code (for integration testing)
- Slack workspace with admin access (for webhook testing)

### Setting Up Development Environment

1. **Clone the repository**:
```bash
git clone https://github.com/projectassistant-webdev/claude-code-slack.git
cd claude-code-slack
```

2. **Create development branch**:
```bash
git checkout -b feature/your-feature-name
```

3. **Set up Python environment** (optional but recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. **Install development dependencies** (when available):
```bash
# Currently no external dependencies required
# Future: pip install -r requirements-dev.txt
```

5. **Configure test environment**:
```bash
export SLACK_DEBUG=1
export SLACK_DRY_RUN=1  # Prevent actual webhook sends during testing
```

## Architecture Overview

### System Architecture

```
┌─────────────────┐     JSON Events    ┌──────────────────┐
│                 │ ─────────────────> │                  │
│  Claude Code    │                    │   Hook Scripts   │
│                 │ <───────────────── │                  │
└─────────────────┘     Exit Codes     └──────────────────┘
        │                                       │
        │ Commands                              │ HTTP POST
        ▼                                       ▼
┌─────────────────┐                    ┌──────────────────┐
│ Command Handlers│                    │  Slack Webhook   │
│                 │ ─────────────────> │                  │
└─────────────────┘    HTTP POST       └──────────────────┘
```

### Component Interaction

1. **Claude Code** triggers events (Stop, Notification, PostToolUse)
2. **Hook Scripts** receive JSON via stdin, process events
3. **Slack Utils** provides common functionality
4. **Command Handlers** process user slash commands
5. **Slack Webhook** receives formatted messages

### Key Design Principles

- **No external dependencies**: Pure Python standard library
- **Local-first**: All data stored locally
- **Non-destructive**: Preserves existing Claude Code configuration
- **Fail-safe**: Errors don't break Claude Code operation
- **Extensible**: Easy to add new notification types or commands

## Code Structure

### Directory Layout

```
claude-code-slack/
├── commands/
│   └── slack/
│       ├── __init__.py           # Package initialization
│       ├── slack_utils.py        # Core utility functions
│       ├── setup_handler.py      # /user:slack:setup
│       ├── start_handler.py      # /user:slack:start
│       ├── stop_handler.py       # /user:slack:stop
│       ├── status_handler.py     # /user:slack:status
│       └── remove_handler.py     # /user:slack:remove
├── hooks/
│   ├── stop-slack.py            # Session complete hook
│   ├── notification-slack.py    # Input needed hook
│   └── posttooluse-slack.py    # Tool usage hook
├── tests/
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   ├── system/                  # System tests
│   └── run_tests.py            # Test runner
├── docs/                        # Documentation
├── install.sh                   # Installation script
├── uninstall.sh                # Uninstallation script
└── README.md                    # User documentation
```

### Core Modules

#### slack_utils.py

Central module containing shared functionality:

```python
# Key functions
validate_webhook_url(url)      # Validate Slack webhook URL
format_block_kit_message(...)  # Create Block Kit messages
send_webhook(url, payload)     # Send to Slack with retry logic
load_configuration(path)       # Load config file
save_configuration(config, path) # Save config file
```

#### Hook Scripts

Each hook follows this pattern:

```python
#!/usr/bin/env python3

import sys
import json
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from commands.slack import slack_utils

def main():
    # 1. Read JSON from stdin
    input_json = sys.stdin.read()
    event_data = json.loads(input_json)

    # 2. Load configuration
    config = slack_utils.load_configuration()

    # 3. Check if enabled
    if not config.get('enabled'):
        sys.exit(0)

    # 4. Format message
    message = format_message(event_data)

    # 5. Send to Slack
    slack_utils.send_webhook(config['webhook_url'], message)

    sys.exit(0)
```

#### Command Handlers

Command handlers follow this pattern:

```python
#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from commands.slack import slack_utils

def handle(args):
    """Main command handler."""
    # 1. Parse arguments
    # 2. Validate input
    # 3. Perform action
    # 4. Return response

if __name__ == "__main__":
    handle(sys.argv[1:])
```

## Testing

### Test Structure

```
tests/
├── unit/                     # Test individual functions
│   ├── test_url_validation.py
│   ├── test_webhook_formatting.py
│   └── test_configuration.py
├── integration/              # Test component interaction
│   ├── test_stop_hook.py
│   ├── test_notification_hook.py
│   └── test_posttooluse_hook.py
├── system/                   # Test complete workflows
│   ├── test_installation_flow.py
│   └── test_e2e_workflow.py
└── fixtures/                 # Test data and mocks
```

### Running Tests

#### All Tests
```bash
python3 tests/run_tests.py
```

#### Specific Test Category
```bash
python3 tests/run_tests.py unit
python3 tests/run_tests.py integration
python3 tests/run_tests.py system
```

#### Individual Test File
```bash
python3 tests/unit/test_url_validation.py
```

### Mock Slack Server

For integration testing without sending real webhooks:

```bash
# Start mock server
python3 tests/mock_slack_server.py --background

# Run tests
python3 tests/test_slack_integration.py

# Check received webhooks
cat /tmp/slack-integration-agents/phase3/validation2/webhook_logs.json
```

### Writing Tests

Example unit test:

```python
import unittest
from commands.slack import slack_utils

class TestWebhookValidation(unittest.TestCase):
    def test_valid_incoming_webhook(self):
        url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
        self.assertTrue(slack_utils.validate_webhook_url(url))

    def test_invalid_webhook(self):
        url = "https://example.com/webhook"
        self.assertFalse(slack_utils.is_valid_webhook_url(url))
```

### Test Coverage

Target: 80% code coverage

Check coverage:
```bash
# If pytest and coverage are available
pytest tests/ --cov=commands --cov=hooks --cov-report=html

# Manual verification
python3 tests/run_tests.py --verbose
```

## Adding Features

### Adding a New Notification Type

1. **Create new hook script** in `hooks/`:
```python
# hooks/custom-slack.py
#!/usr/bin/env python3

import sys
import json
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from commands.slack import slack_utils

def main():
    event_data = json.loads(sys.stdin.read())
    # Custom processing
    message = create_custom_message(event_data)
    config = slack_utils.load_configuration()
    slack_utils.send_webhook(config['webhook_url'], message)

if __name__ == "__main__":
    main()
```

2. **Register in settings.json**:
```json
{
  "hooks": {
    "CustomEvent": [{
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/custom-slack.py"
      }]
    }]
  }
}
```

3. **Add tests**:
```python
# tests/integration/test_custom_hook.py
```

### Adding a New Command

1. **Create command handler**:
```python
# commands/slack/custom_handler.py
#!/usr/bin/env python3

import sys
from commands.slack import slack_utils

def handle(args):
    """Handle /user:slack:custom command."""
    # Implementation
    print("Custom command executed")
    return 0

if __name__ == "__main__":
    sys.exit(handle(sys.argv[1:]))
```

2. **Register command**:
```json
{
  "commands": {
    "user:slack:custom": {
      "type": "python",
      "module": "commands.slack.custom_handler"
    }
  }
}
```

3. **Update documentation**:
- Add to README.md command list
- Update CONFIGURATION.md if needed

### Adding Block Kit Components

Extend `slack_utils.py` with new formatting functions:

```python
def format_custom_block(data):
    """Create custom Block Kit component."""
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Custom*: {data}"
        },
        "accessory": {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "View Details"
            },
            "url": "https://example.com"
        }
    }
```

## Hook Development

### Hook Event Data

Each hook receives different JSON structure via stdin:

#### Stop Hook
```json
{
  "session_id": "abc-123",
  "transcript_path": "/path/to/transcript.md",
  "stop_hook_active": true
}
```

#### Notification Hook
```json
{
  "session_id": "abc-123",
  "transcript_path": "/path/to/transcript.md",
  "message": "User input needed"
}
```

#### PostToolUse Hook
```json
{
  "session_id": "abc-123",
  "transcript_path": "/path/to/transcript.md",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "main.py",
    "changes": "..."
  },
  "tool_response": "File updated successfully"
}
```

### Hook Best Practices

1. **Fast execution**: Hooks block Claude Code, keep them fast
2. **Error handling**: Always catch exceptions, exit cleanly
3. **Logging**: Use stderr for debug output
4. **Exit codes**:
   - 0: Success
   - 2: Cancel subsequent hooks
   - Other: Error (logged but doesn't stop Claude Code)

### Advanced Hook Control

Control Claude Code behavior with JSON output:

```python
# Cancel subsequent hooks
print(json.dumps({"cancel_remaining": True}))
sys.exit(2)

# Modify Claude's response (PreToolUse only)
print(json.dumps({
    "modified_input": {
        "file_path": "/safe/path.txt"
    }
}))
sys.exit(0)
```

## Command Development

### Command Arguments

Commands receive arguments via `sys.argv`:

```python
def handle(args):
    # args[0] = first argument after command name
    # /user:slack:setup WEBHOOK_URL
    # args[0] = "WEBHOOK_URL"

    if not args:
        print("Error: Missing required argument")
        return 1

    webhook_url = args[0]
    # Process...
```

### Command Output Format

Follow consistent formatting:

```python
def print_status(config):
    print("\n📊 Slack Integration Status")
    print("──────────────────────────")
    print(f"✅ Installation: {config['installation_type']}")
    print(f"{'✅' if config['enabled'] else '⚠️ '} Status: {'Active' if config['enabled'] else 'Disabled'}")
    print(f"📍 Webhook: {config['webhook_url'][:30]}...")
```

### Command State Management

Commands should:
1. Load current state
2. Validate changes
3. Apply changes atomically
4. Save state
5. Report results

```python
def enable_notifications():
    # 1. Load
    config = slack_utils.load_configuration()

    # 2. Validate
    if not config.get('webhook_url'):
        print("Error: No webhook configured")
        return 1

    # 3. Change
    config['enabled'] = True

    # 4. Save
    slack_utils.save_configuration(config)

    # 5. Report
    print("✅ Slack notifications enabled")
    return 0
```

## Contributing

### Development Workflow

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes**
4. **Add tests** for new functionality
5. **Run tests**: `python3 tests/run_tests.py`
6. **Commit changes**: `git commit -m 'Add amazing feature'`
7. **Push branch**: `git push origin feature/amazing-feature`
8. **Open Pull Request**

### Coding Standards

#### Python Style
- Follow PEP 8
- Use type hints where helpful
- Document all public functions
- Keep functions focused and small

#### Shell Scripts
- POSIX compliant
- Quote all variables
- Check command results
- Provide helpful error messages

### Documentation Standards

- Update README.md for user-facing changes
- Update relevant docs/ files
- Include docstrings in Python code
- Add comments for complex logic

### Testing Requirements

- Add unit tests for new functions
- Add integration tests for new hooks/commands
- Maintain 80% code coverage
- Test on multiple platforms if possible

### Commit Messages

Follow conventional commits:

```
feat: add thread support for notifications
fix: correct webhook URL validation regex
docs: update installation guide for WSL
test: add unit tests for new formatter
refactor: extract common webhook logic
```

### Pull Request Process

1. **Describe changes** clearly
2. **Link related issues**
3. **Include test results**
4. **Update documentation**
5. **Ensure CI passes** (when available)

### Release Process

1. **Update version** in relevant files
2. **Update CHANGELOG.md**
3. **Create release branch**: `release/v1.0.0`
4. **Test thoroughly**
5. **Merge to main**
6. **Tag release**: `git tag -a v1.0.0 -m "Release version 1.0.0"`
7. **Push tags**: `git push origin --tags`

## Security Considerations

### Webhook URL Protection
- Never log webhook URLs
- Exclude from version control
- Validate format before use
- Use HTTPS only

### Input Validation
- Validate all JSON input
- Sanitize user input
- Check file paths
- Limit payload sizes

### Error Handling
- Don't expose internal paths
- Log errors locally only
- Fail safely
- Return generic error messages

## Performance Optimization

### Hook Performance
- Minimize import time
- Cache configuration
- Use async where possible
- Implement timeouts

### Webhook Optimization
- Batch notifications when possible
- Implement exponential backoff
- Cache Block Kit templates
- Compress large payloads

## Debugging Tips

### Debug Mode
```bash
export SLACK_DEBUG=1
export SLACK_DRY_RUN=1
```

### Trace Execution
```bash
python3 -m trace -t hooks/stop-slack.py < test_input.json
```

### Profile Performance
```bash
python3 -m cProfile -s time hooks/stop-slack.py < test_input.json
```

### Memory Profiling
```bash
python3 -m memory_profiler hooks/stop-slack.py
```

---

**Questions?** Open an issue on GitHub or contact the maintainers.