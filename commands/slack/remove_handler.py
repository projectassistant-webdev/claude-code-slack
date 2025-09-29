#!/usr/bin/env python3
"""
Remove command handler for Slack integration.

This module handles the /user:slack:remove command which completely
removes Slack integration configuration with backup and confirmation.
"""

import os
import sys
import json
from typing import Dict, List, Any

from slack_utils import (
    get_configuration_path,
    load_configuration,
    backup_configuration,
    unregister_hooks_from_settings,
    ConfigurationError
)


def parse_remove_arguments() -> Dict[str, bool]:
    """
    Parse arguments from ARGUMENTS environment variable for remove command.

    Returns:
        Dictionary with parsed flags
    """
    args_string = os.environ.get('ARGUMENTS', '').strip()
    result = {"force": False}

    if args_string:
        args = args_string.split()
        if "--force" in args or "-f" in args:
            result["force"] = True

    return result


def confirm_removal() -> bool:
    """
    Prompt user for confirmation before removal.

    Returns:
        True if user confirms, False otherwise
    """
    print("⚠️  This will completely remove Slack integration:")
    print("   • Delete configuration file")
    print("   • Remove hooks from settings.json")
    print("   • Disable all notifications")
    print("")

    try:
        response = input("Are you sure you want to continue? (y/N): ").strip().lower()
        return response in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        print("\n❌ Removal cancelled.")
        return False


def main():
    """Main entry point for remove command."""
    try:
        # Get configuration path
        config_path = get_configuration_path("project")

        # Check if configuration exists
        if not os.path.exists(config_path):
            print("ℹ️  Slack integration is not installed.")
            print("Nothing to remove.")
            return

        # Parse arguments for force flag
        args = parse_remove_arguments()
        force_mode = args["force"]

        # Load existing configuration (if possible)
        try:
            config = load_configuration(config_path)
        except json.JSONDecodeError:
            print("⚠️  Configuration file appears corrupted, but will be removed.")
            config = {}
        except Exception:
            config = {}

        # Get confirmation unless forced
        if not force_mode:
            if not confirm_removal():
                print("❌ Removal cancelled.")
                return

        # Create backup of configuration
        try:
            backup_path = backup_configuration(config_path)
            if backup_path:
                print(f"📁 Configuration backed up to: {backup_path}")
        except Exception as e:
            print(f"❌ Error creating backup: {e}")
            sys.exit(1)

        # Remove hooks from settings.json
        hooks_to_remove = [
            'notification-slack.py',
            'posttooluse-slack.py',
            'stop-slack.py'
        ]

        try:
            hooks_removed = unregister_hooks_from_settings(hooks_to_remove)
            if hooks_removed:
                print("🔗 Slack hooks removed from settings.json")
            else:
                print("ℹ️  No Slack hooks found in settings.json")
        except Exception as e:
            print(f"⚠️  Warning: Could not remove hooks from settings.json: {e}")

        # Delete configuration file
        try:
            os.remove(config_path)
            print("🗑️  Configuration file deleted")
        except PermissionError as e:
            print(f"❌ Error deleting configuration file: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error deleting configuration file: {e}")
            sys.exit(1)

        # Show success summary
        print("✅ Slack integration completely removed!")
        print("")
        print("Summary of changes:")
        if backup_path:
            print(f"  • Configuration backed up to: {backup_path}")
        print(f"  • Configuration file deleted: {config_path}")
        print("  • Slack hooks removed from settings.json")
        print("  • All notifications disabled")

    except ConfigurationError as e:
        print(f"❌ Error during removal: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during removal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()