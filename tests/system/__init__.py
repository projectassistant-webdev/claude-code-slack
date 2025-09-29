"""
System tests for Claude Code Slack integration.

This package contains comprehensive system tests for the installation and
uninstallation scripts, testing cross-platform compatibility and complete
integration workflows.

Test Categories:
- test_installation_flow.py: Tests for install.sh script functionality
- test_hook_registration.py: Tests for settings.json modification
- test_cross_platform.py: Tests for cross-platform compatibility
- test_uninstallation.py: Tests for uninstall.sh script functionality

Mock Modules:
- mock_install_script.py: Mock implementation of installation functionality
- mock_hook_registration.py: Mock implementation of hook registration
- mock_cross_platform.py: Mock implementation of cross-platform utilities
- mock_uninstall_script.py: Mock implementation of uninstallation functionality

These tests are designed to fail initially since the actual installation and
uninstallation scripts don't exist yet. They serve as specifications for the
expected behavior of these scripts.
"""

# Test markers for pytest
import pytest

# System test configuration
SYSTEM_TEST_CONFIG = {
    'timeout': 30,  # Default timeout for system tests
    'mock_mode': True,  # Use mock implementations by default
    'platforms': ['linux', 'macos', 'wsl'],  # Supported platforms
    'shells': ['bash', 'zsh', 'sh'],  # Supported shells
}

# Common test fixtures and utilities
__all__ = [
    'SYSTEM_TEST_CONFIG',
]