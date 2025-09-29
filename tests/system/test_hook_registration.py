"""
System tests for hook registration in settings.json.

These tests verify the modification of Claude Code's settings.json file:
- Adding hooks to empty settings
- Merging with existing settings
- Preserving other hooks
- Verifying correct paths with $CLAUDE_PROJECT_DIR
- Settings backup functionality
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, mock_open, MagicMock, call
from pathlib import Path
import shutil
import copy


class TestAddHooksToEmptySettings:
    """Test adding hooks to an empty or non-existent settings file."""

    def test_create_settings_file_if_not_exists(self):
        """Test creating settings.json if it doesn't exist."""
        with patch('os.path.exists', return_value=False), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.makedirs') as mock_makedirs:

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            # Verify directory creation
            mock_makedirs.assert_called_with('/home/user/.claude', exist_ok=True)

            # Verify file creation with proper structure
            mock_file.assert_called_with('/home/user/.claude/settings.json', 'w')
            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            assert 'hooks' in settings
            assert 'notification' in settings['hooks']
            assert 'posttooluse' in settings['hooks']
            assert 'stop' in settings['hooks']
            assert result['success'] is True

    def test_add_hooks_to_empty_json(self):
        """Test adding hooks to an existing but empty settings.json."""
        empty_settings = '{}'

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=empty_settings)) as mock_file:

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            # Verify hooks were added
            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            expected_hooks = {
                'notification': [
                    {
                        'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py',
                        'description': 'Send notifications to Slack'
                    }
                ],
                'posttooluse': [
                    {
                        'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/posttooluse-slack.py',
                        'description': 'Send tool usage updates to Slack'
                    }
                ],
                'stop': [
                    {
                        'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/stop-slack.py',
                        'description': 'Send session completion notifications to Slack'
                    }
                ]
            }

            assert settings['hooks'] == expected_hooks
            assert result['success'] is True
            assert result['hooks_added'] == ['notification', 'posttooluse', 'stop']

    def test_add_hooks_to_minimal_settings(self):
        """Test adding hooks to minimal existing settings."""
        minimal_settings = {
            'version': '1.0'
        }

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(minimal_settings))) as mock_file:

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            # Verify existing settings preserved
            assert settings['version'] == '1.0'

            # Verify hooks added
            assert 'hooks' in settings
            assert len(settings['hooks']) == 3
            assert result['success'] is True

    def test_handle_malformed_json(self):
        """Test handling of malformed JSON in settings file."""
        malformed_json = '{"version": "1.0", invalid json'

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=malformed_json)):

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            assert result['success'] is False
            assert 'Invalid JSON' in result['error']
            assert 'malformed' in result['error'].lower()


class TestAddHooksToExistingSettings:
    """Test merging Slack hooks with existing settings."""

    def test_merge_with_existing_complex_settings(self):
        """Test merging with complex existing settings structure."""
        existing_settings = {
            'version': '1.0',
            'ui': {
                'theme': 'dark',
                'editor': 'vscode'
            },
            'features': {
                'auto_save': True,
                'syntax_highlighting': True
            },
            'hooks': {
                'prerun': [
                    {
                        'command': 'echo "Starting session"',
                        'description': 'Startup message'
                    }
                ]
            }
        }

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(existing_settings))) as mock_file:

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            # Verify all existing settings preserved
            assert settings['version'] == '1.0'
            assert settings['ui']['theme'] == 'dark'
            assert settings['features']['auto_save'] is True

            # Verify existing hooks preserved
            assert 'prerun' in settings['hooks']
            assert len(settings['hooks']['prerun']) == 1
            assert settings['hooks']['prerun'][0]['command'] == 'echo "Starting session"'

            # Verify Slack hooks added
            assert 'notification' in settings['hooks']
            assert 'posttooluse' in settings['hooks']
            assert 'stop' in settings['hooks']

            assert result['success'] is True

    def test_merge_with_existing_hook_categories(self):
        """Test merging when hook categories already exist."""
        existing_settings = {
            'hooks': {
                'notification': [
                    {
                        'command': 'custom-notification.py',
                        'description': 'Custom notification'
                    }
                ],
                'stop': [
                    {
                        'command': 'cleanup.sh',
                        'description': 'Cleanup script'
                    }
                ]
            }
        }

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(existing_settings))) as mock_file:

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            # Verify existing hooks preserved and Slack hooks added
            assert len(settings['hooks']['notification']) == 2
            assert len(settings['hooks']['stop']) == 2

            # Verify existing hooks still there
            existing_notification = next(
                hook for hook in settings['hooks']['notification']
                if 'custom-notification.py' in hook['command']
            )
            assert existing_notification['description'] == 'Custom notification'

            # Verify Slack hooks added
            slack_notification = next(
                hook for hook in settings['hooks']['notification']
                if 'notification-slack.py' in hook['command']
            )
            assert slack_notification['description'] == 'Send notifications to Slack'

            # Verify new posttooluse category created
            assert 'posttooluse' in settings['hooks']
            assert len(settings['hooks']['posttooluse']) == 1

            assert result['success'] is True


class TestPreserveOtherHooks:
    """Test that non-Slack hooks are preserved during installation."""

    def test_preserve_custom_hooks_different_categories(self):
        """Test preserving custom hooks in different categories."""
        existing_settings = {
            'hooks': {
                'prerun': [
                    {
                        'command': 'setup-env.sh',
                        'description': 'Environment setup'
                    }
                ],
                'postrun': [
                    {
                        'command': 'cleanup.py',
                        'description': 'Post-run cleanup'
                    }
                ],
                'onerror': [
                    {
                        'command': 'error-handler.py',
                        'description': 'Error handling'
                    }
                ]
            }
        }

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(existing_settings))) as mock_file:

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            # Verify all existing hook categories preserved
            assert 'prerun' in settings['hooks']
            assert 'postrun' in settings['hooks']
            assert 'onerror' in settings['hooks']

            # Verify hooks content unchanged
            assert settings['hooks']['prerun'][0]['command'] == 'setup-env.sh'
            assert settings['hooks']['postrun'][0]['command'] == 'cleanup.py'
            assert settings['hooks']['onerror'][0]['command'] == 'error-handler.py'

            # Verify Slack hooks added
            assert 'notification' in settings['hooks']
            assert 'posttooluse' in settings['hooks']
            assert 'stop' in settings['hooks']

            assert result['success'] is True
            assert len(result['hooks_added']) == 3

    def test_preserve_hooks_with_complex_commands(self):
        """Test preserving hooks with complex command structures."""
        existing_settings = {
            'hooks': {
                'notification': [
                    {
                        'command': 'python3 /path/to/custom/notifier.py --config=/etc/notify.conf',
                        'description': 'Complex custom notification',
                        'environment': {
                            'NOTIFY_TOKEN': 'secret',
                            'NOTIFY_CHANNEL': '#alerts'
                        },
                        'timeout': 30,
                        'retry_count': 3
                    }
                ]
            }
        }

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(existing_settings))) as mock_file:

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            # Verify complex hook preserved exactly
            custom_hook = settings['hooks']['notification'][0]
            assert custom_hook['command'] == 'python3 /path/to/custom/notifier.py --config=/etc/notify.conf'
            assert custom_hook['environment']['NOTIFY_TOKEN'] == 'secret'
            assert custom_hook['timeout'] == 30
            assert custom_hook['retry_count'] == 3

            # Verify Slack hook added alongside
            slack_hook = settings['hooks']['notification'][1]
            assert 'notification-slack.py' in slack_hook['command']

            assert result['success'] is True

    def test_detect_existing_slack_hooks(self):
        """Test detection and handling of existing Slack hooks."""
        existing_settings = {
            'hooks': {
                'notification': [
                    {
                        'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py',
                        'description': 'Send notifications to Slack'
                    }
                ],
                'stop': [
                    {
                        'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/stop-slack.py',
                        'description': 'Send session completion notifications to Slack'
                    }
                ]
            }
        }

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=json.dumps(existing_settings))) as mock_file:

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            # Should detect existing Slack hooks and only add missing ones
            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            # Verify no duplicate Slack hooks
            notification_slack_hooks = [
                hook for hook in settings['hooks']['notification']
                if 'notification-slack.py' in hook['command']
            ]
            assert len(notification_slack_hooks) == 1

            # Verify missing posttooluse hook was added
            assert 'posttooluse' in settings['hooks']
            assert len(settings['hooks']['posttooluse']) == 1

            assert result['success'] is True
            assert 'posttooluse' in result['hooks_added']
            assert 'notification' not in result['hooks_added']  # Already existed


class TestHookCommandPaths:
    """Test verification of correct paths with $CLAUDE_PROJECT_DIR."""

    def test_hook_paths_use_project_dir_variable(self):
        """Test that hook commands use $CLAUDE_PROJECT_DIR variable."""
        with patch('os.path.exists', return_value=False), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.makedirs'):

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            # Verify all hook commands use $CLAUDE_PROJECT_DIR
            for hook_type in ['notification', 'posttooluse', 'stop']:
                hook = settings['hooks'][hook_type][0]
                assert hook['command'].startswith('$CLAUDE_PROJECT_DIR/.claude/hooks/')
                assert f'{hook_type}-slack.py' in hook['command']

            assert result['success'] is True

    def test_custom_claude_directory_path(self):
        """Test hook registration with custom Claude directory."""
        custom_path = '/custom/path/.claude'

        with patch('os.path.exists', return_value=False), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.makedirs'):

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration(custom_path)
            result = registrar.register_slack_hooks()

            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            # Verify hooks still use $CLAUDE_PROJECT_DIR (not absolute path)
            for hook_type in ['notification', 'posttooluse', 'stop']:
                hook = settings['hooks'][hook_type][0]
                assert hook['command'].startswith('$CLAUDE_PROJECT_DIR/.claude/hooks/')
                assert custom_path not in hook['command']  # Should not use absolute path

            assert result['success'] is True

    def test_hook_descriptions_correct(self):
        """Test that hook descriptions are appropriate and informative."""
        with patch('os.path.exists', return_value=False), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.makedirs'):

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            expected_descriptions = {
                'notification': 'Send notifications to Slack',
                'posttooluse': 'Send tool usage updates to Slack',
                'stop': 'Send session completion notifications to Slack'
            }

            for hook_type, expected_desc in expected_descriptions.items():
                hook = settings['hooks'][hook_type][0]
                assert hook['description'] == expected_desc

            assert result['success'] is True


class TestSettingsBackup:
    """Test settings file backup functionality."""

    @patch('shutil.copy2')
    @patch('os.path.exists')
    def test_create_backup_before_modification(self, mock_exists, mock_copy):
        """Test that backup is created before modifying settings."""
        mock_exists.return_value = True

        existing_settings = {'version': '1.0', 'hooks': {}}

        with patch('builtins.open', mock_open(read_data=json.dumps(existing_settings))):
            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks(create_backup=True)

            # Verify backup was created
            mock_copy.assert_called_once_with(
                '/home/user/.claude/settings.json',
                '/home/user/.claude/settings.json.backup'
            )

            assert result['success'] is True
            assert result['backup_created'] is True

    @patch('shutil.copy2')
    @patch('os.path.exists')
    def test_backup_with_timestamp(self, mock_exists, mock_copy):
        """Test backup creation with timestamp."""
        mock_exists.return_value = True

        existing_settings = {'version': '1.0', 'hooks': {}}

        with patch('builtins.open', mock_open(read_data=json.dumps(existing_settings))), \
             patch('datetime.datetime') as mock_datetime:

            mock_datetime.now.return_value.strftime.return_value = '20240115_143025'

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks(create_backup=True, timestamp_backup=True)

            # Verify timestamped backup was created
            mock_copy.assert_called_once_with(
                '/home/user/.claude/settings.json',
                '/home/user/.claude/settings.json.backup.20240115_143025'
            )

            assert result['success'] is True
            assert result['backup_created'] is True

    @patch('shutil.copy2')
    @patch('os.path.exists')
    def test_handle_backup_failure(self, mock_exists, mock_copy):
        """Test handling of backup creation failure."""
        mock_exists.return_value = True
        mock_copy.side_effect = PermissionError("Permission denied")

        existing_settings = {'version': '1.0', 'hooks': {}}

        with patch('builtins.open', mock_open(read_data=json.dumps(existing_settings))):
            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks(create_backup=True)

            assert result['success'] is False
            assert 'backup failed' in result['error'].lower()
            assert result['backup_created'] is False

    @patch('os.path.exists')
    def test_backup_not_created_for_new_file(self, mock_exists):
        """Test that backup is not created for new settings file."""
        mock_exists.return_value = False

        with patch('builtins.open', mock_open()) as mock_file, \
             patch('os.makedirs'), \
             patch('shutil.copy2') as mock_copy:

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks(create_backup=True)

            # Should not attempt backup for non-existent file
            mock_copy.assert_not_called()

            assert result['success'] is True
            assert result['backup_created'] is False


class TestRegistrationErrorHandling:
    """Test error handling during hook registration."""

    @patch('os.path.exists')
    def test_handle_file_permission_error(self, mock_exists):
        """Test handling of file permission errors."""
        mock_exists.return_value = True

        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            assert result['success'] is False
            assert 'permission denied' in result['error'].lower()

    @patch('os.path.exists')
    def test_handle_disk_full_error(self, mock_exists):
        """Test handling of disk full errors."""
        mock_exists.return_value = True

        existing_settings = {'version': '1.0'}

        with patch('builtins.open', mock_open(read_data=json.dumps(existing_settings))) as mock_file:
            mock_file().write.side_effect = OSError("No space left on device")

            from tests.system.mock_hook_registration import HookRegistration

            registrar = HookRegistration('/home/user/.claude')
            result = registrar.register_slack_hooks()

            assert result['success'] is False
            assert 'no space left' in result['error'].lower()

    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_handle_directory_creation_error(self, mock_makedirs, mock_exists):
        """Test handling of directory creation errors."""
        mock_exists.return_value = False
        mock_makedirs.side_effect = PermissionError("Permission denied")

        from tests.system.mock_hook_registration import HookRegistration

        registrar = HookRegistration('/home/user/.claude')
        result = registrar.register_slack_hooks()

        assert result['success'] is False
        assert 'failed to create directory' in result['error'].lower()


# Mock implementation for testing

class MockHookRegistration:
    """Mock implementation of hook registration for testing."""

    def __init__(self, claude_dir):
        self.claude_dir = claude_dir
        self.settings_path = os.path.join(claude_dir, 'settings.json')

    def register_slack_hooks(self, create_backup=False, timestamp_backup=False):
        """Mock hook registration method."""
        # This would be implemented based on the actual registration logic
        return {
            'success': True,
            'hooks_added': ['notification', 'posttooluse', 'stop'],
            'backup_created': create_backup
        }


# Create the mock module for import in tests
class MockHookRegistrationModule:
    """Mock module containing HookRegistration class."""
    HookRegistration = MockHookRegistration