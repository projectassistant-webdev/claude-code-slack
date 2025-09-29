# Configuration Guide

Complete guide for configuring the Claude Code Slack Integration, including webhook setup, notification customization, and advanced settings.

## Table of Contents
- [Quick Setup](#quick-setup)
- [Slack Webhook Configuration](#slack-webhook-configuration)
- [Notification Settings](#notification-settings)
- [Advanced Configuration](#advanced-configuration)
- [Multi-Project Setup](#multi-project-setup)
- [Environment Variables](#environment-variables)
- [Configuration File Reference](#configuration-file-reference)

## Quick Setup

The fastest way to get started:

```bash
# 1. Setup your webhook URL
/user:slack:setup https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX

# 2. Enable notifications
/user:slack:start

# 3. Verify configuration
/user:slack:status
```

## Slack Webhook Configuration

### Creating a Slack Webhook

#### Option 1: Incoming Webhooks (Recommended for Simple Use)

1. **Create a Slack App**:
   - Go to [api.slack.com/apps](https://api.slack.com/apps)
   - Click "Create New App"
   - Choose "From scratch"
   - Name your app (e.g., "Claude Code Notifications")
   - Select your workspace

2. **Enable Incoming Webhooks**:
   - In your app settings, click "Incoming Webhooks"
   - Toggle "Activate Incoming Webhooks" to ON
   - Click "Add New Webhook to Workspace"
   - Choose the channel for notifications
   - Click "Allow"

3. **Copy Your Webhook URL**:
   - You'll see a URL like: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX`
   - Copy this URL for configuration

#### Option 2: Workflow Webhooks (For Advanced Automation)

1. **Create a Workflow**:
   - In Slack, go to Tools → Workflow Builder
   - Click "Create" → "From scratch"
   - Name your workflow

2. **Add Webhook Trigger**:
   - Choose "Webhook" as the trigger
   - Configure any variables you want to receive

3. **Add Message Step**:
   - Add a "Send a message" step
   - Configure the message format
   - Use variables from the webhook

4. **Get Webhook URL**:
   - Publish the workflow
   - Copy the webhook URL (format: `https://hooks.slack.com/workflows/T00000000/A00000000/000000000000000/XXXXXXXXXXXXXXXXXXXX`)

### Configuring Your Webhook

#### Using Commands (Recommended)

```bash
# Basic setup
/user:slack:setup https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Verify webhook is saved
/user:slack:status
```

#### Manual Configuration

Edit `.claude/slack-state.json`:

```json
{
  "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
  "enabled": true,
  "installation_type": "local",
  "notifications": {
    "session_complete": true,
    "input_needed": true,
    "work_in_progress": true
  }
}
```

### Testing Your Webhook

Test that your webhook is working:

```bash
# Using curl
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test message from Claude Code"}' \
  YOUR_WEBHOOK_URL

# Using the integration
/user:slack:start
# Then trigger any Claude Code action
```

## Notification Settings

### Notification Types

Configure which notifications you receive:

| Type | Event | Default | Description |
|------|-------|---------|-------------|
| `session_complete` | Stop hook | ✅ Enabled | When Claude finishes responding |
| `input_needed` | Notification hook | ✅ Enabled | When Claude needs user input |
| `work_in_progress` | PostToolUse hook | ✅ Enabled | After tool execution |

### Customizing Notifications

#### Enable/Disable Specific Notifications

Edit `.claude/slack-state.json`:

```json
{
  "webhook_url": "your-webhook-url",
  "enabled": true,
  "notifications": {
    "session_complete": true,
    "input_needed": true,
    "work_in_progress": false  // Disable progress updates
  }
}
```

#### Filtering Tool Notifications

For PostToolUse events, you can filter by tool type in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit|MultiEdit",  // Only for file changes
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/posttooluse-slack.py"
      }]
    }]
  }
}
```

Common matchers:
- `"*"` - All tools (default)
- `"Write|Edit"` - File modifications only
- `"Bash"` - Command executions only
- `"Read|Grep|Glob"` - File reading operations

### Message Customization

#### Custom Message Formats

While the integration uses Block Kit by default, you can customize messages by modifying the hook scripts.

Example customization in `hooks/stop-slack.py`:

```python
# Add custom fields to the message
custom_blocks = [
    {
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f"*Project:* {project_name}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Duration:* {session_duration}"
            }
        ]
    }
]
```

## Advanced Configuration

### Multiple Slack Channels

Send different notifications to different channels using multiple webhooks:

1. **Create multiple workflows** in Slack
2. **Configure conditional routing** in hooks:

```python
# In hook scripts
def get_webhook_for_event(event_type):
    webhooks = {
        "critical": "https://hooks.slack.com/services/CRITICAL",
        "info": "https://hooks.slack.com/services/INFO"
    }
    return webhooks.get(event_type, webhooks["info"])
```

### Rate Limiting Configuration

Configure rate limiting behavior in `commands/slack/slack_utils.py`:

```python
# Default configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
MAX_BACKOFF = 60     # seconds
BACKOFF_MULTIPLIER = 2
```

### Timeout Settings

Adjust webhook timeout in the hook scripts:

```python
# In send_webhook() function
response = requests.post(
    webhook_url,
    json=payload,
    timeout=10  # Increase from default 5 seconds
)
```

### Debug Mode

Enable debug output for troubleshooting:

```bash
# Set environment variable
export SLACK_DEBUG=1

# Or in slack-state.json
{
  "debug": true,
  "webhook_url": "...",
  "enabled": true
}
```

## Multi-Project Setup

### Scenario 1: Different Webhooks per Project

With local installation (recommended):

```bash
# Project A - Development notifications
cd /path/to/project-a
/user:slack:setup https://hooks.slack.com/services/DEV_WEBHOOK

# Project B - Production monitoring
cd /path/to/project-b
/user:slack:setup https://hooks.slack.com/services/PROD_WEBHOOK
```

### Scenario 2: Shared Webhook, Different Settings

```bash
# Global installation
~/.claude/slack-state.json  # Shared webhook

# Per-project overrides
/project-a/.claude/slack-override.json
/project-b/.claude/slack-override.json
```

Override file example:
```json
{
  "notifications": {
    "work_in_progress": false  // Project-specific setting
  }
}
```

### Scenario 3: Team Collaboration

For teams, commit configuration templates:

1. **Create template**: `.claude/slack-state.template.json`
```json
{
  "webhook_url": "REPLACE_WITH_YOUR_WEBHOOK",
  "enabled": false,
  "notifications": {
    "session_complete": true,
    "input_needed": true,
    "work_in_progress": false
  }
}
```

2. **Add to version control**:
```bash
git add .claude/slack-state.template.json
git commit -m "Add Slack configuration template"
```

3. **Team members configure**:
```bash
cp .claude/slack-state.template.json .claude/slack-state.json
/user:slack:setup THEIR_WEBHOOK_URL
```

## Environment Variables

The integration supports several environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_PROJECT_DIR` | Project directory path | Current directory |
| `SLACK_WEBHOOK_URL` | Override webhook URL | From config file |
| `SLACK_DRY_RUN` | Test mode (no sends) | `0` (disabled) |
| `SLACK_DEBUG` | Enable debug output | `0` (disabled) |
| `SLACK_CONFIG_PATH` | Custom config location | `.claude/slack-state.json` |
| `SLACK_TIMEOUT` | Webhook timeout (seconds) | `5` |

### Using Environment Variables

```bash
# Override webhook for testing
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/TEST"

# Enable dry run mode
export SLACK_DRY_RUN=1

# Custom config path
export SLACK_CONFIG_PATH="/etc/claude/slack.json"
```

## Configuration File Reference

### Complete slack-state.json Structure

```json
{
  "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
  "enabled": true,
  "installation_type": "local",
  "installation_path": "/home/user/project/.claude",
  "created_at": "2025-09-29T12:00:00Z",
  "updated_at": "2025-09-29T12:00:00Z",
  "notifications": {
    "session_complete": true,
    "input_needed": true,
    "work_in_progress": true
  },
  "filters": {
    "tools": ["*"],
    "min_duration": 0,
    "max_notifications_per_hour": 100
  },
  "formatting": {
    "use_blocks": true,
    "include_timestamp": true,
    "include_project_path": true,
    "include_session_id": true
  },
  "advanced": {
    "retry_enabled": true,
    "max_retries": 3,
    "timeout": 5,
    "debug": false
  }
}
```

### Field Descriptions

#### Root Fields
- `webhook_url`: Your Slack webhook URL (required)
- `enabled`: Master on/off switch for all notifications
- `installation_type`: Either "local" or "global"
- `installation_path`: Path to Claude installation
- `created_at`: ISO timestamp of initial setup
- `updated_at`: ISO timestamp of last modification

#### Notifications Object
- `session_complete`: Enable Stop hook notifications
- `input_needed`: Enable Notification hook notifications
- `work_in_progress`: Enable PostToolUse notifications

#### Filters Object (Optional)
- `tools`: Array of tool names to notify about (["*"] for all)
- `min_duration`: Minimum session duration for notifications (seconds)
- `max_notifications_per_hour`: Rate limiting per hour

#### Formatting Object (Optional)
- `use_blocks`: Use Block Kit formatting (vs plain text)
- `include_timestamp`: Add timestamp to messages
- `include_project_path`: Show project path in messages
- `include_session_id`: Include session ID in messages

#### Advanced Object (Optional)
- `retry_enabled`: Enable automatic retry on failure
- `max_retries`: Maximum retry attempts
- `timeout`: Request timeout in seconds
- `debug`: Enable debug logging

## Best Practices

### Security
1. **Never commit webhook URLs** to version control
2. **Use .gitignore** for slack-state.json
3. **Rotate webhooks** periodically
4. **Use environment variables** for CI/CD

### Performance
1. **Disable work_in_progress** for large projects to reduce noise
2. **Set reasonable timeouts** (5-10 seconds)
3. **Use filters** to limit notifications to important events

### Organization
1. **Use descriptive webhook names** in Slack
2. **Create separate webhooks** for dev/staging/prod
3. **Document webhook purposes** in team wikis
4. **Regular cleanup** of unused webhooks

## Validation

### Verify Configuration

```bash
# Check current configuration
/user:slack:status

# Test webhook manually
python3 -c "
import json, requests
webhook = 'YOUR_WEBHOOK_URL'
payload = {'text': 'Test from Claude Code'}
response = requests.post(webhook, json=payload)
print(f'Status: {response.status_code}')
"

# Verify hook registration
cat .claude/settings.json | python3 -m json.tool | grep -A 10 hooks
```

### Common Configuration Issues

| Issue | Solution |
|-------|----------|
| "Webhook URL invalid" | Check URL format matches Slack patterns |
| "Notifications not received" | Verify `enabled: true` in config |
| "Partial notifications" | Check individual notification settings |
| "Rate limited" | Reduce notification frequency or add filtering |

## Migration

### From Other Notification Systems

If migrating from another notification system:

1. **Backup existing configuration**:
```bash
cp -r .claude .claude.backup
```

2. **Install Slack integration**:
```bash
./install.sh
```

3. **Merge configurations** if needed:
```bash
# The installer preserves existing hooks
# Just add your webhook
/user:slack:setup YOUR_WEBHOOK
```

### Upgrading Configuration

When upgrading to a new version:

1. **Backup current config**:
```bash
cp .claude/slack-state.json .claude/slack-state.backup.json
```

2. **Run upgrade**:
```bash
./install.sh --upgrade
```

3. **Verify settings**:
```bash
/user:slack:status
```

---

**Next Steps**: After configuration, see [Troubleshooting Guide](TROUBLESHOOTING.md) for common issues and solutions.