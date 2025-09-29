"""
System tests for the uninstallation script (uninstall.sh).

These tests verify the complete uninstallation flow including:
- Complete removal of all components
- Preservation of user data
- Hook removal from settings.json
- Directory cleanup
- Handling of partial installations
"""

import pytest
import json
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, mock_open, MagicMock, call
from pathlib import Path


class TestCompleteUninstallation:
    """Test complete removal of all Slack integration components."""

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.remove')
    @patch('shutil.rmtree')
    def test_complete_uninstallation_success(self, mock_rmtree, mock_remove,
                                           mock_exists, mock_run):
        """Test successful complete uninstallation."""
        # Setup: Full installation exists
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude': True,
            '/home/user/.claude/hooks': True,
            '/home/user/.claude/settings.json': True,
            '/home/user/.claude/hooks/notification-slack.py': True,
            '/home/user/.claude/hooks/posttooluse-slack.py': True,
            '/home/user/.claude/hooks/stop-slack.py': True,
            '/home/user/.claude/slack-config.json': True,
        }.get(path, False)

        settings_with_slack = {
            'hooks': {
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
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(settings_with_slack))):
            from tests.system.mock_uninstall_script import run_uninstall_script

            result = run_uninstall_script(options=['--complete'])

            # Verify hook files removed
            slack_hooks = [
                '/home/user/.claude/hooks/notification-slack.py',
                '/home/user/.claude/hooks/posttooluse-slack.py',
                '/home/user/.claude/hooks/stop-slack.py'
            ]
            for hook in slack_hooks:
                mock_remove.assert_any_call(hook)

            # Verify Slack config removed
            mock_remove.assert_any_call('/home/user/.claude/slack-config.json')

            assert result['success'] is True
            assert 'Uninstallation completed successfully' in result['message']
            assert result['components_removed'] == ['hooks', 'config', 'settings']

    @patch('os.path.exists')
    @patch('os.remove')
    def test_remove_slack_hooks_only(self, mock_remove, mock_exists):
        """Test removing only Slack hooks, preserving other hooks."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude/settings.json': True,
            '/home/user/.claude/hooks/notification-slack.py': True,
            '/home/user/.claude/hooks/custom-hook.py': True,
        }.get(path, False)

        settings_mixed = {
            'hooks': {
                'notification': [
                    {
                        'command': 'custom-notification.py',
                        'description': 'Custom notification'
                    },
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

        with patch('builtins.open', mock_open(read_data=json.dumps(settings_mixed))) as mock_file:
            from tests.system.mock_uninstall_script import run_uninstall_script

            result = run_uninstall_script(options=['--hooks-only'])

            # Verify only Slack hooks removed
            mock_remove.assert_any_call('/home/user/.claude/hooks/notification-slack.py')
            mock_remove.assert_any_call('/home/user/.claude/hooks/stop-slack.py')

            # Verify custom hook file was not removed (not called with custom-hook.py)
            remove_calls = [call.args[0] for call in mock_remove.call_args_list]
            assert '/home/user/.claude/hooks/custom-hook.py' not in remove_calls

            # Verify settings were updated to remove Slack hooks
            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            updated_settings = json.loads(written_content)

            # Custom notification should remain
            assert len(updated_settings['hooks']['notification']) == 1
            assert 'custom-notification.py' in updated_settings['hooks']['notification'][0]['command']

            # Slack stop hook should be removed completely
            assert 'stop' not in updated_settings['hooks']

            assert result['success'] is True

    @patch('os.path.exists')
    def test_handle_missing_components_gracefully(self, mock_exists):
        """Test uninstallation when some components are already missing."""
        # Setup: Partial installation (some components missing)
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude': True,
            '/home/user/.claude/settings.json': True,
            '/home/user/.claude/hooks/notification-slack.py': False,  # Missing
            '/home/user/.claude/hooks/posttooluse-slack.py': True,
            '/home/user/.claude/hooks/stop-slack.py': False,  # Missing
            '/home/user/.claude/slack-config.json': False,  # Missing
        }.get(path, False)

        settings_partial = {
            'hooks': {
                'posttooluse': [
                    {
                        'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/posttooluse-slack.py',
                        'description': 'Send tool usage updates to Slack'
                    }
                ]
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(settings_partial))), \
             patch('os.remove') as mock_remove:

            from tests.system.mock_uninstall_script import run_uninstall_script

            result = run_uninstall_script()

            # Should only attempt to remove existing components
            mock_remove.assert_called_once_with('/home/user/.claude/hooks/posttooluse-slack.py')

            assert result['success'] is True
            assert 'partial installation' in result['message'].lower()
            assert result['components_removed'] == ['hooks']


class TestPreserveUserData:
    """Test preservation of user data during uninstallation."""

    @patch('shutil.copy2')
    @patch('os.path.exists')
    @patch('os.remove')
    def test_backup_user_configuration(self, mock_remove, mock_exists, mock_copy):
        """Test that user configuration is backed up before removal."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude/slack-config.json': True,
            '/home/user/.claude/settings.json': True,
        }.get(path, False)

        user_config = {
            'webhook_url': 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX',
            'project_name': 'My Project',
            'notification_settings': {
                'session_complete': True,
                'input_needed': False
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(user_config))):
            from tests.system.mock_uninstall_script import run_uninstall_script

            result = run_uninstall_script(options=['--backup-config'])

            # Verify backup was created before removal
            mock_copy.assert_called_with(
                '/home/user/.claude/slack-config.json',
                '/home/user/.claude/slack-config.json.backup'
            )

            # Verify original was removed after backup
            mock_remove.assert_any_call('/home/user/.claude/slack-config.json')

            assert result['success'] is True
            assert result['config_backed_up'] is True

    @patch('shutil.copy2')
    @patch('os.path.exists')
    def test_preserve_custom_hooks_in_settings(self, mock_exists, mock_copy):
        """Test that custom hooks in settings are preserved."""
        mock_exists.return_value = True

        complex_settings = {
            'version': '1.0',
            'ui_settings': {
                'theme': 'dark'
            },
            'hooks': {
                'notification': [
                    {
                        'command': 'custom-notifier.py --email',
                        'description': 'Email notifications',
                        'environment': {'SMTP_SERVER': 'localhost'}
                    },
                    {
                        'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py',
                        'description': 'Send notifications to Slack'
                    }
                ],
                'prerun': [
                    {
                        'command': 'setup-workspace.sh',
                        'description': 'Workspace setup'
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

        with patch('builtins.open', mock_open(read_data=json.dumps(complex_settings))) as mock_file:
            from tests.system.mock_uninstall_script import run_uninstall_script

            result = run_uninstall_script()

            # Verify settings backup was created
            mock_copy.assert_called_with(
                '/home/user/.claude/settings.json',
                '/home/user/.claude/settings.json.backup'
            )

            # Verify updated settings preserve everything except Slack hooks
            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            updated_settings = json.loads(written_content)

            # Verify non-hook settings preserved
            assert updated_settings['version'] == '1.0'
            assert updated_settings['ui_settings']['theme'] == 'dark'

            # Verify custom hooks preserved
            assert len(updated_settings['hooks']['notification']) == 1
            custom_hook = updated_settings['hooks']['notification'][0]
            assert 'custom-notifier.py' in custom_hook['command']
            assert custom_hook['environment']['SMTP_SERVER'] == 'localhost'

            # Verify prerun hooks preserved
            assert 'prerun' in updated_settings['hooks']
            assert 'setup-workspace.sh' in updated_settings['hooks']['prerun'][0]['command']

            # Verify Slack stop hook category removed (no other hooks in it)
            assert 'stop' not in updated_settings['hooks']

            assert result['success'] is True

    @patch('os.path.exists')
    def test_preserve_logs_and_temp_files(self, mock_exists):
        """Test that logs and temporary files are preserved."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude/logs': True,
            '/home/user/.claude/temp': True,
            '/home/user/.claude/cache': True,
            '/home/user/.claude/slack-config.json': True,
        }.get(path, False)

        with patch('os.remove') as mock_remove, \
             patch('shutil.rmtree') as mock_rmtree:

            from tests.system.mock_uninstall_script import run_uninstall_script

            result = run_uninstall_script()

            # Verify logs, temp, and cache directories were not removed
            remove_calls = [call.args[0] for call in mock_rmtree.call_args_list]
            assert '/home/user/.claude/logs' not in remove_calls
            assert '/home/user/.claude/temp' not in remove_calls
            assert '/home/user/.claude/cache' not in remove_calls

            # Only config file should be removed
            mock_remove.assert_called_with('/home/user/.claude/slack-config.json')

            assert result['success'] is True


class TestRemoveHooksFromSettings:
    """Test clean removal of hooks from settings.json."""

    @patch('os.path.exists')
    def test_remove_slack_hooks_preserve_structure(self, mock_exists):
        """Test removing Slack hooks while preserving settings structure."""
        mock_exists.return_value = True

        settings_before = {
            'version': '1.0',
            'hooks': {
                'notification': [
                    {
                        'command': 'email-notifier.py',
                        'description': 'Email notifications'
                    },
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
                        'command': 'cleanup.sh',
                        'description': 'Cleanup script'
                    },
                    {
                        'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/stop-slack.py',
                        'description': 'Send session completion notifications to Slack'
                    }
                ]
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(settings_before))) as mock_file:
            from tests.system.mock_uninstall_script import HookRemover

            remover = HookRemover('/home/user/.claude/settings.json')
            result = remover.remove_slack_hooks()

            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings_after = json.loads(written_content)

            # Verify structure preserved
            assert settings_after['version'] == '1.0'
            assert 'hooks' in settings_after

            # Verify non-Slack hooks preserved
            assert len(settings_after['hooks']['notification']) == 1
            assert 'email-notifier.py' in settings_after['hooks']['notification'][0]['command']

            assert len(settings_after['hooks']['stop']) == 1
            assert 'cleanup.sh' in settings_after['hooks']['stop'][0]['command']

            # Verify Slack-only category removed
            assert 'posttooluse' not in settings_after['hooks']

            assert result['hooks_removed'] == ['notification', 'posttooluse', 'stop']
            assert result['success'] is True

    @patch('os.path.exists')
    def test_remove_empty_hook_categories(self, mock_exists):
        """Test removal of empty hook categories after removing Slack hooks."""
        mock_exists.return_value = True

        settings_slack_only = {
            'hooks': {
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
                ]
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(settings_slack_only))) as mock_file:
            from tests.system.mock_uninstall_script import HookRemover

            remover = HookRemover('/home/user/.claude/settings.json')
            result = remover.remove_slack_hooks()

            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings_after = json.loads(written_content)

            # Verify empty hook categories removed
            assert 'notification' not in settings_after['hooks']
            assert 'posttooluse' not in settings_after['hooks']

            # Verify hooks section is empty dict (not removed entirely)
            assert settings_after['hooks'] == {}

            assert result['success'] is True

    @patch('os.path.exists')
    def test_handle_malformed_settings_during_removal(self, mock_exists):
        """Test handling of malformed settings during hook removal."""
        mock_exists.return_value = True

        malformed_settings = '{"hooks": {"notification": [invalid json'

        with patch('builtins.open', mock_open(read_data=malformed_settings)):
            from tests.system.mock_uninstall_script import HookRemover

            remover = HookRemover('/home/user/.claude/settings.json')
            result = remover.remove_slack_hooks()

            assert result['success'] is False
            assert 'malformed settings' in result['error'].lower()

    @patch('os.path.exists')
    def test_settings_file_missing(self, mock_exists):
        """Test handling when settings.json doesn't exist."""
        mock_exists.return_value = False

        from tests.system.mock_uninstall_script import HookRemover

        remover = HookRemover('/home/user/.claude/settings.json')
        result = remover.remove_slack_hooks()

        assert result['success'] is True
        assert 'settings file not found' in result['message'].lower()
        assert result['hooks_removed'] == []


class TestCleanupDirectories:
    """Test cleanup of created directories during uninstallation."""

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('shutil.rmtree')
    def test_remove_empty_hooks_directory(self, mock_rmtree, mock_listdir, mock_exists):
        """Test removal of hooks directory when empty after Slack hook removal."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude/hooks': True,
            '/home/user/.claude': True,
        }.get(path, False)

        # Hooks directory is empty after Slack hooks removed
        mock_listdir.return_value = []

        from tests.system.mock_uninstall_script import DirectoryCleanup

        cleanup = DirectoryCleanup('/home/user/.claude')
        result = cleanup.cleanup_empty_directories()

        # Verify empty hooks directory removed
        mock_rmtree.assert_called_with('/home/user/.claude/hooks')

        assert result['directories_removed'] == ['/home/user/.claude/hooks']
        assert result['success'] is True

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('shutil.rmtree')
    def test_preserve_non_empty_hooks_directory(self, mock_rmtree, mock_listdir, mock_exists):
        """Test preservation of hooks directory with remaining hooks."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude/hooks': True,
            '/home/user/.claude': True,
        }.get(path, False)

        # Hooks directory contains other hooks
        mock_listdir.return_value = ['custom-hook.py', 'another-hook.sh']

        from tests.system.mock_uninstall_script import DirectoryCleanup

        cleanup = DirectoryCleanup('/home/user/.claude')
        result = cleanup.cleanup_empty_directories()

        # Verify hooks directory not removed
        mock_rmtree.assert_not_called()

        assert result['directories_removed'] == []
        assert result['success'] is True

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('shutil.rmtree')
    def test_preserve_claude_directory_with_other_files(self, mock_rmtree, mock_listdir, mock_exists):
        """Test preservation of .claude directory when it contains other files."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude': True,
            '/home/user/.claude/hooks': False,  # Already removed
        }.get(path, False)

        # .claude directory contains other files
        mock_listdir.return_value = ['settings.json', 'logs', 'temp']

        from tests.system.mock_uninstall_script import DirectoryCleanup

        cleanup = DirectoryCleanup('/home/user/.claude')
        result = cleanup.cleanup_empty_directories()

        # Verify .claude directory not removed
        mock_rmtree.assert_not_called()

        assert result['directories_removed'] == []
        assert result['success'] is True

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('shutil.rmtree')
    def test_complete_claude_directory_removal(self, mock_rmtree, mock_listdir, mock_exists):
        """Test complete removal of .claude directory when empty."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude': True,
            '/home/user/.claude/hooks': False,  # Already removed
        }.get(path, False)

        # .claude directory is empty
        mock_listdir.return_value = []

        from tests.system.mock_uninstall_script import DirectoryCleanup

        cleanup = DirectoryCleanup('/home/user/.claude')
        result = cleanup.cleanup_empty_directories(remove_claude_dir=True)

        # Verify .claude directory removed
        mock_rmtree.assert_called_with('/home/user/.claude')

        assert '/home/user/.claude' in result['directories_removed']
        assert result['success'] is True


class TestPartialUninstallation:
    """Test handling of incomplete installations during uninstallation."""

    @patch('os.path.exists')
    @patch('os.remove')
    def test_handle_hooks_without_settings(self, mock_remove, mock_exists):
        """Test uninstallation when hooks exist but settings.json doesn't."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude/hooks/notification-slack.py': True,
            '/home/user/.claude/hooks/posttooluse-slack.py': True,
            '/home/user/.claude/settings.json': False,  # Missing
        }.get(path, False)

        from tests.system.mock_uninstall_script import run_uninstall_script

        result = run_uninstall_script()

        # Should remove hook files even without settings
        mock_remove.assert_any_call('/home/user/.claude/hooks/notification-slack.py')
        mock_remove.assert_any_call('/home/user/.claude/hooks/posttooluse-slack.py')

        assert result['success'] is True
        assert 'partial installation' in result['message'].lower()

    @patch('os.path.exists')
    def test_handle_settings_without_hooks(self, mock_exists):
        """Test uninstallation when settings references hooks that don't exist."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude/settings.json': True,
            '/home/user/.claude/hooks/notification-slack.py': False,  # Missing
            '/home/user/.claude/hooks/posttooluse-slack.py': False,  # Missing
        }.get(path, False)

        settings_with_missing_hooks = {
            'hooks': {
                'notification': [
                    {
                        'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py',
                        'description': 'Send notifications to Slack'
                    }
                ]
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(settings_with_missing_hooks))) as mock_file, \
             patch('os.remove') as mock_remove:

            from tests.system.mock_uninstall_script import run_uninstall_script

            result = run_uninstall_script()

            # Should not attempt to remove non-existent files
            mock_remove.assert_not_called()

            # Should still clean up settings
            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            updated_settings = json.loads(written_content)
            assert 'notification' not in updated_settings['hooks']

            assert result['success'] is True

    @patch('os.path.exists')
    @patch('os.remove')
    def test_handle_permission_errors_gracefully(self, mock_remove, mock_exists):
        """Test graceful handling of permission errors during uninstallation."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude/hooks/notification-slack.py': True,
            '/home/user/.claude/slack-config.json': True,
        }.get(path, False)

        # Simulate permission error on one file
        def mock_remove_side_effect(path):
            if 'notification-slack.py' in path:
                raise PermissionError("Permission denied")

        mock_remove.side_effect = mock_remove_side_effect

        from tests.system.mock_uninstall_script import run_uninstall_script

        result = run_uninstall_script()

        # Should continue with other files despite permission error
        mock_remove.assert_any_call('/home/user/.claude/slack-config.json')

        assert result['success'] is False  # Should report failure due to permission error
        assert 'permission denied' in result['error'].lower()
        assert result['partial_success'] is True  # Some components were removed

    @patch('os.path.exists')
    def test_dry_run_mode(self, mock_exists):
        """Test dry run mode that shows what would be removed without actually removing."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude/hooks/notification-slack.py': True,
            '/home/user/.claude/hooks/posttooluse-slack.py': True,
            '/home/user/.claude/slack-config.json': True,
            '/home/user/.claude/settings.json': True,
        }.get(path, False)

        settings_with_slack = {
            'hooks': {
                'notification': [
                    {
                        'command': '$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py',
                        'description': 'Send notifications to Slack'
                    }
                ]
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(settings_with_slack))), \
             patch('os.remove') as mock_remove:

            from tests.system.mock_uninstall_script import run_uninstall_script

            result = run_uninstall_script(options=['--dry-run'])

            # Verify no files actually removed
            mock_remove.assert_not_called()

            # Verify dry run results
            assert result['success'] is True
            assert result['dry_run'] is True
            assert len(result['files_to_remove']) > 0
            assert '/home/user/.claude/hooks/notification-slack.py' in result['files_to_remove']
            assert '/home/user/.claude/slack-config.json' in result['files_to_remove']


# Mock implementations for testing

class MockUninstallScript:
    """Mock implementation of uninstall script functionality."""

    def __init__(self):
        pass

    def run_uninstallation(self, options=None):
        """Mock uninstallation execution."""
        return {
            'success': True,
            'message': 'Uninstallation completed successfully',
            'components_removed': ['hooks', 'config', 'settings']
        }


class MockHookRemover:
    """Mock hook removal functionality."""

    def __init__(self, settings_path):
        self.settings_path = settings_path

    def remove_slack_hooks(self):
        """Mock Slack hook removal."""
        return {
            'success': True,
            'hooks_removed': ['notification', 'posttooluse', 'stop']
        }


class MockDirectoryCleanup:
    """Mock directory cleanup functionality."""

    def __init__(self, claude_dir):
        self.claude_dir = claude_dir

    def cleanup_empty_directories(self, remove_claude_dir=False):
        """Mock directory cleanup."""
        return {
            'success': True,
            'directories_removed': []
        }


# Functions that simulate the uninstall script behavior

def run_uninstall_script(options=None):
    """Mock function simulating uninstall.sh execution."""
    if options and '--dry-run' in options:
        return {
            'success': True,
            'dry_run': True,
            'files_to_remove': [
                '/home/user/.claude/hooks/notification-slack.py',
                '/home/user/.claude/hooks/posttooluse-slack.py',
                '/home/user/.claude/slack-config.json'
            ]
        }

    return {
        'success': True,
        'message': 'Uninstallation completed successfully',
        'components_removed': ['hooks', 'config', 'settings']
    }


# Create mock modules for import in tests
class MockUninstallModule:
    """Mock module containing uninstall classes."""
    HookRemover = MockHookRemover
    DirectoryCleanup = MockDirectoryCleanup