"""
Mock implementation of installation script functionality for testing.

This module provides mock implementations of the install.sh script behavior
to enable testing before the actual scripts are implemented.
"""

import os
import json
import subprocess
from unittest.mock import Mock


class MockInstaller:
    """Mock installer class that simulates install.sh behavior."""

    def __init__(self):
        self.python_path = None
        self.download_tool = None
        self.claude_dir = None
        self.hooks_dir = None

    def check_dependencies(self):
        """Mock dependency checking."""
        result = {
            'python_valid': True,
            'python_version': '3.9.0',
            'download_available': True,
            'download_tool': 'curl'
        }
        return result

    def detect_python(self):
        """Mock Python detection."""
        python_paths = ['/usr/bin/python3', '/opt/homebrew/bin/python3', '/usr/local/bin/python3']
        for path in python_paths:
            if os.path.exists(path):
                self.python_path = path
                return {'found': True, 'path': path, 'version': '3.9.0'}
        return {'found': False, 'error': 'Python 3.6+ not found'}

    def detect_download_tool(self):
        """Mock download tool detection."""
        if os.path.exists('/usr/bin/curl'):
            self.download_tool = 'curl'
            return {'tool': 'curl', 'path': '/usr/bin/curl'}
        elif os.path.exists('/usr/bin/wget'):
            self.download_tool = 'wget'
            return {'tool': 'wget', 'path': '/usr/bin/wget'}
        else:
            return {'error': 'No download tool available'}

    def setup_directories(self, claude_dir):
        """Mock directory setup."""
        self.claude_dir = claude_dir
        self.hooks_dir = os.path.join(claude_dir, 'hooks')

        try:
            os.makedirs(claude_dir, exist_ok=True)
            os.makedirs(self.hooks_dir, exist_ok=True)
            return {'success': True, 'directories_created': [claude_dir, self.hooks_dir]}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def install_hooks(self, hook_files):
        """Mock hook installation."""
        installed = []
        for hook in hook_files:
            hook_path = os.path.join(self.hooks_dir, hook)
            # Simulate copying and making executable
            installed.append(hook)

        return {'success': True, 'installed_hooks': installed}

    def register_hooks_in_settings(self):
        """Mock hook registration in settings.json."""
        settings_path = os.path.join(self.claude_dir, 'settings.json')

        # Simulate reading existing settings
        settings = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            except json.JSONDecodeError:
                return {'success': False, 'error': 'Invalid JSON in settings file'}

        # Add hooks
        if 'hooks' not in settings:
            settings['hooks'] = {}

        slack_hooks = {
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

        for hook_type, hook_list in slack_hooks.items():
            if hook_type not in settings['hooks']:
                settings['hooks'][hook_type] = []

            # Check if Slack hook already exists
            existing_commands = [h['command'] for h in settings['hooks'][hook_type]]
            for hook in hook_list:
                if hook['command'] not in existing_commands:
                    settings['hooks'][hook_type].append(hook)

        return {'success': True, 'hooks_registered': list(slack_hooks.keys())}


# Mock functions that simulate the install script behavior

def run_install_script(args=None):
    """Mock function simulating install.sh execution."""
    args = args or []

    # Check for missing dependencies
    if not os.path.exists('/usr/bin/python3') and not os.path.exists('/opt/homebrew/bin/python3'):
        return {
            'success': False,
            'error': 'Python 3.6+ is required but not found',
            'exit_code': 1
        }

    if not os.path.exists('/usr/bin/curl') and not os.path.exists('/usr/bin/wget'):
        return {
            'success': False,
            'error': 'curl or wget is required but not found',
            'exit_code': 1
        }

    # Simulate Python version check
    try:
        result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
        if 'Python 2.' in result.stdout:
            return {
                'success': False,
                'error': 'Python 3.6 or higher is required, found Python 2.x',
                'exit_code': 1
            }
    except FileNotFoundError:
        return {
            'success': False,
            'error': 'Python 3.6+ is required but not found',
            'exit_code': 1
        }

    # Determine installation type
    install_type = 'local'
    if '--global' in args:
        # Check if running as root for global installation
        if os.getuid() != 0:
            return {
                'success': False,
                'error': 'Global installation requires sudo privileges',
                'exit_code': 1
            }
        install_type = 'global'

    # Check for existing installation
    claude_dir = '/home/user/.claude' if install_type == 'local' else '/etc/claude'
    if os.path.exists(os.path.join(claude_dir, 'hooks', 'notification-slack.py')):
        return {
            'success': True,
            'message': 'Slack hooks already installed',
            'install_type': install_type
        }

    # Simulate successful installation
    return {
        'success': True,
        'message': 'Installation completed successfully',
        'install_type': install_type,
        'hooks_installed': ['notification-slack.py', 'posttooluse-slack.py', 'stop-slack.py']
    }


def check_dependencies():
    """Mock function for dependency checking."""
    python_valid = True
    python_version = '3.9.0'
    download_available = True
    download_tool = 'curl'

    if os.path.exists('/usr/bin/python3'):
        try:
            result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
            version_line = result.stdout.strip()
            if 'Python' in version_line:
                version = version_line.split()[1]
                python_version = version
                # Check if version is >= 3.6
                major, minor = map(int, version.split('.')[:2])
                if major < 3 or (major == 3 and minor < 6):
                    python_valid = False
        except:
            python_valid = False
    else:
        python_valid = False

    if os.path.exists('/usr/bin/curl'):
        download_tool = 'curl'
    elif os.path.exists('/usr/bin/wget'):
        download_tool = 'wget'
    else:
        download_available = False
        download_tool = None

    result = {
        'python_valid': python_valid,
        'python_version': python_version,
        'download_available': download_available,
        'download_tool': download_tool
    }

    if not python_valid:
        result['error'] = f'Python 3.6 or higher required, found {python_version}'

    if not download_available:
        result['error'] = 'No download tool available (curl or wget required)'

    return result


def install_hooks(target_dir, hook_files):
    """Mock function for hook installation."""
    try:
        for hook in hook_files:
            hook_path = os.path.join(target_dir, hook)
            # Simulate copying hook file
            # In real implementation, this would copy from source to target
            # and set executable permissions
            pass

        return {
            'success': True,
            'installed_hooks': hook_files
        }
    except PermissionError as e:
        return {
            'success': False,
            'error': f'Permission denied: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def register_hooks(claude_dir):
    """Mock function for hook registration."""
    settings_path = os.path.join(claude_dir, 'settings.json')

    try:
        # Read existing settings
        settings = {}
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                content = f.read()
                if content.strip():
                    settings = json.loads(content)

        # Add hooks section if not exists
        if 'hooks' not in settings:
            settings['hooks'] = {}

        # Define Slack hooks
        slack_hooks = {
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

        hooks_added = []
        for hook_type, hook_list in slack_hooks.items():
            if hook_type not in settings['hooks']:
                settings['hooks'][hook_type] = []

            # Check for existing Slack hooks
            existing_commands = [h.get('command', '') for h in settings['hooks'][hook_type]]
            slack_hook_exists = any('notification-slack.py' in cmd for cmd in existing_commands)

            if not slack_hook_exists:
                settings['hooks'][hook_type].extend(hook_list)
                hooks_added.append(hook_type)

        # Write updated settings (mocked)
        return {
            'success': True,
            'hooks_registered': hooks_added
        }

    except json.JSONDecodeError:
        return {
            'success': False,
            'error': 'Invalid JSON in settings file'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }