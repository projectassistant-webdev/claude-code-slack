# Troubleshooting Guide

Comprehensive troubleshooting guide for common issues with Claude Code Slack Integration.

## Table of Contents
- [Quick Diagnosis](#quick-diagnosis)
- [Common Issues](#common-issues)
- [Installation Problems](#installation-problems)
- [Webhook Issues](#webhook-issues)
- [Notification Problems](#notification-problems)
- [Command Errors](#command-errors)
- [Hook Failures](#hook-failures)
- [Debug Tools](#debug-tools)
- [Getting Help](#getting-help)

## Quick Diagnosis

Run this diagnostic script to identify common issues:

```bash
# Check installation and configuration
/user:slack:status

# Test webhook connectivity
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Diagnostic test from Claude Code"}' \
  $(cat .claude/slack-state.json | grep webhook_url | cut -d'"' -f4)

# Verify Python environment
python3 -c "from commands.slack import slack_utils; print('✓ Modules OK')"

# Check hook registration
cat .claude/settings.json | grep -c "slack"
```

## Common Issues

### Issue: No Notifications Received

**Symptoms**: Commands work but no Slack messages appear

**Diagnosis**:
```bash
# 1. Check if integration is enabled
cat .claude/slack-state.json | grep enabled

# 2. Test webhook directly
curl -X POST YOUR_WEBHOOK_URL \
  -H 'Content-type: application/json' \
  -d '{"text":"Direct test"}'

# 3. Check hook execution
export SLACK_DEBUG=1
# Then trigger a Claude Code action
```

**Solutions**:

1. **Verify webhook URL is correct**:
```bash
/user:slack:setup https://hooks.slack.com/services/CORRECT/URL/HERE
```

2. **Enable notifications**:
```bash
/user:slack:start
```

3. **Check Slack channel**:
- Ensure the webhook's channel still exists
- Verify bot has permission to post
- Check if messages are in thread/collapsed

4. **Test with dry run disabled**:
```bash
export SLACK_DRY_RUN=0
```

### Issue: "Command not found: /user:slack:setup"

**Symptoms**: Slash commands don't work

**Diagnosis**:
```bash
# Check if commands are registered
cat .claude/settings.json | grep -A 5 "user:slack"

# Verify command files exist
ls -la .claude/commands/slack/
```

**Solutions**:

1. **Re-run installation**:
```bash
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash
```

2. **Manual command registration** - Add to `.claude/settings.json`:
```json
{
  "commands": {
    "user:slack:setup": {
      "type": "python",
      "module": "commands.slack.setup_handler"
    }
  }
}
```

3. **Check Python path**:
```bash
export PYTHONPATH="$PYTHONPATH:$(pwd)/.claude"
```

### Issue: "Invalid webhook URL"

**Symptoms**: Setup command rejects your webhook URL

**Diagnosis**:
```bash
# Check URL format
echo "YOUR_WEBHOOK_URL" | grep -E "https://hooks\.slack\.com/(services|workflows)/"
```

**Solutions**:

1. **Verify URL format** - Valid formats:
   - Incoming: `https://hooks.slack.com/services/T.../B.../...`
   - Workflow: `https://hooks.slack.com/workflows/T.../A.../.../.../...`

2. **Remove extra characters**:
```bash
# Remove quotes, spaces, or newlines
/user:slack:setup "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
# Not: /user:slack:setup 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX'
```

3. **Check for URL encoding issues**:
```bash
# Decode if needed
python3 -c "import urllib.parse; print(urllib.parse.unquote('YOUR_URL'))"
```

## Installation Problems

### Permission Denied

**Error**: `bash: ./install.sh: Permission denied`

**Solution**:
```bash
chmod +x install.sh
./install.sh
```

### Python Not Found

**Error**: `/usr/bin/env: 'python3': No such file or directory`

**Solutions**:

1. **Install Python 3**:
```bash
# macOS
brew install python3

# Ubuntu/Debian
sudo apt install python3

# RHEL/CentOS
sudo yum install python3
```

2. **Create Python symlink**:
```bash
# Find Python location
which python
which python3

# Create symlink if needed
sudo ln -s /usr/bin/python /usr/bin/python3
```

3. **Use specific Python path** in `.claude/settings.json`:
```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "/usr/bin/python3.11 $CLAUDE_PROJECT_DIR/.claude/hooks/stop-slack.py"
      }]
    }]
  }
}
```

### Directory Not Found

**Error**: `mkdir: cannot create directory '.claude': File exists`

**Solution**:
```bash
# Check what exists
ls -la .claude

# If it's a file, not directory
rm .claude
mkdir .claude

# Re-run installation
./install.sh
```

## Webhook Issues

### 404 Not Found

**Error**: Webhook returns 404

**Causes & Solutions**:

1. **Webhook deleted in Slack**:
   - Create new webhook in Slack
   - Update configuration: `/user:slack:setup NEW_WEBHOOK_URL`

2. **Wrong workspace**:
   - Verify you're in correct Slack workspace
   - Check webhook URL workspace ID (T... part)

### 403 Forbidden

**Error**: Webhook returns 403

**Solutions**:

1. **App not installed**:
   - Reinstall app to workspace in Slack settings
   - Generate new webhook URL

2. **Permissions revoked**:
   - Re-authorize app in Slack admin settings

### Rate Limiting (429)

**Error**: Too many requests

**Solutions**:

1. **Reduce notification frequency**:
```json
// .claude/slack-state.json
{
  "notifications": {
    "work_in_progress": false  // Disable progress updates
  }
}
```

2. **Add filtering**:
```json
{
  "filters": {
    "tools": ["Write", "Edit"],  // Only notify for file changes
    "min_duration": 60  // Only sessions > 1 minute
  }
}
```

## Notification Problems

### Partial Notifications

**Symptoms**: Only some events trigger notifications

**Diagnosis**:
```bash
# Check which notifications are enabled
cat .claude/slack-state.json | python3 -m json.tool | grep -A 3 notifications
```

**Solution**:
```json
// Enable all notifications in .claude/slack-state.json
{
  "notifications": {
    "session_complete": true,
    "input_needed": true,
    "work_in_progress": true
  }
}
```

### Duplicate Notifications

**Symptoms**: Same event sends multiple messages

**Causes & Solutions**:

1. **Multiple installations**:
```bash
# Check for duplicate hooks
cat .claude/settings.json | grep -c "slack"
cat ~/.claude/settings.json | grep -c "slack"  # If global
```

2. **Remove duplicates**:
```bash
/user:slack:remove
# Then reinstall
./install.sh
```

### Delayed Notifications

**Symptoms**: Notifications arrive late

**Solutions**:

1. **Increase timeout**:
```python
# In hook scripts
response = requests.post(webhook_url, json=payload, timeout=10)
```

2. **Check network**:
```bash
# Test latency to Slack
ping -c 5 hooks.slack.com
```

## Command Errors

### ModuleNotFoundError

**Error**: `ModuleNotFoundError: No module named 'commands.slack'`

**Solutions**:

1. **Fix Python path**:
```bash
export PYTHONPATH="$PYTHONPATH:$(pwd)/.claude"
```

2. **Check file structure**:
```bash
tree .claude/commands/
# Should show:
# .claude/commands/
# └── slack/
#     ├── __init__.py
#     ├── slack_utils.py
#     └── ...
```

3. **Create missing __init__.py**:
```bash
touch .claude/commands/__init__.py
touch .claude/commands/slack/__init__.py
```

### JSONDecodeError

**Error**: `json.decoder.JSONDecodeError`

**Solutions**:

1. **Fix corrupted config**:
```bash
# Backup corrupted file
mv .claude/slack-state.json .claude/slack-state.json.corrupt

# Recreate
/user:slack:setup YOUR_WEBHOOK_URL
```

2. **Validate JSON**:
```bash
python3 -m json.tool < .claude/slack-state.json
```

## Hook Failures

### Hook Exit Code 1

**Symptoms**: Hooks execute but return error

**Diagnosis**:
```bash
# Test hook directly
echo '{"session_id":"test","transcript_path":"/tmp/test.md"}' | \
  python3 .claude/hooks/stop-slack.py

# Check error output
export SLACK_DEBUG=1
# Trigger hook again
```

**Solutions**:

1. **Missing configuration**:
```bash
# Ensure config exists
ls -la .claude/slack-state.json

# Create if missing
/user:slack:setup YOUR_WEBHOOK
```

2. **Invalid JSON input**:
```python
# Add error handling in hooks
try:
    event_data = json.loads(input_json)
except json.JSONDecodeError:
    print(f"Invalid JSON: {input_json}", file=sys.stderr)
    sys.exit(2)
```

### Hook Timeout

**Symptoms**: Claude Code hangs waiting for hook

**Solutions**:

1. **Add timeout to requests**:
```python
response = requests.post(url, json=data, timeout=5)
```

2. **Use async mode**:
```python
# Return immediately, send notification async
import threading
threading.Thread(target=send_notification, args=(data,)).start()
sys.exit(0)  # Don't wait
```

## Debug Tools

### Enable Debug Mode

```bash
# Environment variable
export SLACK_DEBUG=1

# Or in Python
import os
os.environ['SLACK_DEBUG'] = '1'
```

### Debug Output Script

Create `debug_slack.py`:

```python
#!/usr/bin/env python3
import json
import sys
import os
from pathlib import Path

def diagnose():
    results = {}

    # Check installation
    claude_dir = Path(".claude")
    results['installation'] = {
        'exists': claude_dir.exists(),
        'hooks': list(claude_dir.glob("hooks/*slack*")),
        'commands': list(claude_dir.glob("commands/slack/*.py"))
    }

    # Check configuration
    config_file = claude_dir / "slack-state.json"
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
            results['config'] = {
                'enabled': config.get('enabled'),
                'has_webhook': bool(config.get('webhook_url')),
                'notifications': config.get('notifications', {})
            }

    # Check Python
    results['python'] = {
        'version': sys.version,
        'path': sys.executable
    }

    # Check environment
    results['environment'] = {
        'CLAUDE_PROJECT_DIR': os.getenv('CLAUDE_PROJECT_DIR'),
        'SLACK_DEBUG': os.getenv('SLACK_DEBUG'),
        'PYTHONPATH': os.getenv('PYTHONPATH')
    }

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    diagnose()
```

Run diagnosis:
```bash
python3 debug_slack.py
```

### Network Testing

Test Slack connectivity:

```bash
# Test DNS
nslookup hooks.slack.com

# Test HTTPS
openssl s_client -connect hooks.slack.com:443 < /dev/null

# Test webhook
time curl -X POST YOUR_WEBHOOK_URL \
  -H 'Content-type: application/json' \
  -d '{"text":"Network test"}' \
  -w "\n\nTime: %{time_total}s\nHTTP Code: %{http_code}\n"
```

### Log Analysis

Check Claude Code logs:

```bash
# Find error messages
grep -r "ERROR\|error\|Error" .claude/logs/

# Check hook execution
grep -A 5 -B 5 "slack" ~/.claude/logs/session.log

# Monitor in real-time
tail -f ~/.claude/logs/session.log | grep slack
```

## Getting Help

### Self-Help Resources

1. **Check documentation**:
   - [README.md](../README.md)
   - [Configuration Guide](CONFIGURATION.md)
   - [Installation Guide](INSTALLATION.md)

2. **Search issues**:
   - GitHub Issues: `https://github.com/projectassistant-webdev/claude-code-slack/issues`

3. **Community forums**:
   - Claude Code Discord
   - Anthropic Developer Forum

### Reporting Issues

When reporting issues, include:

1. **System information**:
```bash
echo "OS: $(uname -a)"
echo "Python: $(python3 --version)"
echo "Claude: $(claude --version)"
echo "Slack Integration: $(cat .claude/slack-state.json | grep version)"
```

2. **Error messages**:
```bash
# Full error output
/user:slack:status 2>&1 | tee error.log
```

3. **Configuration** (remove sensitive data):
```bash
cat .claude/slack-state.json | sed 's/webhook_url":.*/webhook_url": "REDACTED",/'
```

4. **Debug output**:
```bash
export SLACK_DEBUG=1
# Reproduce issue
# Copy output
```

### Emergency Recovery

If everything is broken:

```bash
# 1. Backup current state
tar -czf claude-slack-backup.tar.gz .claude/

# 2. Remove Slack integration
rm -rf .claude/hooks/*slack*
rm -rf .claude/commands/slack
rm -f .claude/slack-state.json

# 3. Clean settings.json
cp .claude/settings.json .claude/settings.json.backup
# Manually remove Slack-related entries

# 4. Reinstall fresh
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash

# 5. Reconfigure
/user:slack:setup YOUR_WEBHOOK_URL
/user:slack:start
```

## Frequently Asked Questions

### Q: Can I use multiple webhooks?
**A**: Not directly, but you can modify hooks to route to different webhooks based on conditions.

### Q: Why do notifications stop after a while?
**A**: Check if the webhook expired or was rate limited. Webhooks don't expire, but apps can be uninstalled.

### Q: Can I test without sending to Slack?
**A**: Yes, use dry run mode:
```bash
export SLACK_DRY_RUN=1
```

### Q: How do I completely disable notifications temporarily?
**A**: Use the stop command:
```bash
/user:slack:stop
```

### Q: Why do hooks work manually but not in Claude Code?
**A**: Usually a path or environment issue. Check that `CLAUDE_PROJECT_DIR` is set correctly.

---

**Still having issues?** Open a GitHub issue with your diagnostic information.