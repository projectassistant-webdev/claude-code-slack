#!/usr/bin/env python3
"""
Status command handler for Slack integration.

This module handles the /user:slack:status command which displays
current Slack integration configuration and statistics.
"""

import os
import sys
from typing import Dict, Any

from slack_utils import (
    get_configuration_path,
    load_configuration,
    mask_webhook_url,
    detect_installation_type,
    ConfigurationError
)


def format_notification_settings(settings: Dict[str, Any]) -> None:
    """
    Print formatted notification settings.

    Args:
        settings: Notification settings dictionary
    """
    print("🔔 Notification Settings")
    for key, value in settings.items():
        formatted_key = key.replace("_", " ").title()
        status = "✅ Enabled" if value else "❌ Disabled"
        print(f"{formatted_key}: {status}")


def format_statistics(stats: Dict[str, Any]) -> None:
    """
    Print formatted statistics.

    Args:
        stats: Statistics dictionary
    """
    if not stats:
        print("📈 Statistics")
        print("No statistics available")
        return

    print("📈 Statistics")

    if "total_notifications_sent" in stats:
        print(f"Total Notifications Sent: {stats['total_notifications_sent']}")

    if "notifications_today" in stats:
        print(f"Notifications Today: {stats['notifications_today']}")

    if "last_notification_time" in stats:
        print(f"Last Notification: {stats['last_notification_time']}")


def main():
    """Main entry point for status command."""
    try:
        print("📊 Slack Integration Status")
        print("=" * 50)

        # Get configuration path and load config
        config_path = get_configuration_path("project")

        try:
            config = load_configuration(config_path)
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            return

        # Check if configured
        if not config or "webhook_url" not in config:
            print("Status: ❌ Not Configured")
            print("")
            print("To set up Slack integration:")
            print("  /user:slack:setup <webhook_url> [channel] [project_name]")
            print("")
            print("Example:")
            print("  /user:slack:setup https://hooks.slack.com/services/T.../B.../... #general my-project")
            return

        # Show status
        is_active = config.get("active", False)
        if is_active:
            print("Status: ✅ Active")
        else:
            print("Status: ⏸️ Configured but Inactive")
            print("")
            print("To enable notifications:")
            print("  /user:slack:start")
            print("")

        # Show basic configuration
        print(f"Webhook URL: {mask_webhook_url(config['webhook_url'])}")

        if "project_name" in config:
            print(f"Project: {config['project_name']}")

        if "default_channel" in config:
            print(f"Default Channel: {config['default_channel']}")

        # Show installation type
        installation_type = detect_installation_type()
        if installation_type == "project":
            print("Installation Type: Project-level")
        elif installation_type == "user":
            print("Installation Type: User-level")

        # Show thread mode if enabled
        if "thread_ts" in config:
            print(f"Thread Mode: ✅ Enabled ({config['thread_ts']})")

        print("")

        # Show notification settings if available
        if "notification_settings" in config and config["notification_settings"]:
            format_notification_settings(config["notification_settings"])
            print("")

        # Show statistics if available
        if "statistics" in config and config["statistics"]:
            format_statistics(config["statistics"])

    except ConfigurationError as e:
        print("📊 Slack Integration Status")
        print("=" * 50)
        print(f"❌ Error loading configuration: {e}")
    except Exception as e:
        print("📊 Slack Integration Status")
        print("=" * 50)
        print(f"❌ Error loading configuration: {e}")


if __name__ == "__main__":
    main()