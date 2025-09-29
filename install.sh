#!/bin/bash

# Claude Slack Integration Installer
# POSIX-compliant installation script for Slack notification hooks
# Usage: ./install.sh [--global] [--quiet]

set -e

# Script version and metadata
SCRIPT_VERSION="1.0.0"
SCRIPT_NAME="Claude Slack Integration Installer"

# Parse command line arguments
GLOBAL_INSTALL=false
QUIET=false
FORCE_INSTALL=false

while [ $# -gt 0 ]; do
    case $1 in
        --global)
            GLOBAL_INSTALL=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --force)
            FORCE_INSTALL=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --global    Install globally to ~/.claude (requires sudo for system-wide)"
            echo "  --quiet     Suppress non-error output"
            echo "  --force     Force installation even if components already exist"
            echo "  --help      Show this help message"
            echo ""
            echo "Default: Local installation to .claude/ in current directory"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
    esac
done

# Determine installation paths based on mode
if [ "$GLOBAL_INSTALL" = true ]; then
    # Check if we need sudo for global installation
    if [ "$(id -u)" -ne 0 ] && [ ! -w "${HOME}/.claude" ] 2>/dev/null; then
        # Check if ~/.claude exists and is writable, otherwise we might need sudo
        if [ ! -d "${HOME}/.claude" ]; then
            CLAUDE_HOME="${HOME}/.claude"
        else
            CLAUDE_HOME="${HOME}/.claude"
        fi
    else
        CLAUDE_HOME="${HOME}/.claude"
    fi
    HOOKS_DIR="${CLAUDE_HOME}/hooks"
    COMMANDS_DIR="${CLAUDE_HOME}/commands"
    INSTALL_MODE="global"
    INSTALL_TARGET="global installation (${HOME}/.claude)"
else
    CLAUDE_HOME=".claude"
    HOOKS_DIR="${CLAUDE_HOME}/hooks"
    COMMANDS_DIR="${CLAUDE_HOME}/commands"
    INSTALL_MODE="local"
    INSTALL_TARGET="local installation (.claude/)"
fi

# Get current working directory for display
CURRENT_DIR="$(pwd)"

# Source directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_HOOKS_DIR="${SCRIPT_DIR}/hooks"
SOURCE_COMMANDS_DIR="${SCRIPT_DIR}/commands"

# Colors for output (only use if terminal supports it)
if [ -t 1 ] && command -v tput >/dev/null 2>&1; then
    RED=$(tput setaf 1 2>/dev/null || echo '')
    GREEN=$(tput setaf 2 2>/dev/null || echo '')
    YELLOW=$(tput setaf 3 2>/dev/null || echo '')
    BLUE=$(tput setaf 4 2>/dev/null || echo '')
    BOLD=$(tput bold 2>/dev/null || echo '')
    NC=$(tput sgr0 2>/dev/null || echo '')
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    BOLD=''
    NC=''
fi

# Logging functions
log_info() {
    if [ "$QUIET" = false ]; then
        echo "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [ "$QUIET" = false ]; then
        echo "${GREEN}[SUCCESS]${NC} $1"
    fi
}

log_warning() {
    if [ "$QUIET" = false ]; then
        echo "${YELLOW}[WARNING]${NC} $1"
    fi
}

log_error() {
    echo "${RED}[ERROR]${NC} $1" >&2
}

log_debug() {
    if [ "${DEBUG:-false}" = true ] && [ "$QUIET" = false ]; then
        echo "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Error handling
cleanup_on_error() {
    log_error "Installation failed. Cleaning up..."
    # Remove any partially created files
    if [ -d "$HOOKS_DIR" ] && [ "$HOOKS_DIR" != "${HOME}/.claude/hooks" ]; then
        # Only clean up if it's a newly created local directory
        if [ "$INSTALL_MODE" = "local" ] && [ -z "$(ls -A "$HOOKS_DIR" 2>/dev/null | grep -v '^[.]')" ]; then
            rmdir "$HOOKS_DIR" 2>/dev/null || true
        fi
    fi
    if [ -d "$CLAUDE_HOME" ] && [ "$CLAUDE_HOME" != "${HOME}/.claude" ]; then
        if [ "$INSTALL_MODE" = "local" ] && [ -z "$(ls -A "$CLAUDE_HOME" 2>/dev/null | grep -v '^[.]')" ]; then
            rmdir "$CLAUDE_HOME" 2>/dev/null || true
        fi
    fi
}

# Set up error handling
trap cleanup_on_error EXIT

# Check if running on supported platform
check_platform() {
    local platform
    platform="$(uname -s)"
    case "$platform" in
        Linux|Darwin)
            log_debug "Platform: $platform (supported)"
            return 0
            ;;
        MINGW*|MSYS*|CYGWIN*)
            # Windows with WSL or Git Bash
            log_debug "Platform: $platform (Windows compatibility layer)"
            # Check if we're in WSL
            if [ -f /proc/version ] && grep -qi microsoft /proc/version; then
                log_debug "WSL environment detected"
                return 0
            fi
            log_warning "Windows environment detected. Some features may not work correctly."
            return 0
            ;;
        *)
            log_error "Unsupported platform: $platform"
            log_error "This script supports Linux, macOS, and WSL only"
            return 1
            ;;
    esac
}

# Check for required dependencies
check_dependencies() {
    log_info "Checking dependencies..."

    local missing_deps=()
    local python_found=false
    local python_version=""
    local download_tool=""

    # Check for Python 3.6+
    for python_cmd in python3 python; do
        if command -v "$python_cmd" >/dev/null 2>&1; then
            python_version=$($python_cmd --version 2>&1 | head -n1)
            log_debug "Found Python: $python_version"

            # Extract major.minor version
            version_num=$(echo "$python_version" | grep -oE '[0-9]+\.[0-9]+' | head -n1)
            if [ -n "$version_num" ]; then
                major=$(echo "$version_num" | cut -d. -f1)
                minor=$(echo "$version_num" | cut -d. -f2)

                if [ "$major" -gt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -ge 6 ]); then
                    python_found=true
                    log_debug "Python version check passed: $version_num"
                    break
                else
                    log_debug "Python version too old: $version_num"
                fi
            fi
        fi
    done

    if [ "$python_found" = false ]; then
        missing_deps+=("python3 (version 3.6 or higher)")
    fi

    # Check for download tools (curl or wget)
    if command -v curl >/dev/null 2>&1; then
        download_tool="curl"
        log_debug "Download tool: curl"
    elif command -v wget >/dev/null 2>&1; then
        download_tool="wget"
        log_debug "Download tool: wget"
    else
        missing_deps+=("curl or wget")
    fi

    # Check for basic Unix tools
    for tool in mkdir cp chmod rm; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_deps+=("$tool")
        fi
    done

    # Report missing dependencies
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "Missing required dependencies:"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
        echo ""
        log_error "Please install missing dependencies and try again"

        # Provide platform-specific installation hints
        case "$(uname -s)" in
            Linux)
                echo "On Ubuntu/Debian: sudo apt update && sudo apt install python3 curl"
                echo "On CentOS/RHEL: sudo yum install python3 curl"
                echo "On Arch: sudo pacman -S python curl"
                ;;
            Darwin)
                echo "On macOS: brew install python3 curl"
                echo "Or install Python from https://www.python.org/"
                ;;
        esac
        return 1
    fi

    log_success "Dependencies check passed"
    return 0
}

# Check if Claude Code is installed (for global installations)
check_claude_code() {
    if [ "$GLOBAL_INSTALL" = true ]; then
        log_info "Checking Claude Code installation..."

        if [ ! -d "${HOME}/.claude" ]; then
            log_error "Claude Code directory not found at ${HOME}/.claude"
            log_error "Please install Claude Code first:"
            log_error "  https://docs.anthropic.com/claude/docs/claude-code"
            return 1
        fi

        log_success "Claude Code found"
    else
        log_debug "Local installation - Claude Code check skipped"
    fi
    return 0
}

# Check for existing Slack installation
check_existing_installation() {
    log_info "Checking for existing Slack integration..."

    local slack_hooks_found=()
    local existing_components=()

    # Check for hook files
    for hook in notification-slack.py posttooluse-slack.py stop-slack.py; do
        if [ -f "${HOOKS_DIR}/$hook" ]; then
            slack_hooks_found+=("$hook")
            existing_components+=("hook: $hook")
        fi
    done

    # Check for command directory
    if [ -d "${COMMANDS_DIR}/slack" ]; then
        existing_components+=("commands: slack/")
    fi

    # Check for configuration file
    if [ -f "${CLAUDE_HOME}/slack-config.json" ]; then
        existing_components+=("config: slack-config.json")
    fi

    # Check settings.json for Slack hooks
    if [ -f "${CLAUDE_HOME}/settings.json" ]; then
        if grep -q "slack" "${CLAUDE_HOME}/settings.json" 2>/dev/null; then
            existing_components+=("settings: Slack hooks registered")
        fi
    fi

    if [ ${#existing_components[@]} -gt 0 ]; then
        if [ "$FORCE_INSTALL" = false ]; then
            log_warning "Existing Slack integration components found:"
            for component in "${existing_components[@]}"; do
                echo "  - $component"
            done
            echo ""
            log_warning "Use --force to overwrite existing installation"
            log_warning "Or run uninstall.sh first to clean up"
            return 1
        else
            log_warning "Existing components found but --force specified, continuing..."
            return 0
        fi
    fi

    log_success "No existing Slack integration found"
    return 0
}

# Create necessary directories
create_directories() {
    log_info "Creating directories..."

    # Create main Claude directory
    if [ ! -d "$CLAUDE_HOME" ]; then
        mkdir -p "$CLAUDE_HOME" || {
            log_error "Failed to create directory: $CLAUDE_HOME"
            return 1
        }
        log_debug "Created: $CLAUDE_HOME"
    fi

    # Create hooks directory
    if [ ! -d "$HOOKS_DIR" ]; then
        mkdir -p "$HOOKS_DIR" || {
            log_error "Failed to create directory: $HOOKS_DIR"
            return 1
        }
        log_debug "Created: $HOOKS_DIR"
    fi

    # Create commands directory
    if [ ! -d "$COMMANDS_DIR" ]; then
        mkdir -p "$COMMANDS_DIR" || {
            log_error "Failed to create directory: $COMMANDS_DIR"
            return 1
        }
        log_debug "Created: $COMMANDS_DIR"
    fi

    # Create commands/slack directory
    if [ ! -d "${COMMANDS_DIR}/slack" ]; then
        mkdir -p "${COMMANDS_DIR}/slack" || {
            log_error "Failed to create directory: ${COMMANDS_DIR}/slack"
            return 1
        }
        log_debug "Created: ${COMMANDS_DIR}/slack"
    fi

    log_success "Directories created"
    return 0
}

# Backup existing settings
backup_existing_settings() {
    if [ -f "${CLAUDE_HOME}/settings.json" ]; then
        local backup_file="${CLAUDE_HOME}/settings.json.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "Backing up existing settings.json..."

        cp "${CLAUDE_HOME}/settings.json" "$backup_file" || {
            log_error "Failed to create backup of settings.json"
            return 1
        }

        log_success "Settings backup created: $(basename "$backup_file")"
    fi
    return 0
}

# Install hook scripts
install_hooks() {
    log_info "Installing hook scripts..."

    local hooks_installed=0
    local hook_files=("notification-slack.py" "posttooluse-slack.py" "stop-slack.py")

    for hook in "${hook_files[@]}"; do
        local source_file="${SOURCE_HOOKS_DIR}/$hook"
        local dest_file="${HOOKS_DIR}/$hook"

        if [ ! -f "$source_file" ]; then
            log_error "Source hook file not found: $source_file"
            return 1
        fi

        # Copy hook file
        cp "$source_file" "$dest_file" || {
            log_error "Failed to copy hook file: $hook"
            return 1
        }

        # Make executable (755 permissions)
        chmod 755 "$dest_file" || {
            log_error "Failed to set permissions for: $hook"
            return 1
        }

        log_debug "Installed: $hook"
        hooks_installed=$((hooks_installed + 1))
    done

    log_success "Installed $hooks_installed hook scripts"
    return 0
}

# Install command handlers and markdown files
install_commands() {
    log_info "Installing command handlers..."

    local commands_installed=0

    # Check if source commands directory exists
    if [ ! -d "$SOURCE_COMMANDS_DIR" ]; then
        log_warning "Source commands directory not found: $SOURCE_COMMANDS_DIR"
        log_warning "Skipping command installation"
        return 0
    fi

    # Copy all files from commands/slack directory if it exists
    if [ -d "${SOURCE_COMMANDS_DIR}/slack" ]; then
        cp -r "${SOURCE_COMMANDS_DIR}/slack/"* "${COMMANDS_DIR}/slack/" 2>/dev/null || {
            log_warning "Failed to copy some command files"
        }

        # Make Python files executable
        find "${COMMANDS_DIR}/slack" -name "*.py" -type f -exec chmod 755 {} \; 2>/dev/null || true

        # Count installed files
        commands_installed=$(find "${COMMANDS_DIR}/slack" -type f | wc -l)
        log_success "Installed $commands_installed command files"
    else
        log_warning "No slack commands directory found in source"
    fi

    return 0
}

# Register hooks in settings.json
register_hooks() {
    log_info "Registering Slack hooks in settings.json..."

    local settings_file="${CLAUDE_HOME}/settings.json"

    # Create Python script to safely update settings.json
    python3 - "$settings_file" << 'EOF'
import json
import sys
import os

settings_file = sys.argv[1] if len(sys.argv) > 1 else '.claude/settings.json'

# Default Slack hooks configuration
slack_hooks = {
    "notification": [
        {
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py",
            "description": "Send notifications to Slack"
        }
    ],
    "posttooluse": [
        {
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/posttooluse-slack.py",
            "description": "Send tool usage updates to Slack"
        }
    ],
    "stop": [
        {
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/stop-slack.py",
            "description": "Send session completion notifications to Slack"
        }
    ]
}

try:
    # Load existing settings or create new ones
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    else:
        settings = {}

    # Initialize hooks section if it doesn't exist
    if 'hooks' not in settings:
        settings['hooks'] = {}

    # Add Slack hooks, preserving existing ones
    for hook_type, hooks in slack_hooks.items():
        if hook_type not in settings['hooks']:
            settings['hooks'][hook_type] = []

        # Check if Slack hook already exists
        slack_hook_exists = False
        for existing_hook in settings['hooks'][hook_type]:
            if 'slack' in existing_hook.get('command', ''):
                slack_hook_exists = True
                break

        # Add Slack hook if it doesn't exist
        if not slack_hook_exists:
            settings['hooks'][hook_type].extend(hooks)

    # Write updated settings
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)

    print("SUCCESS: Hooks registered successfully")

except Exception as e:
    print(f"ERROR: Failed to register hooks: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        log_success "Slack hooks registered in settings.json"
        return 0
    else
        log_error "Failed to register hooks in settings.json"
        return 1
    fi
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."

    local errors=0
    local checks_performed=0

    # Check hook scripts
    for hook in notification-slack.py posttooluse-slack.py stop-slack.py; do
        checks_performed=$((checks_performed + 1))
        if [ ! -f "${HOOKS_DIR}/$hook" ]; then
            log_error "Hook script missing: $hook"
            errors=$((errors + 1))
        elif [ ! -x "${HOOKS_DIR}/$hook" ]; then
            log_error "Hook script not executable: $hook"
            errors=$((errors + 1))
        else
            log_debug "Verified: $hook"
        fi
    done

    # Check settings.json
    checks_performed=$((checks_performed + 1))
    if [ ! -f "${CLAUDE_HOME}/settings.json" ]; then
        log_error "Settings file missing: settings.json"
        errors=$((errors + 1))
    else
        # Check if Slack hooks are registered
        if grep -q "slack" "${CLAUDE_HOME}/settings.json" 2>/dev/null; then
            log_debug "Verified: Slack hooks in settings.json"
        else
            log_error "Slack hooks not found in settings.json"
            errors=$((errors + 1))
        fi
    fi

    # Check commands directory (optional)
    if [ -d "${COMMANDS_DIR}/slack" ]; then
        local cmd_count
        cmd_count=$(find "${COMMANDS_DIR}/slack" -type f | wc -l)
        log_debug "Found $cmd_count command files"
    fi

    # Summary
    if [ $errors -eq 0 ]; then
        log_success "Installation verification passed ($checks_performed checks)"
        return 0
    else
        log_error "Installation verification failed: $errors errors out of $checks_performed checks"
        return 1
    fi
}

# Display installation summary
show_installation_summary() {
    if [ "$QUIET" = true ]; then
        return 0
    fi

    echo ""
    echo "=================================================="
    echo "${BOLD}${GREEN}Installation completed successfully!${NC}"
    echo "=================================================="
    echo ""
    echo "${BOLD}Installation Details:${NC}"
    echo "  Mode: $INSTALL_MODE"
    echo "  Target: $INSTALL_TARGET"
    echo "  Hooks: ${HOOKS_DIR}/"
    if [ -d "${COMMANDS_DIR}/slack" ]; then
        echo "  Commands: ${COMMANDS_DIR}/slack/"
    fi
    echo ""

    echo "${BOLD}Next Steps:${NC}"
    echo "1. ${BLUE}Configure Slack integration:${NC}"
    echo "   Create ${CLAUDE_HOME}/slack-config.json with your webhook URL"
    echo ""
    echo "2. ${BLUE}Example configuration:${NC}"
    echo "   {"
    echo "     \"enabled\": true,"
    echo "     \"webhook_url\": \"https://hooks.slack.com/services/YOUR/WEBHOOK/URL\","
    echo "     \"project_name\": \"My Project\""
    echo "   }"
    echo ""
    echo "3. ${BLUE}Test the integration:${NC}"
    echo "   The hooks will automatically send notifications when Claude Code events occur"
    echo ""

    if [ "$INSTALL_MODE" = "local" ]; then
        echo "${BOLD}Local Installation Notes:${NC}"
        echo "  - Hooks installed for current project only"
        echo "  - Configuration: $(pwd)/.claude/"
        echo "  - To use in other projects, run install.sh in each project directory"
    else
        echo "${BOLD}Global Installation Notes:${NC}"
        echo "  - Hooks available for all projects"
        echo "  - Global configuration: ${HOME}/.claude/"
        echo "  - Per-project config files will override global settings"
    fi

    echo ""
    echo "${GREEN}Happy coding with Slack notifications! 🚀${NC}"
}

# Main installation function
main() {
    # Remove error trap for normal execution
    trap - EXIT

    if [ "$QUIET" = false ]; then
        echo "=================================================="
        echo "$SCRIPT_NAME v$SCRIPT_VERSION"
        echo "Target: $INSTALL_TARGET"
        echo "=================================================="
        echo ""
    fi

    # Pre-installation checks
    check_platform || return 1
    check_dependencies || return 1
    check_claude_code || return 1
    check_existing_installation || return 1

    # Installation steps
    create_directories || return 1
    backup_existing_settings || return 1
    install_hooks || return 1
    install_commands || return 1
    register_hooks || return 1

    # Post-installation verification
    verify_installation || return 1

    # Success
    show_installation_summary
    return 0
}

# Handle script interruption
handle_interrupt() {
    echo ""
    log_error "Installation interrupted by user"
    cleanup_on_error
    exit 130
}

trap handle_interrupt INT TERM

# Run main function with error handling
if main "$@"; then
    exit 0
else
    log_error "Installation failed"
    exit 1
fi