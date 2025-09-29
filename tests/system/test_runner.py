#!/usr/bin/env python3
"""
System test runner for Claude Code Slack integration.

This script runs all system tests and provides detailed reporting on the
installation and uninstallation script requirements.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False


def run_system_tests(test_pattern: str = None, verbose: bool = False) -> Dict[str, Any]:
    """
    Run system tests with optional filtering.

    Args:
        test_pattern: Pattern to filter tests (e.g., 'test_installation*')
        verbose: Enable verbose output

    Returns:
        Dict with test results and summary
    """
    if not PYTEST_AVAILABLE:
        return {
            'exit_code': 1,
            'success': False,
            'error': 'pytest not available - install with: pip install pytest'
        }

    # Get the directory containing this script
    system_tests_dir = Path(__file__).parent

    # Prepare pytest arguments
    pytest_args = [str(system_tests_dir)]

    if test_pattern:
        pytest_args.extend(['-k', test_pattern])

    if verbose:
        pytest_args.append('-v')
    else:
        pytest_args.append('-q')

    # Add markers for system tests
    pytest_args.extend(['-m', 'not slow'])

    # Run pytest and capture results
    exit_code = pytest.main(pytest_args)

    return {
        'exit_code': exit_code,
        'success': exit_code == 0,
        'tests_dir': str(system_tests_dir)
    }


def run_installation_tests() -> Dict[str, Any]:
    """Run only installation-related tests."""
    return run_system_tests('test_installation')


def run_uninstallation_tests() -> Dict[str, Any]:
    """Run only uninstallation-related tests."""
    return run_system_tests('test_uninstallation')


def run_cross_platform_tests() -> Dict[str, Any]:
    """Run only cross-platform compatibility tests."""
    return run_system_tests('test_cross_platform')


def run_hook_registration_tests() -> Dict[str, Any]:
    """Run only hook registration tests."""
    return run_system_tests('test_hook_registration')


def generate_test_report() -> Dict[str, Any]:
    """
    Generate a comprehensive test report showing what functionality
    needs to be implemented.
    """
    test_categories = {
        'Installation Flow': {
            'description': 'Tests for install.sh script functionality',
            'test_file': 'test_installation_flow.py',
            'required_components': [
                'install.sh script',
                'Dependency checking (Python 3.6+, curl/wget)',
                'Directory creation (.claude/hooks/)',
                'Hook file copying and permission setting',
                'Settings.json registration',
                'Local vs global installation modes',
                'Idempotent installation (safe to run multiple times)'
            ]
        },
        'Hook Registration': {
            'description': 'Tests for settings.json modification',
            'test_file': 'test_hook_registration.py',
            'required_components': [
                'Settings.json parsing and modification',
                'Backup creation before changes',
                'Merge with existing hooks (preserve non-Slack hooks)',
                'Path normalization with $CLAUDE_PROJECT_DIR',
                'Error handling for malformed JSON',
                'Validation of hook structure'
            ]
        },
        'Cross-Platform Compatibility': {
            'description': 'Tests for cross-platform installation',
            'test_file': 'test_cross_platform.py',
            'required_components': [
                'macOS installation (Homebrew vs system Python)',
                'Linux installation (various distributions)',
                'WSL compatibility and detection',
                'Path normalization across platforms',
                'Shell compatibility (bash, zsh, sh)',
                'Package manager detection'
            ]
        },
        'Uninstallation': {
            'description': 'Tests for uninstall.sh script functionality',
            'test_file': 'test_uninstallation.py',
            'required_components': [
                'uninstall.sh script',
                'Complete removal of Slack hooks',
                'Settings.json cleanup (remove Slack hooks only)',
                'Configuration backup before removal',
                'Directory cleanup (remove empty directories)',
                'Partial installation handling',
                'Dry-run mode (show what would be removed)'
            ]
        }
    }

    return {
        'test_categories': test_categories,
        'total_categories': len(test_categories),
        'implementation_status': 'Not implemented - tests will fail initially',
        'next_steps': [
            '1. Implement install.sh script with dependency checking',
            '2. Implement hook registration logic in install.sh',
            '3. Add cross-platform compatibility to install.sh',
            '4. Implement uninstall.sh script',
            '5. Add comprehensive error handling and validation',
            '6. Test on multiple platforms (macOS, Linux, WSL)'
        ]
    }


def print_test_report():
    """Print a formatted test report to console."""
    report = generate_test_report()

    print("=" * 80)
    print("CLAUDE CODE SLACK INTEGRATION - SYSTEM TEST REPORT")
    print("=" * 80)
    print()

    print(f"Total Test Categories: {report['total_categories']}")
    print(f"Implementation Status: {report['implementation_status']}")
    print()

    for category, details in report['test_categories'].items():
        print(f"📋 {category}")
        print(f"   Description: {details['description']}")
        print(f"   Test File: {details['test_file']}")
        print("   Required Components:")
        for component in details['required_components']:
            print(f"     • {component}")
        print()

    print("🚀 NEXT STEPS:")
    for i, step in enumerate(report['next_steps'], 1):
        print(f"   {step}")
    print()

    print("📝 NOTE:")
    print("   These tests are designed to fail initially since the installation")
    print("   and uninstallation scripts don't exist yet. They serve as")
    print("   specifications for the expected behavior of these scripts.")
    print()

    print("🧪 RUN TESTS:")
    print("   pytest tests/system/                    # Run all system tests")
    print("   pytest tests/system/test_installation*  # Run installation tests only")
    print("   pytest tests/system/test_uninstall*     # Run uninstallation tests only")
    print("   python tests/system/test_runner.py      # Generate this report")
    print()


def main():
    """Main entry point for the test runner."""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'install':
            result = run_installation_tests()
        elif command == 'uninstall':
            result = run_uninstallation_tests()
        elif command == 'cross-platform':
            result = run_cross_platform_tests()
        elif command == 'hooks':
            result = run_hook_registration_tests()
        elif command == 'all':
            result = run_system_tests(verbose=True)
        elif command == 'report':
            print_test_report()
            return
        else:
            print(f"Unknown command: {command}")
            print("Available commands: install, uninstall, cross-platform, hooks, all, report")
            sys.exit(1)

        print(f"Tests completed with exit code: {result['exit_code']}")
        sys.exit(result['exit_code'])
    else:
        # Default action: show report
        print_test_report()


if __name__ == '__main__':
    main()