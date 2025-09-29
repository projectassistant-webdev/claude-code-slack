"""
Pytest configuration and fixtures for Slack integration tests.

This file provides common fixtures, mock configurations, and test utilities
that are shared across all test modules in the Slack integration test suite.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime


# Common Test Data Fixtures

@pytest.fixture
def sample_webhook_url():
    """Standard test webhook URL for use across tests."""
    return "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"


@pytest.fixture
def sample_session_id():
    """Standard test session ID."""
    return "test-session-12345"


@pytest.fixture
def sample_project_name():
    """Standard test project name."""
    return "claude-code-test-project"


@pytest.fixture
def sample_timestamp():
    """Standard test timestamp."""
    return "2024-01-15T14:30:25Z"


# Configuration Test Data

@pytest.fixture
def minimal_valid_config(sample_webhook_url):
    """Minimal valid Slack configuration for testing."""
    return {
        "version": "1.0",
        "active": True,
        "webhook_url": sample_webhook_url
    }


@pytest.fixture
def complete_valid_config(sample_webhook_url, sample_project_name):
    """Complete valid Slack configuration with all optional fields."""
    return {
        "version": "1.0",
        "active": True,
        "webhook_url": sample_webhook_url,
        "project_name": sample_project_name,
        "notification_settings": {
            "session_complete": True,
            "input_needed": True,
            "work_in_progress": False,
            "error_notifications": True
        },
        "channel_settings": {
            "default_channel": "#general",
            "mention_users": ["@developer", "@admin"],
            "quiet_hours": {
                "enabled": False,
                "start": "22:00",
                "end": "08:00",
                "timezone": "UTC"
            }
        },
        "message_settings": {
            "format": "block_kit",
            "include_session_id": True,
            "include_project_name": True,
            "max_message_length": 2000
        }
    }


@pytest.fixture
def user_level_config():
    """User-level configuration (global defaults)."""
    return {
        "version": "1.0",
        "notification_settings": {
            "session_complete": True,
            "input_needed": True,
            "work_in_progress": False,
            "error_notifications": True
        },
        "channel_settings": {
            "default_channel": "#general",
            "mention_users": ["@admin"],
            "quiet_hours": {
                "enabled": True,
                "start": "22:00",
                "end": "08:00",
                "timezone": "UTC"
            }
        },
        "message_settings": {
            "format": "block_kit",
            "include_session_id": True,
            "max_message_length": 2000
        }
    }


# Session Data Fixtures

@pytest.fixture
def session_complete_data(sample_session_id, sample_timestamp, sample_project_name):
    """Sample session completion data for testing message formatting."""
    return {
        "session_id": sample_session_id,
        "duration": "45m 23s",
        "commands_executed": 12,
        "files_modified": 3,
        "status": "success",
        "timestamp": sample_timestamp,
        "project_name": sample_project_name,
        "tools_used": ["Write", "Edit", "Bash", "Read", "Grep"],
        "modified_files": ["src/main.py", "tests/test_main.py", "README.md"],
        "summary": "Successfully implemented new feature with tests"
    }


@pytest.fixture
def session_error_data(sample_session_id, sample_timestamp, sample_project_name):
    """Sample session error data for testing error message formatting."""
    return {
        "session_id": sample_session_id,
        "duration": "12m 45s",
        "commands_executed": 8,
        "files_modified": 1,
        "status": "error",
        "error_message": "Tests failed during execution",
        "timestamp": sample_timestamp,
        "project_name": sample_project_name,
        "tools_used": ["Write", "Bash"],
        "modified_files": ["src/buggy_code.py"],
        "exit_code": 1
    }


@pytest.fixture
def input_needed_data(sample_session_id, sample_timestamp, sample_project_name):
    """Sample input needed data for testing input request formatting."""
    return {
        "session_id": sample_session_id,
        "prompt": "Which environment should I deploy to?",
        "context": "Deployment ready for staging or production",
        "timeout": 300,  # 5 minutes
        "options": ["staging", "production", "cancel"],
        "timestamp": sample_timestamp,
        "project_name": sample_project_name,
        "input_type": "selection"
    }


@pytest.fixture
def work_in_progress_data(sample_session_id, sample_timestamp, sample_project_name):
    """Sample work in progress data for testing progress message formatting."""
    return {
        "session_id": sample_session_id,
        "current_task": "Analyzing codebase structure",
        "progress_percentage": 65,
        "estimated_completion": "2m 15s",
        "files_processed": 23,
        "total_files": 45,
        "timestamp": sample_timestamp,
        "project_name": sample_project_name,
        "current_file": "src/complex_module.py"
    }


# Block Kit Test Data

@pytest.fixture
def valid_block_kit_message():
    """Sample valid Block Kit message structure."""
    return {
        "text": "Claude Code Session Completed",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✅ Claude Code Session Completed"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Session ID:*\ntest-session-12345"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Duration:*\n45m 23s"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Commands:*\n12"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Files Modified:*\n3"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Tools Used:* Write, Edit, Bash, Read, Grep"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Completed at 2024-01-15T14:30:25Z"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def interactive_block_kit_message():
    """Sample Block Kit message with interactive elements."""
    return {
        "text": "Claude Code needs your input",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🤔 Input Required"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Which environment should I deploy to?*\n\nDeployment ready for staging or production"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select environment"
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Staging"
                                },
                                "value": "staging"
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Production"
                                },
                                "value": "production"
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Cancel"
                                },
                                "value": "cancel"
                            }
                        ],
                        "action_id": "environment_select"
                    }
                ]
            }
        ]
    }


# Mock and Utility Fixtures

@pytest.fixture
def mock_slack_webhook():
    """Mock Slack webhook client for testing HTTP requests."""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_response.text = "ok"
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_file_operations():
    """Mock file system operations for configuration testing."""
    mocks = {}

    with patch('builtins.open') as mock_open, \
         patch('os.path.exists') as mock_exists, \
         patch('os.makedirs') as mock_makedirs, \
         patch('shutil.copy2') as mock_copy:

        mocks['open'] = mock_open
        mocks['exists'] = mock_exists
        mocks['makedirs'] = mock_makedirs
        mocks['copy'] = mock_copy

        # Default behaviors
        mock_exists.return_value = True

        yield mocks


@pytest.fixture
def temp_config_file(complete_valid_config):
    """Create a temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(complete_valid_config, f, indent=2)
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing file operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    original_env = os.environ.copy()

    # Set up test environment
    test_env = {
        'CLAUDE_PROJECT_DIR': '/test/project',
        'HOME': '/test/home'
    }

    with patch.dict(os.environ, test_env, clear=False):
        yield test_env

    # Restore original environment (patch.dict should handle this automatically)


# URL Validation Test Data

@pytest.fixture
def valid_webhook_urls():
    """Collection of valid Slack webhook URLs for testing."""
    return [
        "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
        "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
        "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
        "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
        "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
    ]


@pytest.fixture
def invalid_webhook_urls():
    """Collection of invalid webhook URLs for testing validation."""
    return [
        # Protocol issues
        "http://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
        "ftp://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",

        # Domain issues
        "https://hooks.discord.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
        "https://example.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
        "https://hooks.slack.co/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",

        # Path structure issues
        "https://hooks.slack.com/webhooks/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
        "https://hooks.slack.com/services/T00000000/B00000000",
        "https://hooks.slack.com/services/T00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
        "https://hooks.slack.com/services/XXXXXXXXXXXXXXXXXXXXXXXX",
        "https://hooks.slack.com/services/",

        # Format issues
        "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX/extra",
        "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
        "https://hooks.slack.com/services/tlowercase/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
        "https://hooks.slack.com/services/T00000000/blowercase/XXXXXXXXXXXXXXXXXXXXXXXX",

        # Invalid values
        "not-a-url",
        "",
        None,
        "   ",
        "https://",
        "slack.com",

        # Query parameters and fragments
        "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX?param=value",
        "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX#fragment"
    ]


# Network Error Simulation

@pytest.fixture
def network_error_scenarios():
    """Network error scenarios for testing error handling."""
    import requests
    import socket

    return {
        'connection_error': requests.exceptions.ConnectionError("Failed to establish connection"),
        'timeout_error': requests.exceptions.Timeout("Request timed out"),
        'ssl_error': requests.exceptions.SSLError("SSL certificate verification failed"),
        'http_error': requests.exceptions.HTTPError("HTTP 500 Internal Server Error"),
        'socket_timeout': socket.timeout("Socket operation timed out"),
        'socket_error': socket.gaierror("Name resolution failed")
    }


@pytest.fixture
def slack_api_error_responses():
    """Slack API error response scenarios."""
    return [
        {
            'status_code': 400,
            'response': {
                'ok': False,
                'error': 'invalid_payload',
                'message': 'Invalid payload format'
            }
        },
        {
            'status_code': 403,
            'response': {
                'ok': False,
                'error': 'action_prohibited',
                'message': 'Posting to this channel is not allowed'
            }
        },
        {
            'status_code': 404,
            'response': {
                'ok': False,
                'error': 'channel_not_found',
                'message': 'Channel not found'
            }
        },
        {
            'status_code': 429,
            'response': {
                'ok': False,
                'error': 'rate_limited',
                'message': 'API rate limit exceeded'
            },
            'headers': {
                'Retry-After': '60'
            }
        },
        {
            'status_code': 500,
            'response': {
                'ok': False,
                'error': 'fatal_error',
                'message': 'Server experienced a fatal error'
            }
        }
    ]


# Test Utilities

@pytest.fixture
def assert_block_kit_valid():
    """Utility function to validate Block Kit structure in tests."""
    def _validate(payload):
        """
        Validate that a payload conforms to basic Block Kit requirements.
        This is a simplified validation for testing purposes.
        """
        assert isinstance(payload, dict), "Payload must be a dictionary"
        assert "text" in payload, "Payload must have 'text' field for fallback"
        assert isinstance(payload["text"], str), "Text field must be a string"

        if "blocks" in payload:
            assert isinstance(payload["blocks"], list), "Blocks must be a list"
            assert len(payload["blocks"]) <= 50, "Maximum 50 blocks allowed"

            for block in payload["blocks"]:
                assert isinstance(block, dict), "Each block must be a dictionary"
                assert "type" in block, "Each block must have a type"
                assert block["type"] in ["header", "section", "context", "actions", "divider"], \
                    f"Invalid block type: {block.get('type')}"

        return True

    return _validate


@pytest.fixture
def create_mock_config_file():
    """Factory function to create mock configuration files for testing."""
    def _create_file(config_data, file_path=None):
        """Create a mock configuration file with given data."""
        if file_path is None:
            file_path = "/test/.claude/slack-config.json"

        mock_file_content = json.dumps(config_data, indent=2)

        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            with patch('os.path.exists', return_value=True):
                return file_path, mock_file_content

    return _create_file


# Pytest Configuration

def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (may require network/file access)"
    )
    config.addinivalue_line(
        "markers",
        "unit: marks tests as unit tests (isolated, no external dependencies)"
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow-running tests"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location and content."""
    for item in items:
        # Mark tests in unit directory as unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark tests in integration directory as integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark tests that use network fixtures as integration tests
        if any(fixture in item.fixturenames for fixture in ['mock_slack_webhook', 'network_error_scenarios']):
            item.add_marker(pytest.mark.integration)


# Cleanup

@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """Automatically clean up test artifacts after each test."""
    yield

    # Clean up any temporary files or state that might have been created
    # This runs after each test automatically due to autouse=True
    pass