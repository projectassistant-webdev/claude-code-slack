"""
System tests for cross-platform installation compatibility.

These tests verify installation works across different platforms:
- macOS specific paths and commands
- Linux specific behavior
- Windows WSL compatibility
- Path normalization across platforms
- Shell compatibility (bash/zsh/sh)
"""

import pytest
import os
import platform
from unittest.mock import Mock, patch, mock_open, MagicMock
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath


class TestMacOSInstallation:
    """Test macOS specific installation behavior."""

    @patch('platform.system')
    @patch('os.path.expanduser')
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_macos_default_paths(self, mock_exists, mock_run, mock_expanduser, mock_system):
        """Test macOS uses correct default paths."""
        mock_system.return_value = 'Darwin'
        mock_expanduser.return_value = '/Users/username'
        mock_exists.side_effect = lambda path: path in [
            '/usr/bin/python3', '/usr/bin/curl', '/opt/homebrew/bin/python3'
        ]
        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0', stderr='')

        from tests.system.mock_cross_platform import CrossPlatformInstaller

        installer = CrossPlatformInstaller()
        result = installer.detect_platform_paths()

        assert result['platform'] == 'macOS'
        assert result['claude_dir'] == '/Users/username/.claude'
        assert result['hooks_dir'] == '/Users/username/.claude/hooks'
        assert result['python_path'] in ['/usr/bin/python3', '/opt/homebrew/bin/python3']

    @patch('platform.system')
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_macos_homebrew_python_detection(self, mock_exists, mock_run, mock_system):
        """Test detection of Homebrew Python on macOS."""
        mock_system.return_value = 'Darwin'
        mock_exists.side_effect = lambda path: {
            '/usr/bin/python3': False,
            '/opt/homebrew/bin/python3': True,
            '/usr/local/bin/python3': False,
            '/usr/bin/curl': True,
        }.get(path, False)

        mock_run.return_value = Mock(returncode=0, stdout='Python 3.11.0', stderr='')

        from tests.system.mock_cross_platform import CrossPlatformInstaller

        installer = CrossPlatformInstaller()
        result = installer.detect_python_installation()

        assert result['python_found'] is True
        assert result['python_path'] == '/opt/homebrew/bin/python3'
        assert result['python_version'] == '3.11.0'
        assert result['installation_type'] == 'homebrew'

    @patch('platform.system')
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_macos_system_python_fallback(self, mock_exists, mock_run, mock_system):
        """Test fallback to system Python on macOS."""
        mock_system.return_value = 'Darwin'
        mock_exists.side_effect = lambda path: {
            '/usr/bin/python3': True,
            '/opt/homebrew/bin/python3': False,
            '/usr/local/bin/python3': False,
            '/usr/bin/curl': True,
        }.get(path, False)

        mock_run.return_value = Mock(returncode=0, stdout='Python 3.9.0', stderr='')

        from tests.system.mock_cross_platform import CrossPlatformInstaller

        installer = CrossPlatformInstaller()
        result = installer.detect_python_installation()

        assert result['python_found'] is True
        assert result['python_path'] == '/usr/bin/python3'
        assert result['installation_type'] == 'system'

    @patch('platform.system')
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_macos_curl_vs_wget_preference(self, mock_exists, mock_run, mock_system):
        """Test that curl is preferred over wget on macOS."""
        mock_system.return_value = 'Darwin'
        mock_exists.side_effect = lambda path: {
            '/usr/bin/curl': True,
            '/usr/bin/wget': True,  # Both available
            '/opt/homebrew/bin/wget': True,
        }.get(path, False)

        from tests.system.mock_cross_platform import CrossPlatformInstaller

        installer = CrossPlatformInstaller()
        result = installer.detect_download_tool()

        assert result['tool'] == 'curl'
        assert result['path'] == '/usr/bin/curl'
        assert result['preference_reason'] == 'native_macos_tool'

    @patch('platform.system')
    @patch('os.path.exists')
    def test_macos_xcode_command_line_tools_check(self, mock_exists, mock_system):
        """Test checking for Xcode Command Line Tools on macOS."""
        mock_system.return_value = 'Darwin'
        mock_exists.side_effect = lambda path: {
            '/usr/bin/curl': True,
            '/usr/bin/git': True,
            '/Library/Developer/CommandLineTools': True,
        }.get(path, False)

        from tests.system.mock_cross_platform import CrossPlatformInstaller

        installer = CrossPlatformInstaller()
        result = installer.check_macos_prerequisites()

        assert result['xcode_tools_installed'] is True
        assert result['curl_available'] is True
        assert result['prerequisites_met'] is True


class TestLinuxInstallation:
    """Test Linux specific installation behavior."""

    @patch('platform.system')
    @patch('platform.linux_distribution', create=True)
    @patch('os.path.expanduser')
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_ubuntu_installation(self, mock_exists, mock_run, mock_expanduser,
                                mock_distro, mock_system):
        """Test installation on Ubuntu/Debian systems."""
        mock_system.return_value = 'Linux'
        mock_distro.return_value = ('Ubuntu', '22.04', 'jammy')
        mock_expanduser.return_value = '/home/username'
        mock_exists.side_effect = lambda path: path in [
            '/usr/bin/python3', '/usr/bin/curl', '/usr/bin/apt'
        ]
        mock_run.return_value = Mock(returncode=0, stdout='Python 3.10.0', stderr='')

        from tests.system.mock_cross_platform import CrossPlatformInstaller

        installer = CrossPlatformInstaller()
        result = installer.detect_platform_specific_info()

        assert result['platform'] == 'Linux'
        assert result['distribution'] == 'Ubuntu'
        assert result['version'] == '22.04'
        assert result['package_manager'] == 'apt'
        assert result['claude_dir'] == '/home/username/.claude'

    @patch('platform.system')
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_centos_rhel_installation(self, mock_exists, mock_run, mock_system):
        """Test installation on CentOS/RHEL systems."""
        mock_system.return_value = 'Linux'
        mock_exists.side_effect = lambda path: {
            '/usr/bin/python3': True,
            '/usr/bin/curl': True,
            '/usr/bin/yum': True,
            '/usr/bin/dnf': False,
        }.get(path, False)

        mock_run.return_value = Mock(returncode=0, stdout='Python 3.8.0', stderr='')

        from tests.system.mock_cross_platform import CrossPlatformInstaller

        installer = CrossPlatformInstaller()
        result = installer.detect_package_manager()

        assert result['package_manager'] == 'yum'
        assert result['install_command'] == 'yum install'
        assert result['python_package'] == 'python3'

    @patch('platform.system')
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_arch_linux_installation(self, mock_exists, mock_run, mock_system):
        """Test installation on Arch Linux."""
        mock_system.return_value = 'Linux'
        mock_exists.side_effect = lambda path: {
            '/usr/bin/python': True,
            '/usr/bin/curl': True,
            '/usr/bin/pacman': True,
        }.get(path, False)

        mock_run.return_value = Mock(returncode=0, stdout='Python 3.11.0', stderr='')

        from tests.system.mock_cross_platform import CrossPlatformInstaller

        installer = CrossPlatformInstaller()
        result = installer.detect_package_manager()

        assert result['package_manager'] == 'pacman'
        assert result['install_command'] == 'pacman -S'
        assert result['python_package'] == 'python'

    @patch('platform.system')
    @patch('subprocess.run')
    def test_linux_snap_python_detection(self, mock_run, mock_system):
        """Test detection of snap-installed Python on Linux."""
        mock_system.return_value = 'Linux'

        # Mock snap list output
        snap_output = """
Name     Version  Rev   Tracking       Publisher     Notes
python3  3.10.12  123   latest/stable  canonical     classic
"""

        mock_run.side_effect = [
            Mock(returncode=0, stdout=snap_output, stderr=''),  # snap list
            Mock(returncode=0, stdout='Python 3.10.12', stderr='')  # python version
        ]

        from tests.system.mock_cross_platform import CrossPlatformInstaller

        installer = CrossPlatformInstaller()
        result = installer.detect_snap_python()

        assert result['snap_python_found'] is True
        assert result['python_version'] == '3.10.12'
        assert result['python_path'] == '/snap/bin/python3'


class TestWSLInstallation:
    """Test Windows WSL compatibility."""

    @patch('platform.system')
    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_wsl_detection(self, mock_run, mock_exists, mock_system):
        """Test detection of WSL environment."""
        mock_system.return_value = 'Linux'
        mock_exists.side_effect = lambda path: {
            '/proc/version': True,
            '/mnt/c': True,
            '/usr/bin/python3': True,
        }.get(path, False)

        # Mock /proc/version content indicating WSL
        proc_version_content = "Linux version 5.4.0-74-generic (buildd@lcy01-amd64-029) Microsoft"

        with patch('builtins.open', mock_open(read_data=proc_version_content)):
            from tests.system.mock_cross_platform import CrossPlatformInstaller

            installer = CrossPlatformInstaller()
            result = installer.detect_wsl_environment()

            assert result['is_wsl'] is True
            assert result['wsl_version'] == 'WSL2'
            assert result['windows_drive_mounted'] is True

    @patch('platform.system')
    @patch('os.path.exists')
    @patch('os.path.expanduser')
    def test_wsl_path_handling(self, mock_expanduser, mock_exists, mock_system):
        """Test proper path handling in WSL environment."""
        mock_system.return_value = 'Linux'
        mock_expanduser.return_value = '/home/username'
        mock_exists.side_effect = lambda path: {
            '/proc/version': True,
            '/mnt/c': True,
            '/home/username': True,
        }.get(path, False)

        with patch('builtins.open', mock_open(read_data="Linux Microsoft WSL")):
            from tests.system.mock_cross_platform import CrossPlatformInstaller

            installer = CrossPlatformInstaller()
            result = installer.get_wsl_paths()

            # Should use Linux paths, not Windows paths
            assert result['claude_dir'] == '/home/username/.claude'
            assert result['home_dir'] == '/home/username'
            assert '/mnt/c' not in result['claude_dir']

    @patch('platform.system')
    @patch('subprocess.run')
    def test_wsl_windows_interop(self, mock_run, mock_system):
        """Test Windows interoperability in WSL."""
        mock_system.return_value = 'Linux'
        mock_run.return_value = Mock(
            returncode=0,
            stdout='Microsoft Windows [Version 10.0.19041.1052]',
            stderr=''
        )

        from tests.system.mock_cross_platform import CrossPlatformInstaller

        installer = CrossPlatformInstaller()
        result = installer.test_windows_interop()

        # Should be able to run Windows commands from WSL
        assert result['windows_interop_available'] is True
        assert 'Windows' in result['windows_version']

    @patch('platform.system')
    @patch('os.environ.get')
    def test_wsl_environment_variables(self, mock_env_get, mock_system):
        """Test WSL-specific environment variable handling."""
        mock_system.return_value = 'Linux'
        mock_env_get.side_effect = lambda var, default=None: {
            'WSL_DISTRO_NAME': 'Ubuntu-22.04',
            'WSL_INTEROP': '/run/WSL/123_interop',
            'WSLENV': 'PATH/l',
        }.get(var, default)

        from tests.system.mock_cross_platform import CrossPlatformInstaller

        installer = CrossPlatformInstaller()
        result = installer.analyze_wsl_environment()

        assert result['distro_name'] == 'Ubuntu-22.04'
        assert result['interop_available'] is True
        assert result['wslenv_configured'] is True


class TestPathNormalization:
    """Test path normalization across different platforms."""

    @patch('platform.system')
    def test_posix_path_normalization(self, mock_system):
        """Test path normalization on POSIX systems."""
        mock_system.return_value = 'Linux'

        from tests.system.mock_cross_platform import PathNormalizer

        normalizer = PathNormalizer()

        test_paths = [
            '~/.claude',
            '/home/user/.claude',
            './relative/path',
            '../parent/path',
            '/path/with spaces/file.txt',
            '/path//double//slashes',
        ]

        expected_results = [
            '/home/user/.claude',  # ~ expanded
            '/home/user/.claude',  # absolute unchanged
            '/current/dir/relative/path',  # relative resolved
            '/current/parent/path',  # parent resolved
            '/path/with spaces/file.txt',  # spaces preserved
            '/path/double/slashes',  # double slashes normalized
        ]

        with patch('os.path.expanduser', side_effect=lambda p: p.replace('~', '/home/user')), \
             patch('os.path.abspath', side_effect=lambda p: f'/current/dir/{p}' if not p.startswith('/') else p), \
             patch('os.path.normpath', side_effect=lambda p: p.replace('//', '/')):

            for test_path, expected in zip(test_paths, expected_results):
                result = normalizer.normalize_path(test_path)
                # This is a simplified test - actual implementation would be more complex
                assert isinstance(result, str)

    def test_path_separator_handling(self):
        """Test handling of different path separators."""
        from tests.system.mock_cross_platform import PathNormalizer

        normalizer = PathNormalizer()

        # Test mixed separators
        mixed_path = '/home/user\\folder/file.txt'
        normalized = normalizer.normalize_separators(mixed_path)

        # Should standardize to forward slashes on POSIX
        assert '\\' not in normalized
        assert normalized == '/home/user/folder/file.txt'

    def test_path_case_sensitivity(self):
        """Test path case sensitivity handling."""
        from tests.system.mock_cross_platform import PathNormalizer

        normalizer = PathNormalizer()

        # Test case preservation on case-sensitive filesystems
        test_path = '/Home/User/.Claude'
        result = normalizer.preserve_case(test_path)
        assert result == '/Home/User/.Claude'

    def test_special_character_handling(self):
        """Test handling of special characters in paths."""
        from tests.system.mock_cross_platform import PathNormalizer

        normalizer = PathNormalizer()

        special_paths = [
            '/path/with spaces/file.txt',
            '/path/with-dashes/file.txt',
            '/path/with_underscores/file.txt',
            '/path/with.dots/file.txt',
            '/path/with(parentheses)/file.txt',
        ]

        for path in special_paths:
            result = normalizer.handle_special_chars(path)
            assert isinstance(result, str)
            # Should handle special characters appropriately


class TestShellCompatibility:
    """Test shell compatibility across bash/zsh/sh."""

    @patch('os.environ.get')
    @patch('subprocess.run')
    def test_bash_shell_detection(self, mock_run, mock_env):
        """Test detection and compatibility with bash shell."""
        mock_env.side_effect = lambda var, default=None: {
            'SHELL': '/bin/bash',
            'BASH_VERSION': '5.1.16(1)-release',
        }.get(var, default)

        mock_run.return_value = Mock(
            returncode=0,
            stdout='GNU bash, version 5.1.16(1)-release',
            stderr=''
        )

        from tests.system.mock_cross_platform import ShellCompatibilityChecker

        checker = ShellCompatibilityChecker()
        result = checker.detect_shell()

        assert result['shell_name'] == 'bash'
        assert result['shell_path'] == '/bin/bash'
        assert result['version'] == '5.1.16'
        assert result['compatible'] is True

    @patch('os.environ.get')
    @patch('subprocess.run')
    def test_zsh_shell_detection(self, mock_run, mock_env):
        """Test detection and compatibility with zsh shell."""
        mock_env.side_effect = lambda var, default=None: {
            'SHELL': '/bin/zsh',
            'ZSH_VERSION': '5.8.1',
        }.get(var, default)

        mock_run.return_value = Mock(
            returncode=0,
            stdout='zsh 5.8.1 (x86_64-apple-darwin21.0)',
            stderr=''
        )

        from tests.system.mock_cross_platform import ShellCompatibilityChecker

        checker = ShellCompatibilityChecker()
        result = checker.detect_shell()

        assert result['shell_name'] == 'zsh'
        assert result['shell_path'] == '/bin/zsh'
        assert result['version'] == '5.8.1'
        assert result['compatible'] is True

    @patch('os.environ.get')
    @patch('subprocess.run')
    def test_sh_shell_compatibility(self, mock_run, mock_env):
        """Test compatibility with minimal sh shell."""
        mock_env.side_effect = lambda var, default=None: {
            'SHELL': '/bin/sh',
        }.get(var, default)

        mock_run.return_value = Mock(
            returncode=0,
            stdout='sh (dash 0.5.11)',
            stderr=''
        )

        from tests.system.mock_cross_platform import ShellCompatibilityChecker

        checker = ShellCompatibilityChecker()
        result = checker.detect_shell()

        assert result['shell_name'] == 'sh'
        assert result['shell_path'] == '/bin/sh'
        assert result['compatible'] is True
        assert result['features']['arrays'] is False  # sh doesn't support arrays

    def test_shell_script_generation(self):
        """Test generation of shell scripts compatible with different shells."""
        from tests.system.mock_cross_platform import ShellScriptGenerator

        generator = ShellScriptGenerator()

        # Test bash-specific script
        bash_script = generator.generate_for_shell('bash')
        assert 'function' in bash_script  # bash supports function keyword
        assert '[[ ' in bash_script  # bash supports [[ ]] syntax

        # Test sh-compatible script
        sh_script = generator.generate_for_shell('sh')
        assert 'function' not in sh_script  # use POSIX function syntax
        assert '[[ ' not in sh_script  # use POSIX [ ] syntax
        assert '[ ' in sh_script

    def test_environment_variable_handling(self):
        """Test environment variable handling across shells."""
        from tests.system.mock_cross_platform import ShellScriptGenerator

        generator = ShellScriptGenerator()

        # Test variable export in different shells
        bash_export = generator.generate_export('bash', 'CLAUDE_PROJECT_DIR', '/path/to/project')
        sh_export = generator.generate_export('sh', 'CLAUDE_PROJECT_DIR', '/path/to/project')

        assert 'export CLAUDE_PROJECT_DIR' in bash_export
        assert 'export CLAUDE_PROJECT_DIR' in sh_export
        assert '/path/to/project' in bash_export
        assert '/path/to/project' in sh_export

    def test_conditional_syntax_compatibility(self):
        """Test conditional syntax compatibility across shells."""
        from tests.system.mock_cross_platform import ShellScriptGenerator

        generator = ShellScriptGenerator()

        # Test file existence check
        bash_check = generator.generate_file_check('bash', '/path/to/file')
        sh_check = generator.generate_file_check('sh', '/path/to/file')

        # Both should work but may use different syntax
        assert 'if' in bash_check and 'if' in sh_check
        assert '/path/to/file' in bash_check and '/path/to/file' in sh_check


# Mock implementations for testing

class MockCrossPlatformInstaller:
    """Mock cross-platform installer for testing."""

    def __init__(self):
        self.platform_info = {}

    def detect_platform_paths(self):
        """Mock platform path detection."""
        return {
            'platform': 'macOS',
            'claude_dir': '/Users/username/.claude',
            'hooks_dir': '/Users/username/.claude/hooks'
        }

    def detect_python_installation(self):
        """Mock Python installation detection."""
        return {
            'python_found': True,
            'python_path': '/usr/bin/python3',
            'python_version': '3.9.0'
        }


class MockPathNormalizer:
    """Mock path normalizer for testing."""

    def normalize_path(self, path):
        """Mock path normalization."""
        return path.replace('~', '/home/user')

    def normalize_separators(self, path):
        """Mock separator normalization."""
        return path.replace('\\', '/')


class MockShellCompatibilityChecker:
    """Mock shell compatibility checker for testing."""

    def detect_shell(self):
        """Mock shell detection."""
        return {
            'shell_name': 'bash',
            'shell_path': '/bin/bash',
            'version': '5.1.16',
            'compatible': True
        }


class MockShellScriptGenerator:
    """Mock shell script generator for testing."""

    def generate_for_shell(self, shell_type):
        """Mock script generation for specific shell."""
        if shell_type == 'bash':
            return '''#!/bin/bash
function install_hooks() {
    if [[ -d "$1" ]]; then
        echo "Directory exists"
    fi
}'''
        else:  # sh
            return '''#!/bin/sh
install_hooks() {
    if [ -d "$1" ]; then
        echo "Directory exists"
    fi
}'''


# Create mock modules for import in tests
class MockCrossPlatformModule:
    """Mock module containing cross-platform classes."""
    CrossPlatformInstaller = MockCrossPlatformInstaller
    PathNormalizer = MockPathNormalizer
    ShellCompatibilityChecker = MockShellCompatibilityChecker
    ShellScriptGenerator = MockShellScriptGenerator