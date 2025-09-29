# Claude Code Slack Integration

**Local-first Slack notifications for Claude Code sessions - stay informed about your coding progress**

Get real-time Slack notifications when Claude completes tasks, needs input, or makes progress on your projects. **Simple local installation** by default, with optional global setup for advanced multi-project workflows.

📖 **[Installation](docs/INSTALLATION.md)** | **[Configuration](docs/CONFIGURATION.md)** | **[Troubleshooting](docs/TROUBLESHOOTING.md)** | **[Development](docs/DEVELOPMENT.md)**

## ✨ Features

- 🏠 **Local-first architecture** - Self-contained installation per project
- 🌐 **Global option available** - Multi-project setup for advanced users
- 🎯 **Project-scoped notifications** - Each project controls its own Slack integration
- 🔔 **Smart notification types** - Input needed, work in progress, session complete
- 📊 **Rich Block Kit formatting** - Beautiful, structured messages in Slack
- ⚡ **Easy control** - Simple slash commands for setup and management
- 🛡️ **Non-destructive setup** - Preserves existing Claude Code configuration
- 🔧 **Configurable webhooks** - No hardcoded URLs, bring your own webhook
- 🐍 **Pure Python implementation** - No external dependencies required
- 🔄 **Automatic retry logic** - Handles rate limiting and temporary failures

## 🚀 Quick Install

### 🏠 Local Installation (Recommended)
Perfect for single projects - everything installs to your current project with automatic setup:

```bash
cd your-project
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash
```

**Automatic hook registration!** Slack hooks are automatically registered in `.claude/settings.json` during local installation.

### 🌐 Global Installation (Advanced)
For managing multiple projects with shared Slack integration:

```bash
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash -s -- --global
```

### 🔧 Manual Installation
```bash
git clone https://github.com/projectassistant-webdev/claude-code-slack.git
cd claude-code-slack
chmod +x install.sh
./install.sh              # Local installation
./install.sh --global     # Global installation
```

## 📋 Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed (global installation only)
- Python 3.6+ (universally available)
- `curl` or `wget` for installation
- Slack webhook URL (incoming webhooks or workflow webhooks)

## 🎯 Quick Start

### 1. Get Your Slack Webhook URL

#### Option A: Incoming Webhooks (Simple)
1. Go to [Slack App Directory](https://api.slack.com/apps)
2. Create a new app or select existing
3. Navigate to **Incoming Webhooks** → Enable
4. Add new webhook to workspace
5. Copy the webhook URL

#### Option B: Workflow Webhooks (Advanced)
1. Create a workflow in Slack Workflow Builder
2. Add "Webhook" as trigger
3. Configure message formatting
4. Copy the workflow webhook URL

### 2. Setup and Enable

After installation, configure Slack integration:

```bash
# Setup Slack integration
/user:slack:setup https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Enable notifications
/user:slack:start

# Check installation type
/user:slack:status
```

### 3. Stay Informed

You'll automatically receive Slack notifications when:
- 🔔 **Claude needs input** (yellow notifications)
- ⚡ **Claude makes progress** (blue notifications after tool usage)
- ✅ **Claude completes session** (green notifications)

## 📱 Notification Types

| Type | Color | Icon | Trigger | Description |
|------|-------|------|---------|-------------|
| 🔔 Input Needed | Yellow | ⚠️ | Claude awaits user input | Session paused, needs attention |
| ⚡ Work in Progress | Blue | 🔧 | After tool usage | File edits, commands, progress updates |
| ✅ Session Complete | Green | ✅ | Claude finishes responding | Task completed successfully |

### Block Kit Message Format

All notifications use Slack's Block Kit for rich formatting:
- **Header**: Clear notification type with emoji
- **Context**: Session ID and timestamp
- **Section**: Main message content
- **Fields**: Tool details (for PostToolUse)
- **Divider**: Visual separation

Example notification structure:
```json
{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "✅ Session Complete",
        "emoji": true
      }
    },
    {
      "type": "context",
      "elements": [
        {
          "type": "mrkdwn",
          "text": "Session: `abc-123` | Project: `my-project`"
        }
      ]
    }
  ]
}
```

## 🎮 Available Commands

**Slash Commands** - Python-enhanced with comprehensive error handling:

| Command | Description | Example |
|---------|-------------|---------|
| `/user:slack:setup WEBHOOK_URL` | Setup Slack integration for project | `/user:slack:setup https://hooks.slack.com/services/T../B../x..` |
| `/user:slack:start` | Enable Slack notifications | `/user:slack:start` |
| `/user:slack:stop` | Disable Slack notifications | `/user:slack:stop` |
| `/user:slack:status` | Show current integration status | `/user:slack:status` |
| `/user:slack:remove` | Remove Slack integration from project | `/user:slack:remove` |

### Command Features
- **Comprehensive error handling** - User-friendly messages for all edge cases
- **Webhook validation** - Supports both `/services/` and `/workflows/` formats
- **Consistent formatting** - Uniform output across all commands
- **Installation detection** - Automatic local vs global installation detection
- **Safe configuration** - Backup creation and selective updates
- **State persistence** - Configuration saved between sessions

## 🛠️ Advanced Usage

### Multiple Projects

**Local Installation**: Each project is completely independent:
```bash
# Project A - local installation
cd /path/to/project-a
curl -fsSL .../install.sh | bash
/user:slack:setup https://hooks.slack.com/services/DEV_WEBHOOK

# Project B - separate local installation
cd /path/to/project-b
curl -fsSL .../install.sh | bash
/user:slack:setup https://hooks.slack.com/workflows/TEST_WEBHOOK
```

**Global Installation**: Shared setup across projects:
```bash
# One-time global install
curl -fsSL .../install.sh | bash -s -- --global

# Then configure each project
cd project-a && /user:slack:setup DEV_WEBHOOK
cd project-b && /user:slack:setup TEST_WEBHOOK
```

### Custom Notification Filtering

Configure which notifications you want to receive:

```bash
# Edit .claude/slack-state.json
{
  "webhook_url": "your-webhook",
  "enabled": true,
  "notifications": {
    "session_complete": true,
    "input_needed": true,
    "work_in_progress": false  # Disable progress updates
  }
}
```

### Team Collaboration

**Local Installation (Recommended)**:
```bash
# Commit Slack integration for team sharing
git add .claude/hooks/ .claude/commands/ .claude/settings.json
git commit -m "Add Slack notifications for team"

# .gitignore - exclude personal webhooks
echo ".claude/slack-state.json" >> .gitignore
echo ".claude/settings.json.backup*" >> .gitignore

# Team members just need to configure their webhook
/user:slack:setup https://hooks.slack.com/services/THEIR_WEBHOOK
/user:slack:start
```

**Global Installation**:
```bash
# Team lead sets up global installation
curl -fsSL .../install.sh | bash -s -- --global

# Commit project hooks only
git add .claude/settings.json
git commit -m "Add Slack hooks config"

# Each team member configures their webhook per project
/user:slack:setup THEIR_WEBHOOK
/user:slack:start
```

## 🔧 Troubleshooting

### No Notifications Received

1. Check if Slack integration is active:
   ```bash
   /user:slack:status
   ```

2. Verify configuration files exist:
   ```bash
   ls -la .claude/
   # Should show: slack-state.json, settings.json
   ```

3. Test webhook manually:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test message from Claude Code"}' \
     YOUR_WEBHOOK_URL
   ```

4. Check hook registration:
   ```bash
   cat .claude/settings.json | grep -A 5 "hooks"
   ```

### Installation Issues

**Permission Denied**:
```bash
chmod +x install.sh
./install.sh
```

**Command Not Found**:
```bash
# Ensure you're in the correct directory
pwd  # Should show .claude directory
ls -la .claude/commands/slack/
```

**Python Errors**:
```bash
# Check Python version (needs 3.6+)
python3 --version

# Verify Python path
which python3
```

### Webhook Validation Failed

The integration supports two webhook formats:
- **Incoming Webhooks**: `https://hooks.slack.com/services/T*/B*/token`
- **Workflow Webhooks**: `https://hooks.slack.com/workflows/T*/A*/token/token`

If your webhook is rejected, verify it matches one of these patterns.

### Rate Limiting

The integration automatically handles Slack rate limits:
- Respects `Retry-After` headers
- Implements exponential backoff
- Logs rate limit events for debugging

## 📂 File Structure

```
.claude/
├── hooks/
│   ├── stop-slack.py           # Session complete notifications
│   ├── notification-slack.py   # Input needed alerts
│   └── posttooluse-slack.py   # Work in progress updates
├── commands/
│   └── slack/
│       ├── slack_utils.py     # Core utility functions
│       ├── setup_handler.py   # /user:slack:setup command
│       ├── start_handler.py   # /user:slack:start command
│       ├── stop_handler.py    # /user:slack:stop command
│       ├── status_handler.py  # /user:slack:status command
│       └── remove_handler.py  # /user:slack:remove command
├── settings.json              # Hook registration
└── slack-state.json          # Configuration state
```

## 🔒 Security

- **Local storage only** - No external servers or cloud services
- **Webhook URLs never exposed** - Stored locally in `.claude/slack-state.json`
- **No telemetry** - Zero data collection
- **Git-friendly** - Webhooks excluded from version control by default
- **Secure defaults** - HTTPS required for all webhooks

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/projectassistant-webdev/claude-code-slack.git
cd claude-code-slack

# Run tests (when available)
python3 tests/run_tests.py

# Test with mock Slack server
python3 tests/mock_slack_server.py --background
python3 tests/test_integration.py
```

## 📜 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) by Anthropic
- Inspired by the claude-code-discord integration
- Uses Slack's [Block Kit](https://api.slack.com/block-kit) for rich formatting
- Thanks to the Claude Code community for feedback and testing

## 📚 Documentation

### Integration Guides
- **[Installation Guide](docs/INSTALLATION.md)** - Detailed installation instructions for all platforms
- **[Configuration Guide](docs/CONFIGURATION.md)** - Complete configuration reference and examples
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Solutions for common issues
- **[Development Guide](docs/DEVELOPMENT.md)** - Contributing and extending the integration

### External Resources
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Claude Code Hooks Reference](https://docs.anthropic.com/en/docs/claude-code/hooks)
- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)
- [Slack Block Kit Builder](https://app.slack.com/block-kit-builder)
- [Slack API Documentation](https://api.slack.com/)

## 🐛 Known Issues

- Workflow webhooks require exact format matching
- Some environments may require explicit Python 3 path configuration
- Rate limiting may delay notifications during heavy usage

## 📈 Version History

### v1.0.0 (2025-09-29)
- Initial release with full TDD implementation
- Support for all Claude Code hook events
- Comprehensive Block Kit formatting
- Local and global installation options
- Complete test coverage (~80%)
- Mock Slack server for testing

---

**Made with ❤️ for the Claude Code community**