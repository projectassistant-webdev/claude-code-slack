#!/bin/bash

# Claude Slack Integration Uninstaller
# POSIX-compliant uninstallation script for Slack notification hooks
# Usage: ./uninstall.sh [--global] [--force] [--dry-run] [--quiet]

set -e

# Script version and metadata
SCRIPT_VERSION="1.0.0"
SCRIPT_NAME="Claude Slack Integration Uninstaller"

# Parse command line arguments
GLOBAL_UNINSTALL=false
QUIET=false
FORCE_UNINSTALL=false
DRY_RUN=false

while [ $# -gt 0 ]; do
    case $1 in
        --global)
            GLOBAL_UNINSTALL=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --force)
            FORCE_UNINSTALL=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --global     Uninstall from global ~/.claude directory"
            echo "  --force      Skip confirmation prompts"
            echo "  --dry-run    Show what would be removed without actually removing"
            echo "  --quiet      Suppress non-error output"
            echo "  --help       Show this help message"
            echo ""
            echo "Default: Local uninstallation from .claude/ in current directory"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
    esac
done

# Determine uninstallation paths based on mode
if [ "$GLOBAL_UNINSTALL" = true ]; then
    CLAUDE_HOME="${HOME}/.claude"
    HOOKS_DIR="${CLAUDE_HOME}/hooks"
    COMMANDS_DIR="${CLAUDE_HOME}/commands"
    UNINSTALL_MODE="global"
    UNINSTALL_TARGET="global installation (${HOME}/.claude)"
else
    CLAUDE_HOME=".claude"
    HOOKS_DIR="${CLAUDE_HOME}/hooks"
    COMMANDS_DIR="${CLAUDE_HOME}/commands"
    UNINSTALL_MODE="local"
    UNINSTALL_TARGET="local installation (.claude/)"
fi

# Get current working directory for display
CURRENT_DIR="$(pwd)"

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

log_dry_run() {
    if [ "$QUIET" = false ]; then
        echo "${YELLOW}[DRY RUN]${NC} Would remove: $1"
    fi
}

# Check if Slack integration is installed
check_installation() {
    log_info "Checking for Slack integration components..."

    local found_components=()
    local component_paths=()

    # Check for hook scripts
    for hook in notification-slack.py posttooluse-slack.py stop-slack.py; do
        if [ -f "${HOOKS_DIR}/$hook" ]; then
            found_components+=("hook: $hook")
            component_paths+=("${HOOKS_DIR}/$hook")
        fi
    done

    # Check for commands directory
    if [ -d "${COMMANDS_DIR}/slack" ]; then
        found_components+=("commands: slack/")
        component_paths+=("${COMMANDS_DIR}/slack")
    fi

    # Check for configuration file
    if [ -f "${CLAUDE_HOME}/slack-config.json" ]; then
        found_components+=("config: slack-config.json")
        component_paths+=("${CLAUDE_HOME}/slack-config.json")
    fi

    # Check settings.json for Slack hooks
    if [ -f "${CLAUDE_HOME}/settings.json" ]; then
        if grep -q "slack" "${CLAUDE_HOME}/settings.json" 2>/dev/null; then
            found_components+=("settings: Slack hooks registered")
        fi
    fi

    if [ ${#found_components[@]} -eq 0 ]; then
        log_warning "No Slack integration components found"
        return 1
    fi

    if [ "$QUIET" = false ]; then
        log_info "Found Slack integration components:"
        for component in "${found_components[@]}"; do
            echo "  - $component"
        done
    fi

    # Store found paths for dry run
    FOUND_COMPONENT_PATHS="${component_paths[*]}"

    return 0
}

# Prompt for confirmation
confirm_removal() {
    if [ "$FORCE_UNINSTALL" = true ] || [ "$DRY_RUN" = true ] || [ "$QUIET" = true ]; then
        return 0  # Skip confirmation
    fi

    echo ""
    if [ "$GLOBAL_UNINSTALL" = true ]; then
        log_warning "This will remove all global Slack integration components from Claude Code."
        log_warning "Project-specific configuration files will NOT be removed."
    else
        # For local uninstall, check if .claude directory exists
        if [ ! -d ".claude" ]; then
            echo "${RED}No .claude directory found in current location.${NC}"
            echo ""
            echo "This appears to be a directory without Slack integration."
            echo ""
            echo "Available options:"
            echo "• Run from a project directory with Slack integration"
            echo "• Use --global flag to remove global installation"
            return 1
        fi

        log_warning "This will remove Slack integration from the current project only."
        log_warning "Global components in ~/.claude/ will NOT be affected."
    fi
    echo ""

    printf "Are you sure you want to continue? (y/N): "
    read -r REPLY
    echo ""

    case "$REPLY" in
        [Yy]|[Yy][Ee][Ss])
            return 0
            ;;
        *)
            log_info "Uninstallation cancelled"
            return 1
            ;;
    esac
}

# Create backup before removal
create_backup() {
    if [ "$DRY_RUN" = true ]; then
        log_dry_run "Would create backup directory"
        return 0
    fi

    local backup_dir="${CLAUDE_HOME}/slack-backup-$(date +%Y%m%d_%H%M%S)"
    local backup_created=false

    log_info "Creating backup before removal..."

    # Create backup directory
    mkdir -p "$backup_dir" || {
        log_error "Failed to create backup directory: $backup_dir"
        return 1
    }

    # Backup hook scripts
    for hook in notification-slack.py posttooluse-slack.py stop-slack.py; do
        if [ -f "${HOOKS_DIR}/$hook" ]; then
            cp "${HOOKS_DIR}/$hook" "$backup_dir/" && backup_created=true
            log_debug "Backed up: $hook"
        fi
    done

    # Backup commands directory
    if [ -d "${COMMANDS_DIR}/slack" ]; then
        cp -r "${COMMANDS_DIR}/slack" "$backup_dir/" && backup_created=true
        log_debug "Backed up: commands/slack/"
    fi

    # Backup configuration file
    if [ -f "${CLAUDE_HOME}/slack-config.json" ]; then
        cp "${CLAUDE_HOME}/slack-config.json" "$backup_dir/" && backup_created=true
        log_debug "Backed up: slack-config.json"
    fi

    # Backup settings.json if it contains Slack hooks
    if [ -f "${CLAUDE_HOME}/settings.json" ] && grep -q "slack" "${CLAUDE_HOME}/settings.json" 2>/dev/null; then
        cp "${CLAUDE_HOME}/settings.json" "$backup_dir/settings.json.with_slack_hooks" && backup_created=true
        log_debug "Backed up: settings.json"
    fi

    if [ "$backup_created" = true ]; then
        log_success "Backup created at: $(basename "$backup_dir")"
    else
        # Remove empty backup directory
        rmdir "$backup_dir" 2>/dev/null || true
        log_info "No components to backup"
    fi

    return 0
}

# Remove hook scripts
remove_hooks() {
    log_info "Removing hook scripts..."

    local removed=0
    local hook_files=("notification-slack.py" "posttooluse-slack.py" "stop-slack.py")

    for hook in "${hook_files[@]}"; do
        local hook_path="${HOOKS_DIR}/$hook"

        if [ -f "$hook_path" ]; then
            if [ "$DRY_RUN" = true ]; then
                log_dry_run "$hook_path"
            else
                rm -f "$hook_path" || {
                    log_error "Failed to remove hook: $hook"
                    continue
                }
                log_debug "Removed: $hook"
            fi
            removed=$((removed + 1))
        fi
    done

    if [ $removed -gt 0 ]; then
        if [ "$DRY_RUN" = true ]; then
            log_info "Would remove $removed hook scripts"
        else
            log_success "Removed $removed hook scripts"
        fi
    else
        log_info "No hook scripts to remove"
    fi

    return 0
}

# Remove command handlers and markdown files
remove_commands() {
    log_info "Removing command handlers..."

    if [ -d "${COMMANDS_DIR}/slack" ]; then
        if [ "$DRY_RUN" = true ]; then
            log_dry_run "${COMMANDS_DIR}/slack/"
            log_info "Would remove slack commands directory"
        else
            rm -rf "${COMMANDS_DIR}/slack" || {
                log_error "Failed to remove commands directory"
                return 1
            }
            log_success "Removed slack commands directory"
        fi
    else
        log_info "No slack commands directory to remove"
    fi

    return 0
}

# Remove configuration file
remove_config() {
    local config_file="${CLAUDE_HOME}/slack-config.json"

    if [ -f "$config_file" ]; then
        log_info "Removing configuration file..."

        if [ "$DRY_RUN" = true ]; then
            log_dry_run "$config_file"
        else
            rm -f "$config_file" || {
                log_error "Failed to remove configuration file"
                return 1
            }
            log_success "Removed slack-config.json"
        fi
    else
        log_debug "No configuration file to remove"
    fi

    return 0
}

# Remove Slack hooks from settings.json while preserving other hooks
remove_settings_hooks() {
    local settings_file="${CLAUDE_HOME}/settings.json"

    if [ ! -f "$settings_file" ]; then
        log_debug "No settings.json file to clean"
        return 0
    fi

    if ! grep -q "slack" "$settings_file" 2>/dev/null; then
        log_debug "No Slack hooks found in settings.json"
        return 0
    fi

    log_info "Removing Slack hooks from settings.json..."

    if [ "$DRY_RUN" = true ]; then
        log_dry_run "Slack hooks in $settings_file"
        return 0
    fi

    # Create backup of settings.json
    local settings_backup="${settings_file}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$settings_file" "$settings_backup" || {
        log_error "Failed to backup settings.json"
        return 1
    }

    # Use Python to safely remove Slack hooks
    python3 - "$settings_file" << 'EOF'
import json
import sys
import os

settings_file = sys.argv[1] if len(sys.argv) > 1 else '.claude/settings.json'

try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)

    if 'hooks' not in settings:
        print("No hooks section found in settings.json")
        sys.exit(0)

    hooks_removed = []
    original_hooks = settings['hooks'].copy()

    # Remove Slack hooks from each hook type
    for hook_type in list(settings['hooks'].keys()):
        if hook_type in settings['hooks']:
            # Filter out Slack hooks
            original_count = len(settings['hooks'][hook_type])
            settings['hooks'][hook_type] = [
                hook for hook in settings['hooks'][hook_type]
                if 'slack' not in hook.get('command', '').lower()
            ]
            new_count = len(settings['hooks'][hook_type])

            # Remove empty hook categories
            if not settings['hooks'][hook_type]:
                del settings['hooks'][hook_type]
                hooks_removed.append(hook_type)
            elif original_count != new_count:
                hooks_removed.append(hook_type)

    # Write updated settings
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)

    if hooks_removed:
        print(f"SUCCESS: Removed Slack hooks from: {', '.join(hooks_removed)}")
    else:
        print("INFO: No Slack hooks found to remove")

except Exception as e:
    print(f"ERROR: Failed to update settings.json: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        log_success "Slack hooks removed from settings.json"
        log_debug "Settings backup: $(basename "$settings_backup")"
        return 0
    else
        log_error "Failed to remove Slack hooks from settings.json"
        # Restore backup
        cp "$settings_backup" "$settings_file" 2>/dev/null || true
        return 1
    fi
}

# Clean up empty directories
cleanup_empty_directories() {
    log_info "Cleaning up empty directories..."

    local dirs_removed=0

    if [ "$DRY_RUN" = true ]; then
        # Check what would be removed
        if [ -d "$HOOKS_DIR" ] && [ -z "$(ls -A "$HOOKS_DIR" 2>/dev/null)" ]; then
            log_dry_run "Empty directory: $HOOKS_DIR"
            dirs_removed=$((dirs_removed + 1))
        fi

        if [ -d "$COMMANDS_DIR" ] && [ -z "$(ls -A "$COMMANDS_DIR" 2>/dev/null)" ]; then
            log_dry_run "Empty directory: $COMMANDS_DIR"
            dirs_removed=$((dirs_removed + 1))
        fi

        if [ "$UNINSTALL_MODE" = "local" ] && [ -d "$CLAUDE_HOME" ] && [ -z "$(ls -A "$CLAUDE_HOME" 2>/dev/null)" ]; then
            log_dry_run "Empty directory: $CLAUDE_HOME"
            dirs_removed=$((dirs_removed + 1))
        fi

        if [ $dirs_removed -gt 0 ]; then
            log_info "Would remove $dirs_removed empty directories"
        fi
        return 0
    fi

    # Remove empty hooks directory
    if [ -d "$HOOKS_DIR" ] && [ -z "$(ls -A "$HOOKS_DIR" 2>/dev/null)" ]; then
        rmdir "$HOOKS_DIR" 2>/dev/null && {
            log_debug "Removed empty directory: $HOOKS_DIR"
            dirs_removed=$((dirs_removed + 1))
        }
    fi

    # Remove empty commands directory
    if [ -d "$COMMANDS_DIR" ] && [ -z "$(ls -A "$COMMANDS_DIR" 2>/dev/null)" ]; then
        rmdir "$COMMANDS_DIR" 2>/dev/null && {
            log_debug "Removed empty directory: $COMMANDS_DIR"
            dirs_removed=$((dirs_removed + 1))
        }
    fi

    # For local uninstalls, remove .claude directory if completely empty
    if [ "$UNINSTALL_MODE" = "local" ] && [ -d "$CLAUDE_HOME" ] && [ -z "$(ls -A "$CLAUDE_HOME" 2>/dev/null)" ]; then
        rmdir "$CLAUDE_HOME" 2>/dev/null && {
            log_debug "Removed empty directory: $CLAUDE_HOME"
            dirs_removed=$((dirs_removed + 1))
        }
    fi

    if [ $dirs_removed -gt 0 ]; then
        log_success "Cleaned up $dirs_removed empty directories"
    else
        log_debug "No empty directories to clean up"
    fi

    return 0
}

# Verify removal
verify_removal() {
    log_info "Verifying removal..."

    local remaining_components=()
    local verification_errors=0

    # Check for remaining hook scripts
    for hook in notification-slack.py posttooluse-slack.py stop-slack.py; do
        if [ -f "${HOOKS_DIR}/$hook" ]; then
            remaining_components+=("hook: $hook")
            verification_errors=$((verification_errors + 1))
        fi
    done

    # Check for remaining commands directory
    if [ -d "${COMMANDS_DIR}/slack" ]; then
        remaining_components+=("commands: slack/")
        verification_errors=$((verification_errors + 1))
    fi

    # Check for remaining configuration file
    if [ -f "${CLAUDE_HOME}/slack-config.json" ]; then
        remaining_components+=("config: slack-config.json")
        verification_errors=$((verification_errors + 1))
    fi

    # Check settings.json for remaining Slack hooks
    if [ -f "${CLAUDE_HOME}/settings.json" ] && grep -q "slack" "${CLAUDE_HOME}/settings.json" 2>/dev/null; then
        remaining_components+=("settings: Slack hooks still registered")
        verification_errors=$((verification_errors + 1))
    fi

    if [ ${#remaining_components[@]} -eq 0 ]; then
        log_success "All Slack integration components removed successfully"
        return 0
    else
        log_error "Some components could not be removed:"
        for component in "${remaining_components[@]}"; do
            echo "  - $component"
        done
        return 1
    fi
}

# Display uninstallation summary
show_uninstallation_summary() {
    if [ "$QUIET" = true ]; then
        return 0
    fi

    echo ""
    if [ "$DRY_RUN" = true ]; then
        echo "=================================================="
        echo "${BOLD}${BLUE}Dry Run Completed${NC}"
        echo "=================================================="
        echo ""
        echo "${BOLD}What would be removed:${NC}"
        echo "  Mode: $UNINSTALL_MODE"
        echo "  Target: $UNINSTALL_TARGET"
        echo ""
        echo "Run without --dry-run to perform actual removal."
    else
        echo "=================================================="
        echo "${BOLD}${GREEN}Uninstallation completed successfully!${NC}"
        echo "=================================================="
        echo ""
        echo "${BOLD}Removal Summary:${NC}"
        echo "  Mode: $UNINSTALL_MODE"
        echo "  Target: $UNINSTALL_TARGET"
        echo ""

        if [ "$UNINSTALL_MODE" = "local" ]; then
            echo "${BOLD}What was removed:${NC}"
            echo "  - Slack hook scripts from .claude/hooks/"
            echo "  - Slack command handlers from .claude/commands/slack/"
            echo "  - Slack hooks from .claude/settings.json"
            echo "  - slack-config.json configuration file"
            echo "  - Empty directories (if any)"
            echo ""
            echo "${BOLD}What was preserved:${NC}"
            echo "  - Global components in ~/.claude/ (if any)"
            echo "  - Other hooks and settings in .claude/settings.json"
            echo "  - Backup files created during removal"
        else
            echo "${BOLD}What was removed:${NC}"
            echo "  - Global Slack hook scripts from ~/.claude/hooks/"
            echo "  - Global Slack command handlers from ~/.claude/commands/slack/"
            echo "  - Empty directories (if any)"
            echo ""
            echo "${BOLD}What was preserved:${NC}"
            echo "  - Project-specific .claude/ directories"
            echo "  - Project-specific slack-config.json files"
            echo "  - Other global hooks and settings"
            echo "  - Backup files created during removal"
        fi
    fi

    echo ""
    if [ "$DRY_RUN" = false ]; then
        echo "${GREEN}Slack integration successfully removed! 👋${NC}"
    fi
}

# Main uninstallation function
main() {
    if [ "$QUIET" = false ]; then
        echo "=================================================="
        echo "$SCRIPT_NAME v$SCRIPT_VERSION"
        if [ "$DRY_RUN" = true ]; then
            echo "Mode: Dry Run (${UNINSTALL_MODE})"
        else
            echo "Target: $UNINSTALL_TARGET"
        fi
        echo "=================================================="
        echo ""
    fi

    # Pre-uninstallation checks
    if ! check_installation; then
        if [ "$QUIET" = false ]; then
            echo ""
            log_info "Nothing to uninstall. Exiting."
        fi
        return 0
    fi

    # Confirm removal
    if ! confirm_removal; then
        return 1
    fi

    # Perform removal steps
    if [ "$DRY_RUN" = false ]; then
        create_backup || return 1
    fi

    remove_hooks || return 1
    remove_commands || return 1
    remove_config || return 1
    remove_settings_hooks || return 1
    cleanup_empty_directories || return 1

    # Verify removal (skip for dry run)
    if [ "$DRY_RUN" = false ]; then
        verify_removal || return 1
    fi

    # Success
    show_uninstallation_summary
    return 0
}

# Handle script interruption
handle_interrupt() {
    echo ""
    log_error "Uninstallation interrupted by user"
    exit 130
}

trap handle_interrupt INT TERM

# Run main function with error handling
if main "$@"; then
    exit 0
else
    log_error "Uninstallation failed"
    exit 1
fi