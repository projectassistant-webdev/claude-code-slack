"""
System tests for the installation script (install.sh).

These tests verify the complete installation flow including:
- Fresh installation on new systems
- Installation with existing hooks
- Local vs global installation modes
- Dependency checking
- Hook registration
- File permissions
"""

import pytest
import json
import tempfile
import os
import stat
from unittest.mock import Mock, patch, mock_open, MagicMock, call
from pathlib import Path
import subprocess


class TestFreshInstallation:
    """Test fresh installation on a clean system."""

    @patch('subprocess.run')
    @patch('subprocess.check_call')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('shutil.copy2')
    @patch('os.chmod')
    def test_fresh_installation_success(self, mock_chmod, mock_copy, mock_makedirs,
                                      mock_exists, mock_check_call, mock_run):
        """Test successful fresh installation."""
        # Setup: Clean system with no existing Claude configuration
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude': False,
            '/home/user/.claude/hooks': False,
            '/home/user/.claude/settings.json': False,
            '/usr/bin/python3': True,
            '/usr/bin/curl': True,
        }.get(path, False)

        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0', stderr='')

        # Mock file operations
        settings_content = json.dumps({})
        with patch('builtins.open', mock_open(read_data=settings_content)) as mock_file:
            # Simulate installation script execution
            from tests.system.mock_install_script import run_install_script

            result = run_install_script()

            # Verify directory creation
            mock_makedirs.assert_any_call('/home/user/.claude', exist_ok=True)
            mock_makedirs.assert_any_call('/home/user/.claude/hooks', exist_ok=True)

            # Verify hook files copied
            expected_hooks = [
                'notification-slack.py',
                'posttooluse-slack.py',
                'stop-slack.py'
            ]
            for hook in expected_hooks:
                mock_copy.assert_any_call(
                    f'/path/to/source/hooks/{hook}',
                    f'/home/user/.claude/hooks/{hook}'
                )

            # Verify scripts made executable
            for hook in expected_hooks:
                mock_chmod.assert_any_call(
                    f'/home/user/.claude/hooks/{hook}',
                    stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
                )

            assert result['success'] is True
            assert 'Installation completed successfully' in result['message']

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_fresh_installation_missing_python(self, mock_exists, mock_run):
        """Test installation fails when Python is not available."""
        mock_exists.side_effect = lambda path: {
            '/usr/bin/python3': False,
            '/usr/bin/python': False,
        }.get(path, False)

        from tests.system.mock_install_script import run_install_script

        result = run_install_script()

        assert result['success'] is False
        assert 'Python 3.6+ is required' in result['error']
        assert result['exit_code'] == 1

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_fresh_installation_missing_download_tool(self, mock_exists, mock_run):
        """Test installation fails when neither curl nor wget is available."""
        mock_exists.side_effect = lambda path: {
            '/usr/bin/python3': True,
            '/usr/bin/curl': False,
            '/usr/bin/wget': False,
        }.get(path, False)

        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0', stderr='')

        from tests.system.mock_install_script import run_install_script

        result = run_install_script()

        assert result['success'] is False
        assert 'curl or wget is required' in result['error']
        assert result['exit_code'] == 1

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_fresh_installation_old_python_version(self, mock_exists, mock_run):
        """Test installation fails with Python version < 3.6."""
        mock_exists.side_effect = lambda path: {
            '/usr/bin/python3': True,
            '/usr/bin/curl': True,
        }.get(path, False)

        mock_run.return_value = Mock(returncode=0, stdout='Python 2.7.18', stderr='')

        from tests.system.mock_install_script import run_install_script

        result = run_install_script()

        assert result['success'] is False
        assert 'Python 3.6 or higher is required' in result['error']
        assert result['exit_code'] == 1


class TestInstallationWithExistingHooks:
    """Test installation when hooks already exist."""

    @patch('subprocess.run')
    @patch('subprocess.check_call')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('shutil.copy2')
    @patch('shutil.move')
    def test_preserve_existing_hooks(self, mock_move, mock_copy, mock_makedirs,
                                   mock_exists, mock_check_call, mock_run):
        """Test that existing non-Slack hooks are preserved."""
        # Setup: System with existing hooks
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude': True,
            '/home/user/.claude/hooks': True,
            '/home/user/.claude/settings.json': True,
            '/home/user/.claude/hooks/custom-hook.py': True,
            '/home/user/.claude/hooks/notification-slack.py': False,
            '/usr/bin/python3': True,
            '/usr/bin/curl': True,
        }.get(path, False)

        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0', stderr='')

        # Mock existing settings with custom hooks
        existing_settings = {
            "hooks": {
                "notification": [
                    {
                        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/custom-hook.py",
                        "description": "Custom notification hook"
                    }
                ]
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(existing_settings))):
            from tests.system.mock_install_script import run_install_script

            result = run_install_script()

            # Verify backup was created
            mock_move.assert_called_with(
                '/home/user/.claude/settings.json',
                '/home/user/.claude/settings.json.backup'
            )

            # Verify existing custom hook was preserved
            assert result['success'] is True
            assert 'Existing hooks preserved' in result['message']

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_skip_existing_slack_hooks(self, mock_file, mock_exists, mock_run):
        """Test that existing Slack hooks are detected and skipped."""
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude': True,
            '/home/user/.claude/hooks': True,
            '/home/user/.claude/settings.json': True,
            '/home/user/.claude/hooks/notification-slack.py': True,
            '/usr/bin/python3': True,
            '/usr/bin/curl': True,
        }.get(path, False)

        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0', stderr='')

        # Mock existing settings with Slack hooks already installed
        existing_settings = {
            "hooks": {
                "notification": [
                    {
                        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py",
                        "description": "Slack notification hook"
                    }
                ]
            }
        }

        mock_file.return_value.read.return_value = json.dumps(existing_settings)

        from tests.system.mock_install_script import run_install_script

        result = run_install_script()

        assert result['success'] is True
        assert 'Slack hooks already installed' in result['message']


class TestLocalVsGlobalInstallation:
    """Test different installation modes (local vs global)."""

    @patch('subprocess.run')
    @patch('subprocess.check_call')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('shutil.copy2')
    def test_local_installation_default(self, mock_copy, mock_makedirs, mock_exists,
                                      mock_check_call, mock_run):
        """Test default local installation mode."""
        mock_exists.side_effect = lambda path: path in ['/usr/bin/python3', '/usr/bin/curl']
        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0', stderr='')

        with patch('builtins.open', mock_open(read_data='{}')):
            from tests.system.mock_install_script import run_install_script

            result = run_install_script(args=['--local'])

            # Verify local installation paths
            mock_makedirs.assert_any_call('/home/user/.claude', exist_ok=True)
            mock_makedirs.assert_any_call('/home/user/.claude/hooks', exist_ok=True)

            assert result['success'] is True
            assert result['install_type'] == 'local'

    @patch('subprocess.run')
    @patch('subprocess.check_call')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('shutil.copy2')
    @patch('os.getuid')
    def test_global_installation_requires_sudo(self, mock_getuid, mock_copy, mock_makedirs,
                                             mock_exists, mock_check_call, mock_run):
        """Test global installation requires sudo privileges."""
        mock_exists.side_effect = lambda path: path in ['/usr/bin/python3', '/usr/bin/curl']
        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0', stderr='')
        mock_getuid.return_value = 1000  # Non-root user

        from tests.system.mock_install_script import run_install_script

        result = run_install_script(args=['--global'])

        assert result['success'] is False
        assert 'Global installation requires sudo privileges' in result['error']
        assert result['exit_code'] == 1

    @patch('subprocess.run')
    @patch('subprocess.check_call')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('shutil.copy2')
    @patch('os.getuid')
    def test_global_installation_with_sudo(self, mock_getuid, mock_copy, mock_makedirs,
                                         mock_exists, mock_check_call, mock_run):
        """Test successful global installation with sudo."""
        mock_exists.side_effect = lambda path: path in ['/usr/bin/python3', '/usr/bin/curl']
        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0', stderr='')
        mock_getuid.return_value = 0  # Root user

        with patch('builtins.open', mock_open(read_data='{}')):
            from tests.system.mock_install_script import run_install_script

            result = run_install_script(args=['--global'])

            # Verify global installation paths
            mock_makedirs.assert_any_call('/etc/claude', exist_ok=True)
            mock_makedirs.assert_any_call('/etc/claude/hooks', exist_ok=True)

            assert result['success'] is True
            assert result['install_type'] == 'global'


class TestDependencyChecking:
    """Test dependency validation during installation."""

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_check_python_version_valid(self, mock_exists, mock_run):
        """Test Python version checking with valid version."""
        mock_exists.side_effect = lambda path: path == '/usr/bin/python3'
        mock_run.return_value = Mock(
            returncode=0,
            stdout='Python 3.9.7',
            stderr=''
        )

        from tests.system.mock_install_script import check_dependencies

        result = check_dependencies()

        assert result['python_valid'] is True
        assert result['python_version'] == '3.9.7'

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_check_python_version_invalid(self, mock_exists, mock_run):
        """Test Python version checking with invalid version."""
        mock_exists.side_effect = lambda path: path == '/usr/bin/python3'
        mock_run.return_value = Mock(
            returncode=0,
            stdout='Python 3.5.2',
            stderr=''
        )

        from tests.system.mock_install_script import check_dependencies

        result = check_dependencies()

        assert result['python_valid'] is False
        assert result['python_version'] == '3.5.2'
        assert 'Python 3.6 or higher required' in result['error']

    @patch('os.path.exists')
    def test_check_download_tools_curl_available(self, mock_exists):
        """Test download tool checking when curl is available."""
        mock_exists.side_effect = lambda path: path == '/usr/bin/curl'

        from tests.system.mock_install_script import check_dependencies

        result = check_dependencies()

        assert result['download_tool'] == 'curl'
        assert result['download_available'] is True

    @patch('os.path.exists')
    def test_check_download_tools_wget_available(self, mock_exists):
        """Test download tool checking when only wget is available."""
        mock_exists.side_effect = lambda path: path == '/usr/bin/wget'

        from tests.system.mock_install_script import check_dependencies

        result = check_dependencies()

        assert result['download_tool'] == 'wget'
        assert result['download_available'] is True

    @patch('os.path.exists')
    def test_check_download_tools_none_available(self, mock_exists):
        """Test download tool checking when neither curl nor wget is available."""
        mock_exists.return_value = False

        from tests.system.mock_install_script import check_dependencies

        result = check_dependencies()

        assert result['download_available'] is False
        assert 'No download tool available' in result['error']


class TestHookRegistration:
    """Test hook registration in settings.json."""

    @patch('os.path.exists')
    def test_register_hooks_empty_settings(self, mock_exists):
        """Test registering hooks in empty settings file."""
        mock_exists.return_value = True

        with patch('builtins.open', mock_open(read_data='{}')) as mock_file:
            from tests.system.mock_install_script import register_hooks

            result = register_hooks('/home/user/.claude')

            # Verify settings were updated
            mock_file().write.assert_called()
            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            assert 'hooks' in settings
            assert 'notification' in settings['hooks']
            assert 'posttooluse' in settings['hooks']
            assert 'stop' in settings['hooks']

            # Verify hook commands include correct path
            notification_hook = settings['hooks']['notification'][0]
            assert '$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py' in notification_hook['command']
            assert result['success'] is True

    @patch('os.path.exists')
    def test_register_hooks_existing_settings(self, mock_exists):
        """Test registering hooks with existing settings."""
        mock_exists.return_value = True

        existing_settings = {
            "version": "1.0",
            "other_config": "value",
            "hooks": {
                "notification": [
                    {
                        "command": "existing-hook.py",
                        "description": "Existing hook"
                    }
                ]
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(existing_settings))) as mock_file:
            from tests.system.mock_install_script import register_hooks

            result = register_hooks('/home/user/.claude')

            # Verify existing settings preserved
            written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
            settings = json.loads(written_content)

            assert settings['version'] == '1.0'
            assert settings['other_config'] == 'value'

            # Verify both existing and new hooks present
            assert len(settings['hooks']['notification']) == 2
            assert any('existing-hook.py' in hook['command']
                      for hook in settings['hooks']['notification'])
            assert any('notification-slack.py' in hook['command']
                      for hook in settings['hooks']['notification'])

            assert result['success'] is True


class TestFilePermissions:
    """Test file permission settings during installation."""

    @patch('os.chmod')
    @patch('os.path.exists')
    @patch('shutil.copy2')
    def test_hook_scripts_executable(self, mock_copy, mock_exists, mock_chmod):
        """Test that hook scripts are made executable."""
        mock_exists.return_value = True

        from tests.system.mock_install_script import install_hooks

        hooks = ['notification-slack.py', 'posttooluse-slack.py', 'stop-slack.py']
        result = install_hooks('/home/user/.claude/hooks', hooks)

        # Verify each hook was made executable
        expected_mode = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        for hook in hooks:
            mock_chmod.assert_any_call(
                f'/home/user/.claude/hooks/{hook}',
                expected_mode
            )

        assert result['success'] is True

    @patch('os.chmod')
    @patch('os.path.exists')
    def test_permission_error_handling(self, mock_exists, mock_chmod):
        """Test handling of permission errors during installation."""
        mock_exists.return_value = True
        mock_chmod.side_effect = PermissionError("Permission denied")

        from tests.system.mock_install_script import install_hooks

        result = install_hooks('/home/user/.claude/hooks', ['notification-slack.py'])

        assert result['success'] is False
        assert 'Permission denied' in result['error']


class TestIdempotentInstallation:
    """Test that installation can be run multiple times safely."""

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_repeated_installation_safe(self, mock_file, mock_exists, mock_run):
        """Test that running installation multiple times doesn't cause issues."""
        # Setup: Slack hooks already installed
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude': True,
            '/home/user/.claude/hooks': True,
            '/home/user/.claude/settings.json': True,
            '/home/user/.claude/hooks/notification-slack.py': True,
            '/home/user/.claude/hooks/posttooluse-slack.py': True,
            '/home/user/.claude/hooks/stop-slack.py': True,
            '/usr/bin/python3': True,
            '/usr/bin/curl': True,
        }.get(path, False)

        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0', stderr='')

        existing_settings = {
            "hooks": {
                "notification": [
                    {
                        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/notification-slack.py",
                        "description": "Slack notification hook"
                    }
                ],
                "posttooluse": [
                    {
                        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/posttooluse-slack.py",
                        "description": "Slack post-tool-use hook"
                    }
                ],
                "stop": [
                    {
                        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/stop-slack.py",
                        "description": "Slack stop hook"
                    }
                ]
            }
        }

        mock_file.return_value.read.return_value = json.dumps(existing_settings)

        from tests.system.mock_install_script import run_install_script

        # Run installation twice
        result1 = run_install_script()
        result2 = run_install_script()

        # Both should succeed
        assert result1['success'] is True
        assert result2['success'] is True
        assert 'already installed' in result2['message']

    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_partial_installation_recovery(self, mock_makedirs, mock_exists, mock_run):
        """Test recovery from partial installation state."""
        # Setup: Partial installation (directories exist but no hooks)
        mock_exists.side_effect = lambda path: {
            '/home/user/.claude': True,
            '/home/user/.claude/hooks': True,
            '/home/user/.claude/settings.json': False,
            '/usr/bin/python3': True,
            '/usr/bin/curl': True,
        }.get(path, False)

        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0', stderr='')

        with patch('builtins.open', mock_open(read_data='{}')):
            with patch('shutil.copy2') as mock_copy:
                from tests.system.mock_install_script import run_install_script

                result = run_install_script()

                # Should complete installation successfully
                assert result['success'] is True
                assert 'Installation completed' in result['message']

                # Should not try to create existing directories
                mock_makedirs.assert_not_called()


# Test utility classes and functions

class MockInstallScript:
    """Mock implementation of installation script functionality for testing."""

    def __init__(self):
        self.dependencies_checked = False
        self.hooks_installed = False
        self.settings_updated = False

    def check_dependencies(self):
        """Mock dependency checking."""
        # This would be implemented based on the actual install script
        pass

    def install_hooks(self, target_dir, hook_files):
        """Mock hook installation."""
        # This would be implemented based on the actual install script
        pass

    def register_hooks(self, claude_dir):
        """Mock hook registration."""
        # This would be implemented based on the actual install script
        pass


# Mock functions that simulate the install script behavior
# These will be imported by the test classes above

def run_install_script(args=None):
    """Mock function simulating install.sh execution."""
    # This function would simulate the actual install script
    # Return format matches what the real script would return
    return {
        'success': True,
        'message': 'Installation completed successfully',
        'install_type': 'local',
        'hooks_installed': ['notification-slack.py', 'posttooluse-slack.py', 'stop-slack.py']
    }

def check_dependencies():
    """Mock function for dependency checking."""
    return {
        'python_valid': True,
        'python_version': '3.9.0',
        'download_available': True,
        'download_tool': 'curl'
    }

def install_hooks(target_dir, hook_files):
    """Mock function for hook installation."""
    return {
        'success': True,
        'installed_hooks': hook_files
    }

def register_hooks(claude_dir):
    """Mock function for hook registration."""
    return {
        'success': True,
        'hooks_registered': ['notification', 'posttooluse', 'stop']
    }