"""
Claude Code Slack Integration Test Suite

This package contains comprehensive tests for the Slack integration module.
Tests are organized to validate the contract that slack_utils.py must implement.

Test Structure:
- unit/: Unit tests for individual functions and components
- conftest.py: Shared fixtures and test configuration
- __init__.py: This file, makes tests package importable

Test Categories:
1. URL Validation (test_url_validation.py)
2. Message Formatting (test_webhook_formatting.py)
3. Configuration Management (test_configuration.py)

All tests are designed to initially fail since slack_utils.py doesn't exist yet.
They define the implementation contract and expected behavior.
"""

__version__ = "1.0.0"
__author__ = "Claude Code Team"