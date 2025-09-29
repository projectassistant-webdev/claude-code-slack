#!/usr/bin/env python3
"""
Simple test runner script for Slack integration tests.

This script demonstrates how to run the tests and what to expect
before and after implementing slack_utils.py.
"""

import sys
import subprocess
import os
from pathlib import Path

def main():
    """Run the Slack integration tests."""

    # Parse command line arguments
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"

    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print("=" * 80)
    print("Claude Code Slack Integration Test Suite")
    print("=" * 80)
    print()

    # Check if pytest is available
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", "--version"],
                              capture_output=True, text=True, check=True)
        print(f"✓ pytest found: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ pytest not found. Install with:")
        print("  pip install -r tests/requirements.txt")
        print()
        print("Alternatively, check test structure manually:")
        manual_check()
        return 1

    print()

    # Determine which tests to run
    if test_type == "system":
        print("Running SYSTEM tests (installation/uninstallation scripts)...")
        test_path = "tests/system/"
        print("NOTE: These tests are expected to FAIL until install.sh and uninstall.sh are implemented")
    elif test_type == "unit":
        print("Running UNIT tests (slack_utils.py functionality)...")
        test_path = "tests/unit/"
        print("NOTE: These tests are expected to FAIL until slack_utils.py is implemented")
    elif test_type == "integration":
        print("Running INTEGRATION tests (hook functionality)...")
        test_path = "tests/integration/"
        print("NOTE: These tests require working slack_utils.py implementation")
    else:
        print("Running ALL tests...")
        test_path = "tests/"
        print("NOTE: Tests will fail until corresponding components are implemented")

    print("-" * 80)

    # Run tests with verbose output
    test_command = [
        sys.executable, "-m", "pytest",
        test_path,
        "-v",
        "--tb=short",
        "--no-header"
    ]

    try:
        result = subprocess.run(test_command, check=False)
        print()
        print("-" * 80)

        if result.returncode == 0:
            print("✓ All tests PASSED!")
            if test_type == "system":
                print("  Installation and uninstallation scripts are working correctly")
            elif test_type == "unit":
                print("  slack_utils.py is properly implemented")
            elif test_type == "integration":
                print("  Hook integration is working correctly")
            else:
                print("  All components are properly implemented")
        else:
            print("✗ Tests FAILED")
            if test_type == "system":
                print("  Implement install.sh and uninstall.sh scripts")
                print("  Run: python tests/system/test_runner.py report")
            elif test_type == "unit":
                print("  Implement functions in commands/slack/slack_utils.py")
            elif test_type == "integration":
                print("  Check slack_utils.py implementation and hook files")
            else:
                print("  Check which test categories are failing and implement accordingly")

        return result.returncode

    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def manual_check():
    """Manually check test file structure when pytest is not available."""
    print("Manual test structure verification:")
    print()

    test_files = [
        "tests/unit/test_url_validation.py",
        "tests/unit/test_webhook_formatting.py",
        "tests/unit/test_configuration.py",
        "tests/conftest.py"
    ]

    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"✓ {test_file}")

            # Count test functions
            with open(test_file, 'r') as f:
                content = f.read()
                test_count = content.count("def test_")
                class_count = content.count("class Test")
                print(f"  - {class_count} test classes, {test_count} test functions")
        else:
            print(f"✗ {test_file} - Missing")

    print()
    print("Expected behavior:")
    print("- All tests should raise NotImplementedError before implementation")
    print("- Tests define the contract for slack_utils.py functions")
    print("- After implementation, tests should pass and validate functionality")
    print()
    print("Test categories:")
    print("- Unit tests: slack_utils.py functionality")
    print("- Integration tests: hook functionality")
    print("- System tests: installation/uninstallation scripts")
    print()
    print("Usage:")
    print("  python tests/run_tests.py              # Run all tests")
    print("  python tests/run_tests.py unit         # Run unit tests only")
    print("  python tests/run_tests.py integration  # Run integration tests only")
    print("  python tests/run_tests.py system       # Run system tests only")


if __name__ == "__main__":
    sys.exit(main())