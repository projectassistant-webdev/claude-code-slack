"""
Slack utility functions for webhook URL validation, message formatting, and configuration management.

This module provides comprehensive functionality for integrating with Slack including:
- Webhook URL validation and parsing
- Block Kit message formatting for various notification types
- Configuration file management and validation
- Error handling and data validation
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass


# Webhook URL validation functions
def is_valid_webhook_url(url: str) -> bool:
    """
    Validates if a URL is a properly formatted Slack webhook URL.

    Args:
        url: The URL to validate

    Returns:
        True if valid Slack webhook URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    # Slack webhook URL patterns (supports both services and workflows)
    services_pattern = r'^https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+$'
    workflows_pattern = r'^https://hooks\.slack\.com/workflows/T[A-Z0-9]+/A[A-Z0-9]+/[a-zA-Z0-9]+/[a-zA-Z0-9]+$'

    return bool(re.match(services_pattern, url) or re.match(workflows_pattern, url))


def validate_webhook_url(url: str) -> bool:
    """
    Validates webhook URL and raises ValueError if invalid.

    Args:
        url: The URL to validate

    Returns:
        True if valid

    Raises:
        ValueError: If URL is invalid
    """
    if not is_valid_webhook_url(url):
        raise ValueError(f"Invalid Slack webhook URL: {url}")
    return True


def parse_webhook_url_components(url: str) -> Dict[str, Union[str, bool]]:
    """
    Extracts team_id, bot_id, and token from a webhook URL.

    Args:
        url: The webhook URL to parse

    Returns:
        Dictionary with components and validation status
    """
    if not is_valid_webhook_url(url):
        return {"valid": False}

    pattern = r'^https://hooks\.slack\.com/services/(T[A-Z0-9]+)/(B[A-Z0-9]+)/([a-zA-Z0-9]+)$'
    match = re.match(pattern, url)

    if match:
        team_id, bot_id, token = match.groups()
        return {
            "team_id": team_id,
            "bot_id": bot_id,
            "token": token,
            "valid": True
        }

    return {"valid": False}


def mask_webhook_url(url: str) -> str:
    """
    Masks the token part of a webhook URL for secure display.

    Args:
        url: The webhook URL to mask

    Returns:
        Masked URL string
    """
    if not is_valid_webhook_url(url):
        return "Invalid URL"

    components = parse_webhook_url_components(url)
    if components["valid"]:
        return f"https://hooks.slack.com/services/{components['team_id']}/{components['bot_id']}/..."

    return "Invalid URL"


# Message formatting functions
def format_session_complete_message(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates Block Kit formatted message for session completion.

    Args:
        session_data: Dictionary containing session completion data

    Returns:
        Block Kit formatted message dictionary
    """
    status = session_data.get("status", "success")
    is_success = status == "success"

    # Header with appropriate emoji
    header_text = "✅ Claude Code Session Completed" if is_success else "❌ Claude Code Session Failed"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text
            }
        }
    ]

    # Main session details
    fields = []

    if "session_id" in session_data:
        fields.append({
            "type": "mrkdwn",
            "text": f"*Session ID:*\n{session_data['session_id']}"
        })

    if "duration" in session_data:
        fields.append({
            "type": "mrkdwn",
            "text": f"*Duration:*\n{session_data['duration']}"
        })

    if "commands_executed" in session_data:
        fields.append({
            "type": "mrkdwn",
            "text": f"*Commands:*\n{session_data['commands_executed']}"
        })

    if "files_modified" in session_data:
        fields.append({
            "type": "mrkdwn",
            "text": f"*Files Modified:*\n{session_data['files_modified']}"
        })

    if fields:
        blocks.append({
            "type": "section",
            "fields": fields
        })

    # Tools and files lists
    if "tools_used" in session_data:
        tools_text = ", ".join(session_data["tools_used"][:10])  # Limit to first 10
        if len(session_data["tools_used"]) > 10:
            tools_text += f" (+{len(session_data['tools_used']) - 10} more)"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Tools Used:*\n{tools_text}"
            }
        })

    if "modified_files" in session_data:
        files_text = "\n".join([f"• {f}" for f in session_data["modified_files"][:5]])  # Limit to first 5
        if len(session_data["modified_files"]) > 5:
            files_text += f"\n• (+{len(session_data['modified_files']) - 5} more files)"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Modified Files:*\n{files_text}"
            }
        })

    # Error message for failed sessions
    if not is_success and "error_message" in session_data:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Error:*\n{session_data['error_message']}"
            }
        })

    # Timestamp context
    timestamp = session_data.get("timestamp", datetime.now().isoformat())
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Completed at {timestamp}"
            }
        ]
    })

    return {
        "text": f"Claude Code session {'completed' if is_success else 'failed'}",
        "blocks": blocks
    }


def format_input_needed_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates Block Kit formatted message for input needed notifications.

    Args:
        message_data: Dictionary containing input request data

    Returns:
        Block Kit formatted message dictionary
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "⚠️ Input Needed"
            }
        }
    ]

    # Main prompt section
    prompt = message_data.get("prompt", "Input required")
    context = message_data.get("context", "")

    prompt_text = f"*Prompt:*\n{prompt}"
    if context:
        prompt_text += f"\n\n*Context:*\n{context}"

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": prompt_text
        }
    })

    # Session details
    fields = []
    if "session_id" in message_data:
        fields.append({
            "type": "mrkdwn",
            "text": f"*Session ID:*\n{message_data['session_id']}"
        })

    if "timeout" in message_data:
        timeout_minutes = message_data["timeout"] // 60
        fields.append({
            "type": "mrkdwn",
            "text": f"*Timeout:*\n{timeout_minutes}m"
        })

    if fields:
        blocks.append({
            "type": "section",
            "fields": fields
        })

    # Options if provided
    if "options" in message_data and message_data["options"]:
        options_text = "\n".join([f"• {opt}" for opt in message_data["options"][:10]])  # Limit to 10
        if len(message_data["options"]) > 10:
            options_text += f"\n• (+{len(message_data['options']) - 10} more options)"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Available Options:*\n{options_text}"
            }
        })

    # Timestamp context
    timestamp = message_data.get("timestamp", datetime.now().isoformat())
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Requested at {timestamp}"
            }
        ]
    })

    return {
        "text": "Claude Code needs input to continue",
        "blocks": blocks
    }


def format_work_in_progress_message(progress_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates Block Kit formatted message for work in progress notifications.

    Args:
        progress_data: Dictionary containing progress data

    Returns:
        Block Kit formatted message dictionary
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔄 Work in Progress"
            }
        }
    ]

    # Current task
    current_task = progress_data.get("current_task", "Working...")
    # Truncate long task descriptions
    if len(current_task) > 200:
        current_task = current_task[:197] + "..."

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Current Task:*\n{current_task}"
        }
    })

    # Progress details
    fields = []

    if "session_id" in progress_data:
        fields.append({
            "type": "mrkdwn",
            "text": f"*Session ID:*\n{progress_data['session_id']}"
        })

    if "progress_percentage" in progress_data:
        percentage = progress_data["progress_percentage"]
        # Create simple progress bar
        filled = int(percentage / 10)
        empty = 10 - filled
        progress_bar = "█" * filled + "░" * empty
        fields.append({
            "type": "mrkdwn",
            "text": f"*Progress:*\n{progress_bar} {percentage}%"
        })

    if "estimated_completion" in progress_data and progress_data["estimated_completion"]:
        fields.append({
            "type": "mrkdwn",
            "text": f"*ETA:*\n{progress_data['estimated_completion']}"
        })

    if "files_processed" in progress_data and "total_files" in progress_data:
        fields.append({
            "type": "mrkdwn",
            "text": f"*Files:*\n{progress_data['files_processed']}/{progress_data['total_files']}"
        })

    if fields:
        blocks.append({
            "type": "section",
            "fields": fields
        })

    # Timestamp context
    timestamp = progress_data.get("timestamp", datetime.now().isoformat())
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Updated at {timestamp}"
            }
        ]
    })

    return {
        "text": "Claude Code work in progress",
        "blocks": blocks
    }


def validate_block_kit_structure(blocks: Dict[str, Any]) -> bool:
    """
    Validates Block Kit message structure against Slack specifications.

    Args:
        blocks: Block Kit message structure to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(blocks, dict):
        return False

    # Must have fallback text
    if "text" not in blocks:
        return False

    # Must have blocks array
    if "blocks" not in blocks or not isinstance(blocks["blocks"], list):
        return False

    # Check block count limit (50 blocks max)
    if len(blocks["blocks"]) > 50:
        return False

    # Validate each block
    for block in blocks["blocks"]:
        if not isinstance(block, dict) or "type" not in block:
            return False

        block_type = block["type"]

        # Validate specific block types
        if block_type == "header":
            if "text" not in block or block["text"].get("type") != "plain_text":
                return False
        elif block_type == "section":
            # Check text length limits (3000 chars max)
            if "text" in block and isinstance(block["text"], dict):
                text_content = block["text"].get("text", "")
                if len(text_content) > 3000:
                    return False
            # Check fields limit (10 fields max)
            if "fields" in block and len(block["fields"]) > 10:
                return False
        elif block_type not in ["header", "section", "context", "actions", "divider"]:
            return False

    return True


def truncate_message_content(content: str, max_length: int = 2000) -> str:
    """
    Truncates message content to specified length, preserving word boundaries when possible.

    Args:
        content: The content to truncate
        max_length: Maximum length allowed

    Returns:
        Truncated content string
    """
    if content is None:
        return ""

    if not isinstance(content, str):
        content = str(content)

    if len(content) <= max_length:
        return content

    # Try to preserve word boundaries
    truncated = content[:max_length - 3]  # Leave space for "..."

    # Find last word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # Only use word boundary if it's not too short
        truncated = truncated[:last_space]

    return truncated + "..."


# Configuration management functions
def get_configuration_path(config_type: str = "project") -> str:
    """
    Returns appropriate configuration file path based on type.

    Args:
        config_type: Type of configuration ("project" or "user")

    Returns:
        Path to configuration file

    Raises:
        ValueError: If config_type is invalid
    """
    if config_type == "project":
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        return os.path.join(project_dir, ".claude", "slack-config.json")
    elif config_type == "user":
        home_dir = os.path.expanduser("~")
        return os.path.join(home_dir, ".claude", "slack-config.json")
    else:
        raise ValueError(f"Invalid config_type: {config_type}. Must be 'project' or 'user'")


def load_configuration(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads configuration from JSON file.

    Args:
        config_path: Path to configuration file (uses default if None)

    Returns:
        Configuration dictionary (empty dict if file doesn't exist)

    Raises:
        ConfigurationError: For JSON parsing or permission errors
    """
    if config_path is None:
        config_path = get_configuration_path("project")

    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except PermissionError as e:
        raise ConfigurationError(f"Permission denied reading configuration: {e}")
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
    except Exception as e:
        raise ConfigurationError(f"Error loading configuration: {e}")


def save_configuration(config_data: Dict[str, Any], config_path: Optional[str] = None) -> bool:
    """
    Saves configuration to JSON file with proper formatting.

    Args:
        config_data: Configuration dictionary to save
        config_path: Path to save configuration (uses default if None)

    Returns:
        True on success

    Raises:
        ConfigurationError: For serialization or I/O errors
    """
    if config_path is None:
        config_path = get_configuration_path("project")

    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        return True
    except (TypeError, ValueError) as e:
        raise ConfigurationError(f"Cannot serialize configuration data: {e}")
    except PermissionError as e:
        raise ConfigurationError(f"Permission denied writing configuration: {e}")
    except OSError as e:
        raise ConfigurationError(f"Error writing configuration file: {e}")


def validate_configuration(config_data: Dict[str, Any]) -> bool:
    """
    Validates configuration structure and field types.

    Args:
        config_data: Configuration dictionary to validate

    Returns:
        True if valid

    Raises:
        ConfigurationError: If configuration is invalid
    """
    if not isinstance(config_data, dict):
        raise ConfigurationError("Configuration must be a dictionary")

    # Check required fields
    required_fields = ["version", "active", "webhook_url"]
    for field in required_fields:
        if field not in config_data:
            raise ConfigurationError(f"Missing required field: {field}")

    # Validate field types
    if not isinstance(config_data["active"], bool):
        raise ConfigurationError("Field 'active' must be a boolean")

    if not isinstance(config_data["webhook_url"], str):
        raise ConfigurationError("Field 'webhook_url' must be a string")

    # Validate webhook URL format
    if not is_valid_webhook_url(config_data["webhook_url"]):
        raise ConfigurationError("Invalid webhook URL format")

    # Validate optional fields
    if "project_name" in config_data and not isinstance(config_data["project_name"], str):
        raise ConfigurationError("Field 'project_name' must be a string")

    if "notification_settings" in config_data:
        if not isinstance(config_data["notification_settings"], dict):
            raise ConfigurationError("Field 'notification_settings' must be a dictionary")

    return True


def merge_configurations(user_config: Optional[Dict[str, Any]],
                        project_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merges user-level and project-level configurations.

    Args:
        user_config: User-level configuration dictionary
        project_config: Project-level configuration dictionary

    Returns:
        Merged configuration dictionary (project takes precedence)
    """
    if user_config is None:
        user_config = {}
    if project_config is None:
        project_config = {}

    # Start with user config as base
    merged = user_config.copy()

    # Deep merge project config
    def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    return deep_merge(merged, project_config)


def backup_configuration(config_path: str) -> Optional[str]:
    """
    Creates timestamped backup of existing configuration.

    Args:
        config_path: Path to configuration file to backup

    Returns:
        Path to backup file, or None if source doesn't exist

    Raises:
        ConfigurationError: If backup operation fails
    """
    if not os.path.exists(config_path):
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{config_path}.backup.{timestamp}"

    try:
        shutil.copy2(config_path, backup_path)
        return backup_path
    except Exception as e:
        raise ConfigurationError(f"Failed to create backup: {e}")


def migrate_configuration(old_config: Dict[str, Any], target_version: str = "1.0") -> Dict[str, Any]:
    """
    Migrates configuration from old format to new format.

    Args:
        old_config: Configuration in old format
        target_version: Target version to migrate to

    Returns:
        Migrated configuration dictionary

    Raises:
        ConfigurationError: For unsupported migrations
    """
    if not isinstance(old_config, dict):
        raise ConfigurationError("Configuration must be a dictionary")

    # Check if already current version
    if old_config.get("version") == target_version:
        return old_config.copy()

    if target_version != "1.0":
        raise ConfigurationError(f"Unsupported target version: {target_version}")

    migrated = {}

    # Migrate from old field names to new ones
    field_mappings = {
        "slack_webhook": "webhook_url",
        "enabled": "active"
    }

    # Copy and rename fields
    for old_key, new_key in field_mappings.items():
        if old_key in old_config:
            migrated[new_key] = old_config[old_key]

    # Copy other fields as-is
    for key, value in old_config.items():
        if key not in field_mappings and key != "notifications":
            migrated[key] = value

    # Migrate notification structure
    if "notifications" in old_config:
        migrated["notification_settings"] = {}
        notifications = old_config["notifications"]

        if "on_complete" in notifications:
            migrated["notification_settings"]["session_complete"] = notifications["on_complete"]
        if "on_error" in notifications:
            migrated["notification_settings"]["error_notifications"] = notifications["on_error"]

    # Set version
    migrated["version"] = target_version

    return migrated


# Settings.json management functions
def get_settings_path(config_type: str = "project") -> str:
    """
    Returns appropriate settings.json file path based on type.

    Args:
        config_type: Type of configuration ("project" or "user")

    Returns:
        Path to settings.json file

    Raises:
        ValueError: If config_type is invalid
    """
    if config_type == "project":
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        return os.path.join(project_dir, ".claude", "settings.json")
    elif config_type == "user":
        home_dir = os.path.expanduser("~")
        return os.path.join(home_dir, ".claude", "settings.json")
    else:
        raise ValueError(f"Invalid config_type: {config_type}. Must be 'project' or 'user'")


def load_settings_json(settings_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads settings from settings.json file.

    Args:
        settings_path: Path to settings.json file (uses default if None)

    Returns:
        Settings dictionary (empty dict if file doesn't exist)

    Raises:
        ConfigurationError: For JSON parsing or permission errors
    """
    if settings_path is None:
        settings_path = get_settings_path("project")

    if not os.path.exists(settings_path):
        return {}

    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except PermissionError as e:
        raise ConfigurationError(f"Permission denied reading settings: {e}")
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Invalid JSON in settings file: {e}")
    except Exception as e:
        raise ConfigurationError(f"Error loading settings: {e}")


def save_settings_json(settings_data: Dict[str, Any], settings_path: Optional[str] = None) -> bool:
    """
    Saves settings to settings.json file with proper formatting.

    Args:
        settings_data: Settings dictionary to save
        settings_path: Path to save settings (uses default if None)

    Returns:
        True on success

    Raises:
        ConfigurationError: For serialization or I/O errors
    """
    if settings_path is None:
        settings_path = get_settings_path("project")

    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)

    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=2, ensure_ascii=False)
        return True
    except (TypeError, ValueError) as e:
        raise ConfigurationError(f"Cannot serialize settings data: {e}")
    except PermissionError as e:
        raise ConfigurationError(f"Permission denied writing settings: {e}")
    except OSError as e:
        raise ConfigurationError(f"Error writing settings file: {e}")


def register_hook_in_settings(hooks_to_register: List[str], settings_path: Optional[str] = None) -> bool:
    """
    Registers hooks in settings.json file.

    Args:
        hooks_to_register: List of hook filenames to register
        settings_path: Path to settings.json file (uses default if None)

    Returns:
        True on success

    Raises:
        ConfigurationError: For settings file errors
    """
    if settings_path is None:
        settings_path = get_settings_path("project")

    # Load existing settings
    settings = load_settings_json(settings_path)

    # Ensure hooks section exists
    if "hooks" not in settings:
        settings["hooks"] = {}

    # Define hook type mappings
    hook_types = {
        "notification-slack.py": "notification",
        "posttooluse-slack.py": "posttooluse",
        "stop-slack.py": "stop"
    }

    # Register each hook
    for hook_file in hooks_to_register:
        hook_type = hook_types.get(hook_file)
        if not hook_type:
            continue

        # Ensure hook type array exists
        if hook_type not in settings["hooks"]:
            settings["hooks"][hook_type] = []

        # Add hook if not already present
        if hook_file not in settings["hooks"][hook_type]:
            settings["hooks"][hook_type].append(hook_file)

    # Save updated settings
    return save_settings_json(settings, settings_path)


def unregister_hooks_from_settings(hooks_to_remove: List[str], settings_path: Optional[str] = None) -> bool:
    """
    Unregisters hooks from settings.json file.

    Args:
        hooks_to_remove: List of hook filenames to remove
        settings_path: Path to settings.json file (uses default if None)

    Returns:
        True if any hooks were removed, False if none found

    Raises:
        ConfigurationError: For settings file errors
    """
    if settings_path is None:
        settings_path = get_settings_path("project")

    # Load existing settings
    settings = load_settings_json(settings_path)

    if "hooks" not in settings:
        return False

    hooks_removed = False

    # Remove each hook from all hook types
    for hook_type in settings["hooks"]:
        if isinstance(settings["hooks"][hook_type], list):
            original_length = len(settings["hooks"][hook_type])
            settings["hooks"][hook_type] = [
                hook for hook in settings["hooks"][hook_type]
                if hook not in hooks_to_remove
            ]
            if len(settings["hooks"][hook_type]) < original_length:
                hooks_removed = True

    # Save updated settings if any changes were made
    if hooks_removed:
        save_settings_json(settings, settings_path)

    return hooks_removed


def detect_installation_type() -> str:
    """
    Detects whether Slack integration is installed at project or user level.

    Returns:
        "project" if project-level config exists, "user" if user-level, "none" if neither
    """
    project_config = get_configuration_path("project")
    user_config = get_configuration_path("user")

    if os.path.exists(project_config):
        return "project"
    elif os.path.exists(user_config):
        return "user"
    else:
        return "none"