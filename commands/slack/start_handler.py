#!/usr/bin/env python3
"""
Start command handler for Slack integration.

This module handles the /user:slack:start command which enables
Slack notifications with optional thread mode configuration.
"""

import os
import sys
from typing import Dict, Optional, Any

from slack_utils import (
    get_configuration_path,
    load_configuration,
    save_configuration,
    ConfigurationError
)


def parse_start_arguments() -> Dict[str, str]:
    """
    Parse arguments from ARGUMENTS environment variable for start command.

    Returns:
        Dictionary with parsed arguments
    """
    args_string = os.environ.get('ARGUMENTS', '').strip()
    if not args_string:
        return {}

    result = {}
    for arg in args_string.split():
        if '=' in arg:
            key, value = arg.split('=', 1)
            result[key] = value

    return result


def main():
    """Main entry point for start command."""
    # Get configuration path and load existing config
    config_path = get_configuration_path("project")
    config = load_configuration(config_path)

    # Check if Slack is configured
    if not config:
        print("❌ Slack integration is not configured.")
        print("Please run '/user:slack:setup <webhook_url>' first.")
        sys.exit(1)

    # Check if webhook URL is present
    if "webhook_url" not in config or not config["webhook_url"]:
        print("❌ Slack webhook URL is not configured.")
        print("Please run '/user:slack:setup <webhook_url>' first.")
        sys.exit(1)

    try:
        # Parse optional arguments
        args = parse_start_arguments()

        # Check if already active
        was_already_active = config.get("active", False)

        # Update configuration
        config["active"] = True

        # Handle thread mode if specified
        if "thread_ts" in args:
            config["thread_ts"] = args["thread_ts"]

        # Save updated configuration
        save_configuration(config, config_path)

        # Print appropriate message
        if was_already_active:
            print("ℹ️ Slack notifications are already enabled.")
        else:
            print("✅ Slack notifications enabled!")
            print("Notifications will be sent to the configured webhook.")

        # Show thread mode if enabled
        if "thread_ts" in config:
            print(f"Thread mode enabled: replies will be posted to thread {config['thread_ts']}")

    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()