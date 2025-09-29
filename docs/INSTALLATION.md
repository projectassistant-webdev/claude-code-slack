# Installation Guide

This guide provides detailed installation instructions for the Claude Code Slack Integration across different platforms and configurations.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [Platform-Specific Instructions](#platform-specific-instructions)
- [Verification](#verification)
- [Upgrading](#upgrading)
- [Uninstallation](#uninstallation)

## Prerequisites

### Required Software
- **Claude Code**: Must be installed and accessible from your terminal
- **Python 3.6+**: Required for hook scripts and command handlers
- **Bash Shell**: For installation scripts (Git Bash on Windows)
- **Git** (optional): For cloning the repository

### Verify Prerequisites
```bash
# Check Claude Code installation
claude --version

# Check Python version
python3 --version
# or
python --version

# Check bash availability
bash --version
```

## Installation Methods

### Method 1: Quick Install (Recommended)

#### Local Installation
Best for single projects where you want notifications only for that specific project:

```bash
cd /path/to/your/project
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash
```

#### Global Installation
For system-wide installation that works across all projects:

```bash
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash -s -- --global
```

### Method 2: Manual Installation

#### Step 1: Clone the Repository
```bash
git clone https://github.com/projectassistant-webdev/claude-code-slack.git
cd claude-code-slack
```

#### Step 2: Make Scripts Executable
```bash
chmod +x install.sh
chmod +x uninstall.sh
chmod +x hooks/*.py
```

#### Step 3: Run Installation
```bash
# For local installation
./install.sh

# For global installation
./install.sh --global
```

### Method 3: Manual Setup (Advanced)

If you prefer to set up everything manually:

#### Step 1: Create Directory Structure
```bash
# For local installation
mkdir -p .claude/hooks
mkdir -p .claude/commands/slack

# For global installation
mkdir -p ~/.claude/hooks
mkdir -p ~/.claude/commands/slack
```

#### Step 2: Copy Files
```bash
# Set target directory
TARGET_DIR=".claude"  # or "~/.claude" for global

# Copy hook scripts
cp hooks/stop-slack.py $TARGET_DIR/hooks/
cp hooks/notification-slack.py $TARGET_DIR/hooks/
cp hooks/posttooluse-slack.py $TARGET_DIR/hooks/

# Copy command handlers
cp -r commands/slack/ $TARGET_DIR/commands/

# Make scripts executable
chmod +x $TARGET_DIR/hooks/*.py
```

#### Step 3: Update settings.json
Add the following to your `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/stop-slack.py"
      }]
    }],
    "Notification": [{
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py"
      }]
    }],
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/posttooluse-slack.py"
      }]
    }]
  },
  "commands": {
    "user:slack:setup": {
      "type": "python",
      "module": "commands.slack.setup_handler"
    },
    "user:slack:start": {
      "type": "python",
      "module": "commands.slack.start_handler"
    },
    "user:slack:stop": {
      "type": "python",
      "module": "commands.slack.stop_handler"
    },
    "user:slack:status": {
      "type": "python",
      "module": "commands.slack.status_handler"
    },
    "user:slack:remove": {
      "type": "python",
      "module": "commands.slack.remove_handler"
    }
  }
}
```

## Platform-Specific Instructions

### macOS

1. **Install Homebrew** (if not already installed):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. **Ensure Python 3 is installed**:
```bash
brew install python3
```

3. **Run installation**:
```bash
cd your-project
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash
```

### Linux (Ubuntu/Debian)

1. **Update package list**:
```bash
sudo apt update
```

2. **Install Python 3** (if needed):
```bash
sudo apt install python3 python3-pip
```

3. **Run installation**:
```bash
cd your-project
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash
```

### Windows (WSL)

1. **Install WSL** (if not already installed):
```powershell
wsl --install
```

2. **Inside WSL, install Python**:
```bash
sudo apt update
sudo apt install python3
```

3. **Run installation**:
```bash
cd /mnt/c/Users/YourName/your-project
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash
```

### Windows (Git Bash)

1. **Install Git for Windows** (includes Git Bash)
2. **Install Python for Windows** from python.org
3. **Open Git Bash and run**:
```bash
cd /c/Users/YourName/your-project
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash
```

## Verification

After installation, verify everything is working correctly:

### 1. Check Installation Type
```bash
/user:slack:status
```

Expected output:
```
📊 Slack Integration Status
──────────────────────────
✅ Installation: Local
⚠️  Status: Not configured
📍 Location: /path/to/project/.claude
```

### 2. Verify File Structure
```bash
# For local installation
ls -la .claude/hooks/*slack*
ls -la .claude/commands/slack/

# For global installation
ls -la ~/.claude/hooks/*slack*
ls -la ~/.claude/commands/slack/
```

### 3. Test Hook Registration
```bash
cat .claude/settings.json | grep -A 5 "hooks"
```

You should see the Stop, Notification, and PostToolUse hooks registered.

### 4. Test Python Environment
```bash
python3 -c "import sys; print(f'Python {sys.version}')"
python3 -c "from commands.slack import slack_utils; print('✓ Modules load correctly')"
```

## Upgrading

### Automatic Upgrade
```bash
# Backup current installation
cp -r .claude .claude.backup

# Re-run installation
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash
```

### Manual Upgrade
1. **Backup your configuration**:
```bash
cp .claude/slack-state.json .claude/slack-state.json.backup
```

2. **Pull latest changes**:
```bash
cd claude-code-slack
git pull origin main
```

3. **Re-run installation**:
```bash
./install.sh
```

## Uninstallation

### Method 1: Using Uninstall Script

```bash
# For local installation
./.claude/uninstall.sh

# For global installation
~/.claude/uninstall.sh --global
```

### Method 2: Using Remove Command

```bash
/user:slack:remove
```

### Method 3: Manual Removal

```bash
# Remove hooks from settings.json
# Edit .claude/settings.json and remove Slack-related hooks

# Remove Slack files
rm -f .claude/hooks/*slack*
rm -rf .claude/commands/slack
rm -f .claude/slack-state.json

# Remove backup files
rm -f .claude/settings.json.backup*
```

## Troubleshooting Installation

### Common Issues

#### Permission Denied
```bash
# Fix permissions
chmod +x install.sh
chmod +x hooks/*.py
```

#### Command Not Found
```bash
# Ensure you're in the correct directory
pwd
ls -la install.sh

# Or download directly
wget https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh
chmod +x install.sh
./install.sh
```

#### Python Module Not Found
```bash
# Add project to Python path
export PYTHONPATH="$PYTHONPATH:$(pwd)"

# Or use full paths in settings.json
"command": "/usr/bin/python3 /full/path/to/.claude/hooks/stop-slack.py"
```

#### Curl Not Available
Use wget instead:
```bash
wget -O - https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/main/install.sh | bash
```

### Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review the [FAQ](#frequently-asked-questions)
3. Open an issue on GitHub
4. Contact support

## Frequently Asked Questions

### Q: Can I install both locally and globally?
A: Yes, local installations take precedence over global ones when you're in a project directory with local installation.

### Q: How do I switch from local to global installation?
A: Uninstall the local version first (`/user:slack:remove`), then run the global installation.

### Q: Can I use different webhooks for different projects?
A: Yes! With local installation, each project has its own configuration. With global installation, you can still configure different webhooks per project.

### Q: Will installation affect my existing Claude Code setup?
A: No, the installation is non-destructive. It only adds new hooks and preserves all existing configuration.

### Q: How do I know if installation was successful?
A: Run `/user:slack:status` - you should see installation details. If not configured yet, you'll see "Not configured" which is expected.

---

**Next Steps**: After installation, proceed to [Configuration Guide](CONFIGURATION.md) to set up your Slack webhook.