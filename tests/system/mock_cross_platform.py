"""
Mock implementation of cross-platform functionality for testing.

This module provides mock implementations of cross-platform utilities
to enable testing before the actual cross-platform logic is implemented.
"""

import os
import platform
import subprocess
from typing import Dict, List, Any, Optional
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath


class CrossPlatformInstaller:
    """Mock cross-platform installer functionality."""

    def __init__(self):
        self.platform_info = {}
        self.detected_paths = {}

    def detect_platform_paths(self) -> Dict[str, str]:
        """Mock platform-specific path detection."""
        system = platform.system()
        user_home = os.path.expanduser('~')

        if system == 'Darwin':  # macOS
            return {
                'platform': 'macOS',
                'claude_dir': os.path.join(user_home, '.claude'),
                'hooks_dir': os.path.join(user_home, '.claude', 'hooks'),
                'python_path': self._detect_macos_python(),
                'download_tool': self._detect_macos_download_tool()
            }
        elif system == 'Linux':
            return {
                'platform': 'Linux',
                'claude_dir': os.path.join(user_home, '.claude'),
                'hooks_dir': os.path.join(user_home, '.claude', 'hooks'),
                'python_path': self._detect_linux_python(),
                'download_tool': self._detect_linux_download_tool()
            }
        else:
            return {
                'platform': 'Unknown',
                'claude_dir': os.path.join(user_home, '.claude'),
                'hooks_dir': os.path.join(user_home, '.claude', 'hooks'),
                'python_path': None,
                'download_tool': None
            }

    def detect_python_installation(self) -> Dict[str, Any]:
        """Mock Python installation detection."""
        system = platform.system()

        if system == 'Darwin':
            # Check Homebrew first, then system Python
            homebrew_python = '/opt/homebrew/bin/python3'
            system_python = '/usr/bin/python3'

            if os.path.exists(homebrew_python):
                return {
                    'python_found': True,
                    'python_path': homebrew_python,
                    'python_version': '3.11.0',
                    'installation_type': 'homebrew'
                }
            elif os.path.exists(system_python):
                return {
                    'python_found': True,
                    'python_path': system_python,
                    'python_version': '3.9.0',
                    'installation_type': 'system'
                }
        elif system == 'Linux':
            if os.path.exists('/usr/bin/python3'):
                return {
                    'python_found': True,
                    'python_path': '/usr/bin/python3',
                    'python_version': '3.10.0',
                    'installation_type': 'system'
                }

        return {
            'python_found': False,
            'error': 'Python 3.6+ not found'
        }

    def detect_download_tool(self) -> Dict[str, str]:
        """Mock download tool detection."""
        if os.path.exists('/usr/bin/curl'):
            return {
                'tool': 'curl',
                'path': '/usr/bin/curl',
                'preference_reason': 'native_macos_tool' if platform.system() == 'Darwin' else 'widely_available'
            }
        elif os.path.exists('/usr/bin/wget'):
            return {
                'tool': 'wget',
                'path': '/usr/bin/wget',
                'preference_reason': 'alternative_download_tool'
            }
        else:
            return {
                'error': 'No download tool found'
            }

    def detect_platform_specific_info(self) -> Dict[str, str]:
        """Mock platform-specific information detection."""
        system = platform.system()

        if system == 'Linux':
            # Mock Linux distribution detection
            return {
                'platform': 'Linux',
                'distribution': 'Ubuntu',
                'version': '22.04',
                'codename': 'jammy',
                'package_manager': 'apt',
                'claude_dir': os.path.expanduser('~/.claude')
            }
        elif system == 'Darwin':
            return {
                'platform': 'macOS',
                'version': '13.0',
                'codename': 'Ventura',
                'package_manager': 'homebrew',
                'claude_dir': os.path.expanduser('~/.claude')
            }
        else:
            return {
                'platform': system,
                'claude_dir': os.path.expanduser('~/.claude')
            }

    def detect_package_manager(self) -> Dict[str, str]:
        """Mock package manager detection."""
        if os.path.exists('/usr/bin/apt'):
            return {
                'package_manager': 'apt',
                'install_command': 'apt install',
                'python_package': 'python3'
            }
        elif os.path.exists('/usr/bin/yum'):
            return {
                'package_manager': 'yum',
                'install_command': 'yum install',
                'python_package': 'python3'
            }
        elif os.path.exists('/usr/bin/dnf'):
            return {
                'package_manager': 'dnf',
                'install_command': 'dnf install',
                'python_package': 'python3'
            }
        elif os.path.exists('/usr/bin/pacman'):
            return {
                'package_manager': 'pacman',
                'install_command': 'pacman -S',
                'python_package': 'python'
            }
        else:
            return {
                'package_manager': 'unknown',
                'error': 'No supported package manager found'
            }

    def detect_snap_python(self) -> Dict[str, Any]:
        """Mock snap Python detection."""
        try:
            # Mock snap list output
            snap_result = subprocess.run(['snap', 'list'], capture_output=True, text=True)
            if 'python3' in snap_result.stdout:
                return {
                    'snap_python_found': True,
                    'python_version': '3.10.12',
                    'python_path': '/snap/bin/python3'
                }
        except FileNotFoundError:
            pass

        return {
            'snap_python_found': False
        }

    def detect_wsl_environment(self) -> Dict[str, Any]:
        """Mock WSL environment detection."""
        if platform.system() != 'Linux':
            return {'is_wsl': False}

        try:
            with open('/proc/version', 'r') as f:
                proc_version = f.read()

            is_wsl = 'Microsoft' in proc_version or 'WSL' in proc_version
            wsl_version = 'WSL2' if 'WSL2' in proc_version else 'WSL1'
            windows_drive_mounted = os.path.exists('/mnt/c')

            return {
                'is_wsl': is_wsl,
                'wsl_version': wsl_version,
                'windows_drive_mounted': windows_drive_mounted
            }
        except FileNotFoundError:
            return {'is_wsl': False}

    def get_wsl_paths(self) -> Dict[str, str]:
        """Mock WSL path handling."""
        user_home = os.path.expanduser('~')
        return {
            'claude_dir': os.path.join(user_home, '.claude'),
            'home_dir': user_home,
            'windows_home': '/mnt/c/Users' if os.path.exists('/mnt/c') else None
        }

    def test_windows_interop(self) -> Dict[str, Any]:
        """Mock Windows interoperability test."""
        try:
            # Mock cmd.exe execution from WSL
            result = subprocess.run(['cmd.exe', '/c', 'ver'], capture_output=True, text=True)
            if result.returncode == 0:
                return {
                    'windows_interop_available': True,
                    'windows_version': result.stdout.strip()
                }
        except FileNotFoundError:
            pass

        return {
            'windows_interop_available': False
        }

    def analyze_wsl_environment(self) -> Dict[str, Any]:
        """Mock WSL environment analysis."""
        wsl_env = {
            'distro_name': os.environ.get('WSL_DISTRO_NAME'),
            'interop_available': os.environ.get('WSL_INTEROP') is not None,
            'wslenv_configured': os.environ.get('WSLENV') is not None
        }

        return wsl_env

    def check_macos_prerequisites(self) -> Dict[str, bool]:
        """Mock macOS prerequisites check."""
        return {
            'xcode_tools_installed': os.path.exists('/Library/Developer/CommandLineTools'),
            'curl_available': os.path.exists('/usr/bin/curl'),
            'prerequisites_met': True
        }

    def _detect_macos_python(self) -> Optional[str]:
        """Mock macOS Python detection."""
        python_paths = [
            '/opt/homebrew/bin/python3',
            '/usr/local/bin/python3',
            '/usr/bin/python3'
        ]

        for path in python_paths:
            if os.path.exists(path):
                return path
        return None

    def _detect_macos_download_tool(self) -> Optional[str]:
        """Mock macOS download tool detection."""
        if os.path.exists('/usr/bin/curl'):
            return '/usr/bin/curl'
        elif os.path.exists('/opt/homebrew/bin/wget'):
            return '/opt/homebrew/bin/wget'
        return None

    def _detect_linux_python(self) -> Optional[str]:
        """Mock Linux Python detection."""
        python_paths = [
            '/usr/bin/python3',
            '/usr/local/bin/python3',
            '/snap/bin/python3'
        ]

        for path in python_paths:
            if os.path.exists(path):
                return path
        return None

    def _detect_linux_download_tool(self) -> Optional[str]:
        """Mock Linux download tool detection."""
        if os.path.exists('/usr/bin/curl'):
            return '/usr/bin/curl'
        elif os.path.exists('/usr/bin/wget'):
            return '/usr/bin/wget'
        return None


class PathNormalizer:
    """Mock path normalization functionality."""

    def __init__(self):
        self.platform = platform.system()

    def normalize_path(self, path: str) -> str:
        """Mock path normalization."""
        # Expand user home directory
        if path.startswith('~'):
            path = os.path.expanduser(path)

        # Convert to absolute path
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        # Normalize path separators and remove redundant separators
        path = os.path.normpath(path)

        return path

    def normalize_separators(self, path: str) -> str:
        """Mock path separator normalization."""
        if self.platform == 'Windows':
            return path.replace('/', '\\')
        else:
            return path.replace('\\', '/')

    def preserve_case(self, path: str) -> str:
        """Mock case preservation."""
        # On case-sensitive filesystems, preserve case
        # On case-insensitive filesystems, might normalize case
        return path

    def handle_special_chars(self, path: str) -> str:
        """Mock special character handling."""
        # Handle spaces and special characters in paths
        # This is a simplified mock implementation
        return path


class ShellCompatibilityChecker:
    """Mock shell compatibility checking."""

    def __init__(self):
        self.supported_shells = ['bash', 'zsh', 'sh', 'dash']

    def detect_shell(self) -> Dict[str, Any]:
        """Mock shell detection."""
        shell_path = os.environ.get('SHELL', '/bin/sh')
        shell_name = os.path.basename(shell_path)

        # Mock version detection
        version_map = {
            'bash': '5.1.16',
            'zsh': '5.8.1',
            'sh': '0.5.11',
            'dash': '0.5.11'
        }

        features_map = {
            'bash': {
                'arrays': True,
                'functions': True,
                'conditionals': True,
                'test_double_bracket': True
            },
            'zsh': {
                'arrays': True,
                'functions': True,
                'conditionals': True,
                'test_double_bracket': True
            },
            'sh': {
                'arrays': False,
                'functions': True,
                'conditionals': True,
                'test_double_bracket': False
            },
            'dash': {
                'arrays': False,
                'functions': True,
                'conditionals': True,
                'test_double_bracket': False
            }
        }

        return {
            'shell_name': shell_name,
            'shell_path': shell_path,
            'version': version_map.get(shell_name, 'unknown'),
            'compatible': shell_name in self.supported_shells,
            'features': features_map.get(shell_name, {})
        }

    def check_shell_features(self, shell_name: str) -> Dict[str, bool]:
        """Mock shell feature checking."""
        feature_sets = {
            'bash': {
                'arrays': True,
                'associative_arrays': True,
                'functions': True,
                'local_variables': True,
                'test_double_bracket': True,
                'process_substitution': True
            },
            'zsh': {
                'arrays': True,
                'associative_arrays': True,
                'functions': True,
                'local_variables': True,
                'test_double_bracket': True,
                'process_substitution': True
            },
            'sh': {
                'arrays': False,
                'associative_arrays': False,
                'functions': True,
                'local_variables': False,
                'test_double_bracket': False,
                'process_substitution': False
            }
        }

        return feature_sets.get(shell_name, {})


class ShellScriptGenerator:
    """Mock shell script generation for different shells."""

    def __init__(self):
        self.templates = {}

    def generate_for_shell(self, shell_type: str) -> str:
        """Mock script generation for specific shell."""
        if shell_type == 'bash':
            return self._generate_bash_script()
        elif shell_type == 'zsh':
            return self._generate_zsh_script()
        elif shell_type in ['sh', 'dash']:
            return self._generate_posix_script()
        else:
            return self._generate_posix_script()  # Default to POSIX

    def generate_export(self, shell_type: str, var_name: str, var_value: str) -> str:
        """Mock environment variable export generation."""
        return f'export {var_name}="{var_value}"'

    def generate_file_check(self, shell_type: str, file_path: str) -> str:
        """Mock file existence check generation."""
        if shell_type == 'bash' or shell_type == 'zsh':
            return f'if [[ -f "{file_path}" ]]; then\n    echo "File exists"\nfi'
        else:  # POSIX sh
            return f'if [ -f "{file_path}" ]; then\n    echo "File exists"\nfi'

    def generate_function_definition(self, shell_type: str, func_name: str, func_body: str) -> str:
        """Mock function definition generation."""
        if shell_type == 'bash':
            return f'function {func_name}() {{\n{func_body}\n}}'
        else:  # POSIX sh and zsh
            return f'{func_name}() {{\n{func_body}\n}}'

    def _generate_bash_script(self) -> str:
        """Generate bash-specific script."""
        return '''#!/bin/bash
function install_hooks() {
    local hooks_dir="$1"
    if [[ -d "$hooks_dir" ]]; then
        echo "Hooks directory exists"
        return 0
    fi
    return 1
}'''

    def _generate_zsh_script(self) -> str:
        """Generate zsh-specific script."""
        return '''#!/bin/zsh
function install_hooks() {
    local hooks_dir="$1"
    if [[ -d "$hooks_dir" ]]; then
        echo "Hooks directory exists"
        return 0
    fi
    return 1
}'''

    def _generate_posix_script(self) -> str:
        """Generate POSIX sh compatible script."""
        return '''#!/bin/sh
install_hooks() {
    hooks_dir="$1"
    if [ -d "$hooks_dir" ]; then
        echo "Hooks directory exists"
        return 0
    fi
    return 1
}'''


# Utility functions for testing

def get_platform_specific_paths() -> Dict[str, str]:
    """Get platform-specific default paths."""
    system = platform.system()
    home = os.path.expanduser('~')

    if system == 'Darwin':  # macOS
        return {
            'home': home,
            'claude_dir': os.path.join(home, '.claude'),
            'python_paths': ['/opt/homebrew/bin/python3', '/usr/bin/python3'],
            'download_tools': ['/usr/bin/curl', '/opt/homebrew/bin/wget']
        }
    elif system == 'Linux':
        return {
            'home': home,
            'claude_dir': os.path.join(home, '.claude'),
            'python_paths': ['/usr/bin/python3', '/usr/local/bin/python3'],
            'download_tools': ['/usr/bin/curl', '/usr/bin/wget']
        }
    else:
        return {
            'home': home,
            'claude_dir': os.path.join(home, '.claude'),
            'python_paths': [],
            'download_tools': []
        }


def simulate_platform_environment(target_platform: str) -> Dict[str, Any]:
    """Simulate different platform environments for testing."""
    environments = {
        'ubuntu_22_04': {
            'platform.system': 'Linux',
            'os.path.exists': {
                '/usr/bin/python3': True,
                '/usr/bin/apt': True,
                '/usr/bin/curl': True
            }
        },
        'macos_ventura': {
            'platform.system': 'Darwin',
            'os.path.exists': {
                '/opt/homebrew/bin/python3': True,
                '/usr/bin/curl': True,
                '/Library/Developer/CommandLineTools': True
            }
        },
        'wsl_ubuntu': {
            'platform.system': 'Linux',
            'os.path.exists': {
                '/proc/version': True,
                '/mnt/c': True,
                '/usr/bin/python3': True
            },
            'file_contents': {
                '/proc/version': 'Linux version 5.4.0-74-generic Microsoft'
            }
        }
    }

    return environments.get(target_platform, {})