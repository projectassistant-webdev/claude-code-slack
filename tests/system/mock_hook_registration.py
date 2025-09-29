"""
Mock implementation of hook registration functionality for testing.

This module provides mock implementations of settings.json modification
to enable testing before the actual registration logic is implemented.
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional


class HookRegistration:
    """Mock hook registration class that simulates settings.json modification."""

    def __init__(self, claude_dir: str):
        self.claude_dir = claude_dir
        self.settings_path = os.path.join(claude_dir, 'settings.json')

    def register_slack_hooks(self, create_backup: bool = False, timestamp_backup: bool = False) -> Dict[str, Any]:
        """
        Mock hook registration in settings.json.

        Args:
            create_backup: Whether to create a backup of settings.json
            timestamp_backup: Whether to add timestamp to backup filename

        Returns:
            Dict containing success status and details
        """
        try:
            # Create backup if requested
            backup_created = False
            if create_backup and os.path.exists(self.settings_path):
                backup_created = self._create_backup(timestamp_backup)
                if not backup_created:
                    return {
                        'success': False,
                        'error': 'Backup failed - permission denied',
                        'backup_created': False
                    }

            # Ensure directory exists
            if not os.path.exists(self.claude_dir):
                try:
                    os.makedirs(self.claude_dir, exist_ok=True)
                except PermissionError:
                    return {
                        'success': False,
                        'error': 'Failed to create directory - permission denied',
                        'backup_created': backup_created
                    }

            # Read existing settings
            settings = self._read_settings()
            if settings is None:
                return {
                    'success': False,
                    'error': 'Invalid JSON in settings file',
                    'backup_created': backup_created
                }

            # Add Slack hooks
            hooks_added = self._add_slack_hooks(settings)

            # Write updated settings
            self._write_settings(settings)

            return {
                'success': True,
                'hooks_added': hooks_added,
                'backup_created': backup_created
            }

        except PermissionError:
            return {
                'success': False,
                'error': 'Permission denied accessing settings file',
                'backup_created': backup_created
            }
        except OSError as e:
            if 'No space left' in str(e):
                return {
                    'success': False,
                    'error': 'No space left on device',
                    'backup_created': backup_created
                }
            return {
                'success': False,
                'error': str(e),
                'backup_created': backup_created
            }

    def _create_backup(self, timestamp_backup: bool) -> bool:
        """Create backup of settings.json."""
        try:
            if timestamp_backup:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f'{self.settings_path}.backup.{timestamp}'
            else:
                backup_path = f'{self.settings_path}.backup'

            shutil.copy2(self.settings_path, backup_path)
            return True
        except (PermissionError, OSError):
            return False

    def _read_settings(self) -> Optional[Dict[str, Any]]:
        """Read and parse settings.json."""
        if not os.path.exists(self.settings_path):
            return {}

        try:
            with open(self.settings_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except json.JSONDecodeError:
            return None
        except (PermissionError, OSError):
            raise

    def _write_settings(self, settings: Dict[str, Any]) -> None:
        """Write settings to settings.json."""
        with open(self.settings_path, 'w') as f:
            json.dump(settings, f, indent=2)

    def _add_slack_hooks(self, settings: Dict[str, Any]) -> List[str]:
        """Add Slack hooks to settings, preserving existing hooks."""
        if 'hooks' not in settings:
            settings['hooks'] = {}

        slack_hooks = {
            'notification': {
                'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py',
                'description': 'Send notifications to Slack'
            },
            'posttooluse': {
                'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/posttooluse-slack.py',
                'description': 'Send tool usage updates to Slack'
            },
            'stop': {
                'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/stop-slack.py',
                'description': 'Send session completion notifications to Slack'
            }
        }

        hooks_added = []

        for hook_type, hook_config in slack_hooks.items():
            if hook_type not in settings['hooks']:
                settings['hooks'][hook_type] = []

            # Check if Slack hook already exists
            existing_commands = [h.get('command', '') for h in settings['hooks'][hook_type]]
            slack_hook_exists = any('slack.py' in cmd for cmd in existing_commands)

            if not slack_hook_exists:
                settings['hooks'][hook_type].append(hook_config)
                hooks_added.append(hook_type)

        return hooks_added

    def detect_existing_slack_hooks(self) -> Dict[str, List[str]]:
        """Detect existing Slack hooks in settings."""
        settings = self._read_settings()
        if not settings or 'hooks' not in settings:
            return {}

        existing_slack_hooks = {}
        for hook_type, hook_list in settings['hooks'].items():
            slack_hooks = [
                hook for hook in hook_list
                if isinstance(hook, dict) and 'slack.py' in hook.get('command', '')
            ]
            if slack_hooks:
                existing_slack_hooks[hook_type] = [hook['command'] for hook in slack_hooks]

        return existing_slack_hooks

    def remove_slack_hooks(self) -> Dict[str, Any]:
        """Remove Slack hooks from settings."""
        try:
            settings = self._read_settings()
            if not settings or 'hooks' not in settings:
                return {
                    'success': True,
                    'hooks_removed': [],
                    'message': 'No hooks found to remove'
                }

            hooks_removed = []
            for hook_type, hook_list in list(settings['hooks'].items()):
                # Filter out Slack hooks
                non_slack_hooks = [
                    hook for hook in hook_list
                    if not (isinstance(hook, dict) and 'slack.py' in hook.get('command', ''))
                ]

                if len(non_slack_hooks) != len(hook_list):
                    hooks_removed.append(hook_type)

                if non_slack_hooks:
                    settings['hooks'][hook_type] = non_slack_hooks
                else:
                    # Remove empty hook category
                    del settings['hooks'][hook_type]

            self._write_settings(settings)

            return {
                'success': True,
                'hooks_removed': hooks_removed
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class HookValidator:
    """Validate hook configurations."""

    @staticmethod
    def validate_hook_structure(hook: Dict[str, Any]) -> bool:
        """Validate that a hook has the required structure."""
        required_fields = ['command', 'description']
        return all(field in hook for field in required_fields)

    @staticmethod
    def validate_slack_hook_command(command: str) -> bool:
        """Validate that a command is a valid Slack hook command."""
        return (
            command.startswith('$CLAUDE_PROJECT_DIR/.claude/hooks/') and
            command.endswith('-slack.py')
        )

    @staticmethod
    def normalize_hook_path(command: str, claude_dir: str) -> str:
        """Normalize hook path to use $CLAUDE_PROJECT_DIR variable."""
        if command.startswith(claude_dir):
            # Replace absolute path with variable
            relative_path = command[len(claude_dir):].lstrip('/')
            return f'$CLAUDE_PROJECT_DIR/.claude/{relative_path}'
        return command


class SettingsManager:
    """Advanced settings management functionality."""

    def __init__(self, settings_path: str):
        self.settings_path = settings_path

    def merge_settings(self, new_settings: Dict[str, Any], preserve_existing: bool = True) -> Dict[str, Any]:
        """Merge new settings with existing ones."""
        if not preserve_existing:
            return new_settings

        existing = self._load_settings()
        return self._deep_merge(existing, new_settings)

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file."""
        if not os.path.exists(self.settings_path):
            return {}

        try:
            with open(self.settings_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            elif key in result and isinstance(result[key], list) and isinstance(value, list):
                # For lists, append unique items
                for item in value:
                    if item not in result[key]:
                        result[key].append(item)
            else:
                result[key] = value

        return result

    def backup_settings(self, timestamp: bool = True) -> str:
        """Create a backup of current settings."""
        if not os.path.exists(self.settings_path):
            raise FileNotFoundError("Settings file does not exist")

        if timestamp:
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f'{self.settings_path}.backup.{timestamp_str}'
        else:
            backup_path = f'{self.settings_path}.backup'

        shutil.copy2(self.settings_path, backup_path)
        return backup_path

    def restore_settings(self, backup_path: str) -> bool:
        """Restore settings from backup."""
        try:
            shutil.copy2(backup_path, self.settings_path)
            return True
        except (IOError, OSError):
            return False


# Mock functions for direct testing

def create_mock_settings_file(claude_dir: str, settings_data: Dict[str, Any]) -> str:
    """Create a mock settings file with given data."""
    settings_path = os.path.join(claude_dir, 'settings.json')
    os.makedirs(claude_dir, exist_ok=True)

    with open(settings_path, 'w') as f:
        json.dump(settings_data, f, indent=2)

    return settings_path


def validate_settings_structure(settings: Dict[str, Any]) -> List[str]:
    """Validate settings structure and return list of issues."""
    issues = []

    if 'hooks' in settings:
        hooks = settings['hooks']
        if not isinstance(hooks, dict):
            issues.append("'hooks' must be a dictionary")
        else:
            for hook_type, hook_list in hooks.items():
                if not isinstance(hook_list, list):
                    issues.append(f"Hook type '{hook_type}' must be a list")
                else:
                    for i, hook in enumerate(hook_list):
                        if not isinstance(hook, dict):
                            issues.append(f"Hook {i} in '{hook_type}' must be a dictionary")
                        else:
                            if 'command' not in hook:
                                issues.append(f"Hook {i} in '{hook_type}' missing 'command' field")
                            if 'description' not in hook:
                                issues.append(f"Hook {i} in '{hook_type}' missing 'description' field")

    return issues


def get_slack_hook_commands() -> Dict[str, str]:
    """Get the expected Slack hook commands."""
    return {
        'notification': '$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py',
        'posttooluse': '$CLAUDE_PROJECT_DIR/.claude/hooks/posttooluse-slack.py',
        'stop': '$CLAUDE_PROJECT_DIR/.claude/hooks/stop-slack.py'
    }