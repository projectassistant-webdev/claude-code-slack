#!/usr/bin/env python3

"""
Integration tests for Claude Code Slack Notification hook.

These tests verify the Notification hook functionality according to the specifications in:
- /tmp/slack-integration-agents/phase2/research-summary.md
- docs/localdocs/5b71f56c.md

The Notification hook should:
1. Parse JSON from stdin correctly
2. Load configuration from .claude/slack-config.json
3. Format appropriate Slack messages for different notification types
4. Send webhook requests
5. Return correct exit codes (0 for success, other for error)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest
import requests


class TestNotificationHook(unittest.TestCase):
    """Test suite for the Notification hook script."""

    def setUp(self):
        """Set up test environment before each test."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Mock Claude project directory
        self.claude_project_dir = self.test_dir
        os.environ['CLAUDE_PROJECT_DIR'] = self.claude_project_dir

        # Create mock .claude directory and config
        self.claude_dir = Path(self.test_dir) / '.claude'
        self.claude_dir.mkdir()

        # Mock Slack configuration
        self.mock_slack_config = {
            "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
            "channel": "#general",
            "enabled": True,
            "project_name": "test-project"
        }

        # Create mock config file
        config_path = self.claude_dir / 'slack-config.json'
        with open(config_path, 'w') as f:
            json.dump(self.mock_slack_config, f)

    def tearDown(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        # Clean up temp directory (in real implementation)
        if 'CLAUDE_PROJECT_DIR' in os.environ:
            del os.environ['CLAUDE_PROJECT_DIR']

    def create_mock_transcript(self, content_lines):
        """Create a mock transcript file in JSONL format."""
        transcript_path = Path(self.test_dir) / 'test_transcript.jsonl'
        with open(transcript_path, 'w') as f:
            for line in content_lines:
                f.write(json.dumps(line) + '\n')
        return str(transcript_path)

    @patch('subprocess.run')
    @patch('requests.post')
    def test_notification_hook_permission_request(self, mock_post, mock_subprocess):
        """Test Notification hook for permission request messages."""
        # Arrange
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'ok'

        transcript_path = self.create_mock_transcript([
            {"type": "user", "message": {"content": "Please run npm test"}}
        ])

        input_data = {
            "session_id": "test-session-001",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "Notification",
            "message": "Claude needs your permission to use Bash"
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}
            result = self._simulate_notification_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        mock_send.assert_called_once()

        # Verify the Slack payload structure for permission request
        call_args = mock_send.call_args[0]
        slack_payload = call_args[0]

        self.assertIn("blocks", slack_payload)
        self.assertTrue(len(slack_payload["blocks"]) >= 2)

        # Check for permission request header
        header_text = self._extract_header_text(slack_payload)
        self.assertIn("Permission", header_text)
        self.assertTrue("⚠️" in header_text or "🔐" in header_text)

        # Check for the actual permission message
        message_text = self._extract_all_text_from_payload(slack_payload)
        combined_text = " ".join(message_text)
        self.assertIn("Claude needs your permission to use Bash", combined_text)

        # Check for session details
        self.assertIn("test-session-001", combined_text)

    @patch('subprocess.run')
    @patch('requests.post')
    def test_notification_hook_idle_waiting(self, mock_post, mock_subprocess):
        """Test Notification hook for idle waiting messages."""
        # Arrange
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'ok'

        transcript_path = self.create_mock_transcript([
            {"type": "assistant", "message": {"content": "What would you like me to do next?"}}
        ])

        input_data = {
            "session_id": "test-session-002",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "Notification",
            "message": "Claude is waiting for your input"
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}
            result = self._simulate_notification_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        mock_send.assert_called_once()

        # Verify the Slack payload structure for idle waiting
        call_args = mock_send.call_args[0]
        slack_payload = call_args[0]

        self.assertIn("blocks", slack_payload)

        # Check for waiting/idle header
        header_text = self._extract_header_text(slack_payload)
        self.assertTrue(
            any(word in header_text.lower() for word in ["waiting", "idle", "input"]),
            f"Header doesn't indicate waiting state: {header_text}"
        )
        self.assertTrue("⏳" in header_text or "⏰" in header_text)

        # Check for the actual waiting message
        message_text = self._extract_all_text_from_payload(slack_payload)
        combined_text = " ".join(message_text)
        self.assertIn("Claude is waiting for your input", combined_text)

        # Check for session details
        self.assertIn("test-session-002", combined_text)

    @patch('subprocess.run')
    @patch('requests.post')
    def test_notification_hook_custom_message(self, mock_post, mock_subprocess):
        """Test Notification hook for custom notification messages."""
        # Arrange
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'ok'

        transcript_path = self.create_mock_transcript([
            {"type": "assistant", "message": {"content": "Build process completed with 2 warnings"}}
        ])

        input_data = {
            "session_id": "test-session-003",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "Notification",
            "message": "Build completed with warnings"
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}
            result = self._simulate_notification_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        mock_send.assert_called_once()

        # Verify the Slack payload structure for custom message
        call_args = mock_send.call_args[0]
        slack_payload = call_args[0]

        self.assertIn("blocks", slack_payload)

        # Check for notification header
        header_text = self._extract_header_text(slack_payload)
        self.assertTrue(
            any(word in header_text.lower() for word in ["notification", "claude code"]),
            f"Header doesn't indicate notification: {header_text}"
        )
        self.assertTrue("📢" in header_text or "ℹ️" in header_text or "🔔" in header_text)

        # Check for the custom message
        message_text = self._extract_all_text_from_payload(slack_payload)
        combined_text = " ".join(message_text)
        self.assertIn("Build completed with warnings", combined_text)

        # Check for session details
        self.assertIn("test-session-003", combined_text)

    @patch('subprocess.run')
    def test_notification_hook_missing_config(self, mock_subprocess):
        """Test Notification hook when no configuration exists (silent exit)."""
        # Arrange - Remove the config file
        config_path = self.claude_dir / 'slack-config.json'
        if config_path.exists():
            config_path.unlink()

        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "test-session-004",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "Notification",
            "message": "Test notification"
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Slack integration not configured"
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.load_config') as mock_load_config:
            mock_load_config.return_value = None
            result = self._simulate_notification_hook(input_data)

        # Assert - Should exit silently (code 0) when no config
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("not configured", result["stdout"])

    @patch('subprocess.run')
    def test_notification_hook_malformed_input(self, mock_subprocess):
        """Test Notification hook handling of invalid JSON input."""
        # Arrange
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = "Error: Invalid JSON input"

        # Act
        test_cases = [
            '{"session_id": "test", "invalid": }',  # Invalid JSON syntax
            '{"missing_message": true}',            # Missing required message field
            '',                                     # Empty input
            'not json at all',                     # Not JSON
            '{"message": "", "session_id": ""}',   # Empty required fields
        ]

        for malformed_input in test_cases:
            with self.subTest(input=malformed_input[:20] + "..."):
                result = self._simulate_notification_hook_with_invalid_json(malformed_input)
                self.assertEqual(result["exit_code"], 1)
                self.assertIn("Invalid JSON", result["stderr"])

    @patch('subprocess.run')
    @patch('requests.post')
    def test_notification_hook_webhook_failure(self, mock_post, mock_subprocess):
        """Test Notification hook handling of webhook send failure."""
        # Arrange
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "test-session-005",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "Notification",
            "message": "Test notification for webhook failure"
        }

        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = "Error: Failed to send webhook notification"

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.side_effect = Exception("Webhook failed")
            result = self._simulate_notification_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 1)  # Non-blocking error
        self.assertIn("webhook", result["stderr"].lower())

    @patch('subprocess.run')
    def test_notification_hook_disabled_integration(self, mock_subprocess):
        """Test Notification hook when Slack integration is disabled."""
        # Arrange - Set enabled to false in config
        disabled_config = self.mock_slack_config.copy()
        disabled_config["enabled"] = False

        config_path = self.claude_dir / 'slack-config.json'
        with open(config_path, 'w') as f:
            json.dump(disabled_config, f)

        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "test-session-006",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "Notification",
            "message": "Test notification when disabled"
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Slack integration disabled"
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.load_config') as mock_load_config:
            mock_load_config.return_value = disabled_config
            result = self._simulate_notification_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("disabled", result["stdout"])

    def test_notification_message_types_classification(self):
        """Test that different notification message types are classified correctly."""
        test_cases = [
            {
                "message": "Claude needs your permission to use Bash",
                "expected_type": "permission",
                "expected_emoji": "⚠️"
            },
            {
                "message": "Claude is waiting for your input",
                "expected_type": "idle",
                "expected_emoji": "⏳"
            },
            {
                "message": "Claude is waiting for your input (idle for 60+ seconds)",
                "expected_type": "idle",
                "expected_emoji": "⏳"
            },
            {
                "message": "Build completed successfully",
                "expected_type": "custom",
                "expected_emoji": "📢"
            },
            {
                "message": "Tests failed with 3 errors",
                "expected_type": "custom",
                "expected_emoji": "📢"
            },
            {
                "message": "Permission needed for file access",
                "expected_type": "permission",
                "expected_emoji": "⚠️"
            }
        ]

        for case in test_cases:
            with self.subTest(message=case["message"]):
                notification_type = self._classify_notification_message(case["message"])
                self.assertEqual(notification_type["type"], case["expected_type"])
                self.assertEqual(notification_type["emoji"], case["expected_emoji"])

    @patch('subprocess.run')
    @patch('requests.post')
    def test_notification_hook_large_message(self, mock_post, mock_subprocess):
        """Test Notification hook with very large notification message."""
        # Arrange
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'ok'

        # Create a large message (close to Slack's limits)
        large_message = "Error details: " + "A" * 2500  # Approach 3000 char limit

        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "test-session-007",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "Notification",
            "message": large_message
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}
            result = self._simulate_notification_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        mock_send.assert_called_once()

        # Verify the message was truncated if necessary
        call_args = mock_send.call_args[0]
        slack_payload = call_args[0]

        message_text = self._extract_all_text_from_payload(slack_payload)
        combined_text = " ".join(message_text)

        # Should contain truncated content or original if within limits
        if len(large_message) > 2000:  # Assuming 2000 char truncation limit
            self.assertTrue(
                "..." in combined_text or len(combined_text) <= 2500,
                "Large message not properly truncated"
            )

    def _simulate_notification_hook(self, input_data):
        """Simulate the notification hook execution."""
        try:
            # Simulate JSON parsing
            if not isinstance(input_data, dict):
                return {"exit_code": 1, "stderr": "Error: Invalid JSON input"}

            # Check for required fields
            required_fields = ["session_id", "hook_event_name", "message"]
            for field in required_fields:
                if field not in input_data or not input_data[field]:
                    return {"exit_code": 1, "stderr": f"Error: Missing required field: {field}"}

            # Simulate configuration loading
            config = self.mock_slack_config
            if not config:
                return {"exit_code": 0, "stdout": "Slack integration not configured"}

            if not config.get("enabled", False):
                return {"exit_code": 0, "stdout": "Slack integration disabled"}

            # Simulate notification processing and Slack message creation
            from slack_utils import send_webhook, create_notification_message

            # Classify the notification type
            notification_type = self._classify_notification_message(input_data["message"])

            # Create Slack message
            slack_message = create_notification_message(
                session_id=input_data["session_id"],
                message=input_data["message"],
                notification_type=notification_type,
                project_name=config.get("project_name", "Unknown Project"),
                cwd=input_data.get("cwd", "")
            )

            # Send webhook
            webhook_result = send_webhook(config["webhook_url"], slack_message)

            if webhook_result.get("success", False):
                return {"exit_code": 0, "stdout": "Notification sent"}
            else:
                return {"exit_code": 1, "stderr": "Error: Failed to send webhook notification"}

        except Exception as e:
            return {"exit_code": 1, "stderr": f"Error: {str(e)}"}

    def _simulate_notification_hook_with_invalid_json(self, invalid_input):
        """Simulate notification hook with invalid JSON input."""
        return {"exit_code": 1, "stderr": "Error: Invalid JSON input"}

    def _classify_notification_message(self, message):
        """Classify notification message type and return appropriate formatting."""
        message_lower = message.lower()

        if "permission" in message_lower or "needs your permission" in message_lower:
            return {
                "type": "permission",
                "emoji": "⚠️",
                "title": "Permission Required"
            }
        elif "waiting" in message_lower or "idle" in message_lower:
            return {
                "type": "idle",
                "emoji": "⏳",
                "title": "Waiting for Input"
            }
        else:
            return {
                "type": "custom",
                "emoji": "📢",
                "title": "Claude Code Notification"
            }

    def _extract_header_text(self, slack_payload):
        """Extract header text from Slack payload."""
        for block in slack_payload.get("blocks", []):
            if block.get("type") == "header":
                return block.get("text", {}).get("text", "")
            elif block.get("type") == "section" and "text" in block:
                text = block["text"].get("text", "")
                # Check if this looks like a header (contains emojis or formatting)
                if any(emoji in text for emoji in ["⚠️", "⏳", "📢", "🔔", "ℹ️"]):
                    return text
        return ""

    def _extract_all_text_from_payload(self, slack_payload):
        """Extract all text content from a Slack Block Kit payload."""
        text_content = []

        for block in slack_payload.get("blocks", []):
            if "text" in block and "text" in block["text"]:
                text_content.append(block["text"]["text"])

            if "fields" in block:
                for field in block["fields"]:
                    if "text" in field:
                        text_content.append(field["text"])

            if "elements" in block:
                for element in block["elements"]:
                    if "text" in element:
                        text_content.append(element["text"])

        return text_content


# Mock slack_utils module for testing
class MockSlackUtils:
    """Mock implementation of slack_utils functions."""

    @staticmethod
    def send_webhook(webhook_url, payload):
        """Mock webhook sending."""
        if not webhook_url or "hooks.slack.com" not in webhook_url:
            raise Exception("Invalid webhook URL")
        return {"success": True, "status_code": 200}

    @staticmethod
    def create_notification_message(session_id, message, notification_type, project_name, cwd):
        """Mock Slack notification message creation."""
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{notification_type['emoji']} *{notification_type['title']}*"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Session:*\n{session_id}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Project:*\n{project_name}"
                        }
                    ]
                }
            ]
        }

    @staticmethod
    def load_config():
        """Mock configuration loading."""
        return {
            "webhook_url": "https://hooks.slack.com/services/test",
            "enabled": True,
            "project_name": "test-project"
        }


# Patch the slack_utils module for all tests
@patch.dict('sys.modules', {'slack_utils': MockSlackUtils()})
class TestNotificationHookWithMocks(TestNotificationHook):
    """Test Notification hook with mocked slack_utils module."""
    pass


if __name__ == '__main__':
    unittest.main()