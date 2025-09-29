"""
Mock implementation of uninstallation script functionality for testing.

This module provides mock implementations of the uninstall.sh script behavior
to enable testing before the actual scripts are implemented.
"""

import os
import json
import shutil
from typing import Dict, List, Any, Optional
from pathlib import Path


class UninstallManager:
    """Mock uninstall manager that simulates uninstall.sh behavior."""

    def __init__(self, claude_dir: str):
        self.claude_dir = claude_dir
        self.settings_path = os.path.join(claude_dir, 'settings.json')
        self.config_path = os.path.join(claude_dir, 'slack-config.json')
        self.hooks_dir = os.path.join(claude_dir, 'hooks')

    def run_uninstallation(self, options: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Mock complete uninstallation process.

        Args:
            options: List of command line options (--complete, --hooks-only, etc.)

        Returns:
            Dict containing uninstallation results
        """
        options = options or []

        if '--dry-run' in options:
            return self._dry_run_uninstallation()

        try:
            results = {
                'success': True,
                'components_removed': [],
                'files_removed': [],
                'errors': []
            }

            # Create backup if requested
            if '--backup-config' in options:
                backup_result = self._backup_user_config()
                results['config_backed_up'] = backup_result['success']
                if not backup_result['success']:
                    results['errors'].append(backup_result['error'])

            # Remove hooks
            if '--complete' in options or '--hooks-only' in options or not any(opt.startswith('--') for opt in options):
                hook_result = self._remove_slack_hooks()
                if hook_result['success']:
                    results['components_removed'].append('hooks')
                    results['files_removed'].extend(hook_result.get('files_removed', []))
                else:
                    results['errors'].append(hook_result['error'])

            # Remove configuration
            if '--complete' in options or not any(opt.startswith('--') for opt in options):
                config_result = self._remove_slack_config()
                if config_result['success']:
                    results['components_removed'].append('config')
                    results['files_removed'].extend(config_result.get('files_removed', []))
                else:
                    results['errors'].append(config_result['error'])

            # Update settings
            settings_result = self._update_settings()
            if settings_result['success']:
                results['components_removed'].append('settings')
            else:
                results['errors'].append(settings_result['error'])

            # Clean up empty directories
            if '--complete' in options:
                cleanup_result = self._cleanup_directories()
                results['directories_removed'] = cleanup_result.get('directories_removed', [])

            # Determine overall success
            if results['errors']:
                results['success'] = len(results['components_removed']) > 0
                results['partial_success'] = len(results['components_removed']) > 0
                results['message'] = f"Partial uninstallation completed with {len(results['errors'])} errors"
            else:
                results['message'] = 'Uninstallation completed successfully'

            # Handle partial installations
            if not results['components_removed'] and not results['errors']:
                results['message'] = 'No Slack integration components found to remove'

            return results

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'components_removed': [],
                'partial_success': False
            }

    def _dry_run_uninstallation(self) -> Dict[str, Any]:
        """Mock dry run showing what would be removed."""
        files_to_remove = []
        directories_to_remove = []

        # Check for Slack hook files
        slack_hooks = [
            'notification-slack.py',
            'posttooluse-slack.py',
            'stop-slack.py'
        ]

        for hook in slack_hooks:
            hook_path = os.path.join(self.hooks_dir, hook)
            if os.path.exists(hook_path):
                files_to_remove.append(hook_path)

        # Check for Slack config
        if os.path.exists(self.config_path):
            files_to_remove.append(self.config_path)

        # Check if hooks directory would be empty
        if os.path.exists(self.hooks_dir):
            remaining_files = [
                f for f in os.listdir(self.hooks_dir)
                if f not in slack_hooks
            ]
            if not remaining_files:
                directories_to_remove.append(self.hooks_dir)

        return {
            'success': True,
            'dry_run': True,
            'files_to_remove': files_to_remove,
            'directories_to_remove': directories_to_remove,
            'settings_changes': self._preview_settings_changes()
        }

    def _backup_user_config(self) -> Dict[str, Any]:
        """Mock backup of user configuration."""
        if not os.path.exists(self.config_path):
            return {
                'success': True,
                'message': 'No config file to backup'
            }

        try:
            backup_path = f'{self.config_path}.backup'
            shutil.copy2(self.config_path, backup_path)
            return {
                'success': True,
                'backup_path': backup_path
            }
        except PermissionError:
            return {
                'success': False,
                'error': 'Permission denied creating backup'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _remove_slack_hooks(self) -> Dict[str, Any]:
        """Mock removal of Slack hook files."""
        files_removed = []
        errors = []

        slack_hooks = [
            'notification-slack.py',
            'posttooluse-slack.py',
            'stop-slack.py'
        ]

        for hook in slack_hooks:
            hook_path = os.path.join(self.hooks_dir, hook)
            if os.path.exists(hook_path):
                try:
                    os.remove(hook_path)
                    files_removed.append(hook_path)
                except PermissionError:
                    errors.append(f'Permission denied removing {hook_path}')
                except Exception as e:
                    errors.append(f'Error removing {hook_path}: {str(e)}')

        if errors:
            return {
                'success': False,
                'error': '; '.join(errors),
                'files_removed': files_removed
            }

        return {
            'success': True,
            'files_removed': files_removed
        }

    def _remove_slack_config(self) -> Dict[str, Any]:
        """Mock removal of Slack configuration file."""
        if not os.path.exists(self.config_path):
            return {
                'success': True,
                'message': 'Config file not found'
            }

        try:
            os.remove(self.config_path)
            return {
                'success': True,
                'files_removed': [self.config_path]
            }
        except PermissionError:
            return {
                'success': False,
                'error': 'Permission denied removing config file'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _update_settings(self) -> Dict[str, Any]:
        """Mock updating settings.json to remove Slack hooks."""
        if not os.path.exists(self.settings_path):
            return {
                'success': True,
                'message': 'Settings file not found'
            }

        try:
            # Create backup
            backup_path = f'{self.settings_path}.backup'
            shutil.copy2(self.settings_path, backup_path)

            # Read current settings
            with open(self.settings_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    settings = {}
                else:
                    settings = json.loads(content)

            # Remove Slack hooks
            if 'hooks' in settings:
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

            # Write updated settings
            with open(self.settings_path, 'w') as f:
                json.dump(settings, f, indent=2)

            return {
                'success': True,
                'hooks_removed': hooks_removed if 'hooks_removed' in locals() else []
            }

        except json.JSONDecodeError:
            return {
                'success': False,
                'error': 'Malformed settings file'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _cleanup_directories(self) -> Dict[str, Any]:
        """Mock cleanup of empty directories."""
        directories_removed = []

        try:
            # Check if hooks directory is empty
            if os.path.exists(self.hooks_dir):
                if not os.listdir(self.hooks_dir):
                    shutil.rmtree(self.hooks_dir)
                    directories_removed.append(self.hooks_dir)

            # Check if claude directory is empty (optional)
            if os.path.exists(self.claude_dir):
                remaining_items = os.listdir(self.claude_dir)
                # Only remove if completely empty or only contains backup files
                if not remaining_items or all(item.endswith('.backup') for item in remaining_items):
                    # Don't actually remove in mock - this would be dangerous
                    pass

            return {
                'success': True,
                'directories_removed': directories_removed
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'directories_removed': directories_removed
            }

    def _preview_settings_changes(self) -> Dict[str, Any]:
        """Mock preview of settings changes for dry run."""
        if not os.path.exists(self.settings_path):
            return {'message': 'No settings file found'}

        try:
            with open(self.settings_path, 'r') as f:
                settings = json.load(f)

            if 'hooks' not in settings:
                return {'message': 'No hooks found in settings'}

            changes = {}
            for hook_type, hook_list in settings['hooks'].items():
                slack_hooks = [
                    hook for hook in hook_list
                    if isinstance(hook, dict) and 'slack.py' in hook.get('command', '')
                ]
                if slack_hooks:
                    changes[hook_type] = f"Remove {len(slack_hooks)} Slack hook(s)"

            return changes

        except Exception as e:
            return {'error': str(e)}


class HookRemover:
    """Mock hook removal functionality."""

    def __init__(self, settings_path: str):
        self.settings_path = settings_path

    def remove_slack_hooks(self) -> Dict[str, Any]:
        """Mock Slack hook removal from settings."""
        if not os.path.exists(self.settings_path):
            return {
                'success': True,
                'message': 'Settings file not found',
                'hooks_removed': []
            }

        try:
            with open(self.settings_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    settings = {}
                else:
                    settings = json.loads(content)

            if 'hooks' not in settings:
                return {
                    'success': True,
                    'message': 'No hooks found',
                    'hooks_removed': []
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

            # Write updated settings
            with open(self.settings_path, 'w') as f:
                json.dump(settings, f, indent=2)

            return {
                'success': True,
                'hooks_removed': hooks_removed
            }

        except json.JSONDecodeError:
            return {
                'success': False,
                'error': 'Malformed settings file'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class DirectoryCleanup:
    """Mock directory cleanup functionality."""

    def __init__(self, claude_dir: str):
        self.claude_dir = claude_dir
        self.hooks_dir = os.path.join(claude_dir, 'hooks')

    def cleanup_empty_directories(self, remove_claude_dir: bool = False) -> Dict[str, Any]:
        """Mock cleanup of empty directories."""
        directories_removed = []

        try:
            # Check hooks directory
            if os.path.exists(self.hooks_dir):
                if not os.listdir(self.hooks_dir):
                    shutil.rmtree(self.hooks_dir)
                    directories_removed.append(self.hooks_dir)

            # Check claude directory
            if remove_claude_dir and os.path.exists(self.claude_dir):
                remaining_items = os.listdir(self.claude_dir)
                if not remaining_items:
                    shutil.rmtree(self.claude_dir)
                    directories_removed.append(self.claude_dir)

            return {
                'success': True,
                'directories_removed': directories_removed
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'directories_removed': directories_removed
            }

    def is_directory_empty(self, directory_path: str) -> bool:
        """Mock check if directory is empty."""
        if not os.path.exists(directory_path):
            return True

        try:
            return len(os.listdir(directory_path)) == 0
        except OSError:
            return False

    def get_directory_contents(self, directory_path: str) -> List[str]:
        """Mock get directory contents."""
        if not os.path.exists(directory_path):
            return []

        try:
            return os.listdir(directory_path)
        except OSError:
            return []


class UninstallValidator:
    """Mock validation of uninstallation completeness."""

    def __init__(self, claude_dir: str):
        self.claude_dir = claude_dir

    def validate_complete_removal(self) -> Dict[str, Any]:
        """Mock validation that all Slack components are removed."""
        remaining_components = []

        # Check for remaining hook files
        hooks_dir = os.path.join(self.claude_dir, 'hooks')
        if os.path.exists(hooks_dir):
            slack_hooks = [
                f for f in os.listdir(hooks_dir)
                if f.endswith('-slack.py')
            ]
            if slack_hooks:
                remaining_components.extend(slack_hooks)

        # Check for remaining config
        config_path = os.path.join(self.claude_dir, 'slack-config.json')
        if os.path.exists(config_path):
            remaining_components.append('slack-config.json')

        # Check settings for Slack hooks
        settings_path = os.path.join(self.claude_dir, 'settings.json')
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)

                if 'hooks' in settings:
                    for hook_type, hook_list in settings['hooks'].items():
                        slack_hooks = [
                            hook for hook in hook_list
                            if isinstance(hook, dict) and 'slack.py' in hook.get('command', '')
                        ]
                        if slack_hooks:
                            remaining_components.append(f'settings.json:{hook_type}')

            except (json.JSONDecodeError, IOError):
                pass

        return {
            'complete_removal': len(remaining_components) == 0,
            'remaining_components': remaining_components
        }

    def generate_removal_report(self) -> Dict[str, Any]:
        """Mock generation of removal report."""
        validation = self.validate_complete_removal()

        if validation['complete_removal']:
            return {
                'status': 'complete',
                'message': 'All Slack integration components successfully removed',
                'remaining_components': []
            }
        else:
            return {
                'status': 'incomplete',
                'message': f"Found {len(validation['remaining_components'])} remaining components",
                'remaining_components': validation['remaining_components'],
                'recommendations': [
                    'Run uninstall script again with --complete flag',
                    'Manually remove remaining components',
                    'Check file permissions'
                ]
            }


# Mock functions that simulate the uninstall script behavior

def run_uninstall_script(options: Optional[List[str]] = None) -> Dict[str, Any]:
    """Mock function simulating uninstall.sh execution."""
    options = options or []
    claude_dir = '/home/user/.claude'

    uninstaller = UninstallManager(claude_dir)
    return uninstaller.run_uninstallation(options)


def remove_slack_hooks_from_settings(settings_path: str) -> Dict[str, Any]:
    """Mock function for removing Slack hooks from settings."""
    remover = HookRemover(settings_path)
    return remover.remove_slack_hooks()


def cleanup_empty_directories(claude_dir: str, remove_claude_dir: bool = False) -> Dict[str, Any]:
    """Mock function for directory cleanup."""
    cleanup = DirectoryCleanup(claude_dir)
    return cleanup.cleanup_empty_directories(remove_claude_dir)


def validate_uninstallation(claude_dir: str) -> Dict[str, Any]:
    """Mock function for validating uninstallation completeness."""
    validator = UninstallValidator(claude_dir)
    return validator.validate_complete_removal()


# Utility functions for testing

def create_mock_installation(claude_dir: str) -> None:
    """Create a mock installation for testing uninstallation."""
    os.makedirs(claude_dir, exist_ok=True)
    hooks_dir = os.path.join(claude_dir, 'hooks')
    os.makedirs(hooks_dir, exist_ok=True)

    # Create mock hook files
    slack_hooks = [
        'notification-slack.py',
        'posttooluse-slack.py',
        'stop-slack.py'
    ]

    for hook in slack_hooks:
        hook_path = os.path.join(hooks_dir, hook)
        with open(hook_path, 'w') as f:
            f.write(f'#!/usr/bin/env python3\n# Mock {hook} hook\n')

    # Create mock settings.json
    settings = {
        'hooks': {
            'notification': [{
                'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py',
                'description': 'Send notifications to Slack'
            }],
            'posttooluse': [{
                'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/posttooluse-slack.py',
                'description': 'Send tool usage updates to Slack'
            }],
            'stop': [{
                'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/stop-slack.py',
                'description': 'Send session completion notifications to Slack'
            }]
        }
    }

    settings_path = os.path.join(claude_dir, 'settings.json')
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)

    # Create mock config file
    config = {
        'webhook_url': 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX',
        'project_name': 'Test Project'
    }

    config_path = os.path.join(claude_dir, 'slack-config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def simulate_partial_installation(claude_dir: str, components: List[str]) -> None:
    """Simulate a partial installation with only specified components."""
    os.makedirs(claude_dir, exist_ok=True)

    if 'hooks' in components:
        hooks_dir = os.path.join(claude_dir, 'hooks')
        os.makedirs(hooks_dir, exist_ok=True)

        # Create only some hook files
        hook_path = os.path.join(hooks_dir, 'notification-slack.py')
        with open(hook_path, 'w') as f:
            f.write('#!/usr/bin/env python3\n# Mock notification hook\n')

    if 'settings' in components:
        settings = {
            'hooks': {
                'notification': [{
                    'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py',
                    'description': 'Send notifications to Slack'
                }]
            }
        }

        settings_path = os.path.join(claude_dir, 'settings.json')
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)

    if 'config' in components:
        config = {
            'webhook_url': 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX'
        }

        config_path = os.path.join(claude_dir, 'slack-config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)