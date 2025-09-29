#!/usr/bin/env python3
"""
Stop command handler for Slack integration.

This module handles the /user:slack:stop command which disables
Slack notifications and removes thread-specific settings.
"""

import os
import sys
from typing import Dict, Any

from slack_utils import (
    get_configuration_path,
    load_configuration,
    save_configuration,
    ConfigurationError
)


def main():
    """Main entry point for stop command."""
    # Get configuration path and load existing config
    config_path = get_configuration_path("project")
    config = load_configuration(config_path)

    # Check if Slack is configured
    if not config:
        print("❌ Slack integration is not configured.")
        print("Nothing to disable.")
        sys.exit(1)

    try:
        # Check if already inactive
        was_already_inactive = not config.get("active", False)

        # Update configuration
        config["active"] = False

        # Remove thread-specific settings when stopping
        if "thread_ts" in config:
            del config["thread_ts"]

        # Save updated configuration
        save_configuration(config, config_path)

        # Print appropriate message
        if was_already_inactive:
            print("ℹ️ Slack notifications are already disabled.")
        else:
            print("🔇 Slack notifications disabled.")
            print("You can re-enable them with '/user:slack:start'.")

    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()