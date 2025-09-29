#!/usr/bin/env python3
"""
Setup command handler for Slack integration.

This module handles the /user:slack:setup command which configures
Slack webhook integration for Claude Code notifications.
"""

import os
import sys
from typing import Dict, List, Optional, Any

from slack_utils import (
    is_valid_webhook_url,
    mask_webhook_url,
    get_configuration_path,
    load_configuration,
    save_configuration,
    register_hook_in_settings,
    ConfigurationError
)


def parse_arguments() -> Optional[List[str]]:
    """
    Parse arguments from ARGUMENTS environment variable.

    Returns:
        List of arguments or None if not provided
    """
    args_string = os.environ.get('ARGUMENTS', '').strip()
    if not args_string:
        return None

    return args_string.split()


def validate_setup_arguments(args: List[str]) -> Dict[str, str]:
    """
    Validate and parse setup command arguments.

    Args:
        args: List of command arguments

    Returns:
        Dictionary with parsed arguments

    Raises:
        ValueError: If arguments are invalid
    """
    if len(args) < 1:
        raise ValueError("Webhook URL is required")

    if len(args) > 3:
        raise ValueError("Too many arguments")

    webhook_url = args[0]
    channel = args[1] if len(args) > 1 else None
    project_name = args[2] if len(args) > 2 else None

    # Validate webhook URL
    if not is_valid_webhook_url(webhook_url):
        raise ValueError("Invalid Slack webhook URL format")

    result = {"webhook_url": webhook_url}

    if channel:
        result["default_channel"] = channel

    if project_name:
        result["project_name"] = project_name

    return result


def create_configuration(parsed_args: Dict[str, str], existing_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create configuration dictionary with new and existing settings.

    Args:
        parsed_args: Parsed command arguments
        existing_config: Existing configuration to preserve

    Returns:
        Complete configuration dictionary
    """
    # Start with existing config to preserve settings
    config = existing_config.copy()

    # Update with new values
    config.update(parsed_args)

    # Set required fields
    config["version"] = "1.0"
    config["active"] = True

    return config


def main():
    """Main entry point for setup command."""
    # Parse arguments
    args = parse_arguments()
    if args is None:
        print("❌ Error: Webhook URL is required.")
        print("Usage: /user:slack:setup <webhook_url> [channel] [project_name]")
        sys.exit(1)

    # Validate arguments
    try:
        parsed_args = validate_setup_arguments(args)
    except ValueError as e:
        if "Invalid Slack webhook URL format" in str(e):
            print("❌ Error: Invalid Slack webhook URL format.")
            print("Expected format: https://hooks.slack.com/services/T.../B.../...")
        else:
            print(f"❌ Error: {e}")
            print("Usage: /user:slack:setup <webhook_url> [channel] [project_name]")
        sys.exit(1)

    try:
        # Get configuration path and load existing config
        config_path = get_configuration_path("project")
        existing_config = load_configuration(config_path)

        # Create .claude directory if missing
        claude_dir = os.path.dirname(config_path)
        if not os.path.exists(claude_dir):
            os.makedirs(claude_dir, exist_ok=True)

        # Create complete configuration
        config = create_configuration(parsed_args, existing_config)

        # Save configuration
        save_configuration(config, config_path)

        # Register hooks in settings.json
        hooks_to_register = [
            'notification-slack.py',
            'posttooluse-slack.py',
            'stop-slack.py'
        ]
        register_hook_in_settings(hooks_to_register)

        # Print success messages
        print("✅ Slack integration configured successfully!")
        print(f"Webhook URL: {mask_webhook_url(parsed_args['webhook_url'])}")

        if "default_channel" in parsed_args:
            print(f"Default channel: {parsed_args['default_channel']}")

        if "project_name" in parsed_args:
            print(f"Project name: {parsed_args['project_name']}")

    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()