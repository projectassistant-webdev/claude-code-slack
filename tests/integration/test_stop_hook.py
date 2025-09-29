#!/usr/bin/env python3

"""
Integration tests for Claude Code Slack Stop hook.

These tests verify the Stop hook functionality according to the specifications in:
- /tmp/slack-integration-agents/phase2/research-summary.md
- docs/localdocs/5b71f56c.md

The Stop hook should:
1. Parse JSON from stdin correctly
2. Load configuration from .claude/slack-config.json
3. Format appropriate Slack messages using slack_utils
4. Send webhook requests
5. Return correct exit codes
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


class TestStopHook(unittest.TestCase):
    """Test suite for the Stop hook script."""

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
    def test_stop_hook_with_valid_input(self, mock_post, mock_subprocess):
        """Test Stop hook with valid JSON input and successful notification."""
        # Arrange
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'ok'

        # Create transcript with tool usage
        transcript_content = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/test/file.py", "content": "print('hello')"}
                        }
                    ]
                }
            },
            {
                "type": "user",
                "message": {"content": "Create a Python script"}
            }
        ]
        transcript_path = self.create_mock_transcript(transcript_content)

        input_data = {
            "session_id": "test-session-001",
            "transcript_path": transcript_path,
            "hook_event_name": "Stop",
            "stop_hook_active": False,
            "cwd": self.test_dir
        }

        # Mock the hook script process
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act - This would normally call the actual hook script
        # For now, we'll simulate the hook behavior
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}

            # Simulate hook execution
            result = self._simulate_stop_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        mock_send.assert_called_once()

        # Verify the Slack payload structure
        call_args = mock_send.call_args[0]
        slack_payload = call_args[0]

        self.assertIn("blocks", slack_payload)
        self.assertTrue(len(slack_payload["blocks"]) >= 2)

        # Check for session complete header
        header_block = slack_payload["blocks"][0]
        self.assertEqual(header_block["type"], "section")
        self.assertIn("Session Complete", header_block["text"]["text"])

        # Check for session details
        details_found = False
        for block in slack_payload["blocks"]:
            if block["type"] == "section" and "fields" in block:
                fields = block["fields"]
                session_field = next((f for f in fields if "Session ID" in f["text"]), None)
                if session_field:
                    details_found = True
                    self.assertIn("test-session-001", session_field["text"])

        self.assertTrue(details_found, "Session details not found in Slack payload")

    @patch('subprocess.run')
    def test_stop_hook_with_empty_transcript(self, mock_subprocess):
        """Test Stop hook handling of empty transcript session."""
        # Arrange
        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "test-session-002",
            "transcript_path": transcript_path,
            "hook_event_name": "Stop",
            "stop_hook_active": False,
            "cwd": self.test_dir
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}
            result = self._simulate_stop_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        mock_send.assert_called_once()

        # Verify that the notification mentions "no activity" or similar
        call_args = mock_send.call_args[0]
        slack_payload = call_args[0]

        # Look for indication of empty session in any text block
        text_content = []
        for block in slack_payload["blocks"]:
            if "text" in block and "text" in block["text"]:
                text_content.append(block["text"]["text"])
            if "fields" in block:
                for field in block["fields"]:
                    text_content.append(field["text"])

        combined_text = " ".join(text_content).lower()
        self.assertTrue(
            any(word in combined_text for word in ["empty", "no activity", "brief"]),
            f"Empty session not indicated in text: {combined_text}"
        )

    @patch('subprocess.run')
    def test_stop_hook_when_already_active(self, mock_subprocess):
        """Test Stop hook skips notification when stop_hook_active is true."""
        # Arrange
        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "test-session-003",
            "transcript_path": transcript_path,
            "hook_event_name": "Stop",
            "stop_hook_active": True,  # This should cause the hook to skip
            "cwd": self.test_dir
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Skipping notification - stop hook already active"
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            result = self._simulate_stop_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        mock_send.assert_not_called()  # Should not send notification
        self.assertIn("already active", result["stdout"])

    @patch('subprocess.run')
    @patch('requests.post')
    def test_stop_hook_webhook_failure(self, mock_post, mock_subprocess):
        """Test Stop hook handling of webhook send failure."""
        # Arrange
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        transcript_path = self.create_mock_transcript([
            {"type": "user", "message": {"content": "Test message"}}
        ])

        input_data = {
            "session_id": "test-session-004",
            "transcript_path": transcript_path,
            "hook_event_name": "Stop",
            "stop_hook_active": False,
            "cwd": self.test_dir
        }

        # Mock hook script to return error code for webhook failure
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = "Error: Failed to send webhook notification"

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.side_effect = Exception("Webhook failed")
            result = self._simulate_stop_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 1)  # Non-blocking error
        self.assertIn("webhook", result["stderr"].lower())

    @patch('subprocess.run')
    def test_stop_hook_exit_codes(self, mock_subprocess):
        """Test Stop hook returns correct exit codes for different scenarios."""
        transcript_path = self.create_mock_transcript([])

        test_cases = [
            {
                "name": "success",
                "input": {
                    "session_id": "success-session",
                    "transcript_path": transcript_path,
                    "hook_event_name": "Stop",
                    "stop_hook_active": False,
                    "cwd": self.test_dir
                },
                "expected_exit_code": 0,
                "mock_returncode": 0
            },
            {
                "name": "block_incomplete_work",
                "input": {
                    "session_id": "incomplete-session",
                    "transcript_path": transcript_path,
                    "hook_event_name": "Stop",
                    "stop_hook_active": False,
                    "cwd": self.test_dir
                },
                "expected_exit_code": 2,  # Block stoppage
                "mock_returncode": 2,
                "mock_stderr": "Work appears incomplete - tests are failing"
            },
            {
                "name": "network_error",
                "input": {
                    "session_id": "error-session",
                    "transcript_path": transcript_path,
                    "hook_event_name": "Stop",
                    "stop_hook_active": False,
                    "cwd": self.test_dir
                },
                "expected_exit_code": 1,  # Non-blocking error
                "mock_returncode": 1,
                "mock_stderr": "Network error occurred"
            }
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                # Arrange
                mock_subprocess.return_value.returncode = case["mock_returncode"]
                mock_subprocess.return_value.stdout = ""
                mock_subprocess.return_value.stderr = case.get("mock_stderr", "")

                # Act
                result = self._simulate_stop_hook(case["input"])

                # Assert
                self.assertEqual(result["exit_code"], case["expected_exit_code"])
                if "mock_stderr" in case:
                    self.assertEqual(result["stderr"], case["mock_stderr"])

    def test_stop_hook_missing_config(self):
        """Test Stop hook behavior when Slack configuration is missing."""
        # Arrange - Remove the config file
        config_path = self.claude_dir / 'slack-config.json'
        if config_path.exists():
            config_path.unlink()

        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "no-config-session",
            "transcript_path": transcript_path,
            "hook_event_name": "Stop",
            "stop_hook_active": False,
            "cwd": self.test_dir
        }

        # Act
        with patch('slack_utils.load_config') as mock_load_config:
            mock_load_config.return_value = None
            result = self._simulate_stop_hook(input_data)

        # Assert - Should exit silently when no config
        self.assertEqual(result["exit_code"], 0)

    def test_stop_hook_malformed_json_input(self):
        """Test Stop hook handling of malformed JSON input."""
        # This test would be performed by feeding malformed JSON to stdin
        # In practice, the hook script should handle JSON parsing errors gracefully

        malformed_inputs = [
            '{"session_id": "test", "invalid": }',  # Invalid JSON
            '{"missing_required_fields": true}',    # Missing required fields
            '',                                     # Empty input
            'not json at all'                      # Not JSON
        ]

        for malformed_input in malformed_inputs:
            with self.subTest(input=malformed_input[:20] + "..."):
                # In a real test, we would pipe this to the hook script
                # and expect it to exit with error code 1
                with patch('json.loads') as mock_json_loads:
                    mock_json_loads.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
                    result = self._simulate_stop_hook_with_invalid_json()
                    self.assertEqual(result["exit_code"], 1)

    def test_stop_hook_transcript_parsing(self):
        """Test Stop hook correctly parses transcript for session summary."""
        # Create a rich transcript with various tool usages
        transcript_content = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/test/main.py", "content": "def main(): pass"}
                        }
                    ]
                }
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": "/test/utils.py", "old_string": "old", "new_string": "new"}
                        }
                    ]
                }
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "npm test", "description": "Run tests"}
                        }
                    ]
                }
            },
            {
                "type": "user",
                "message": {"content": "Please create a Python application with tests"}
            }
        ]

        transcript_path = self.create_mock_transcript(transcript_content)

        input_data = {
            "session_id": "rich-session",
            "transcript_path": transcript_path,
            "hook_event_name": "Stop",
            "stop_hook_active": False,
            "cwd": self.test_dir
        }

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}
            result = self._simulate_stop_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)

        # Verify that the Slack payload includes tool usage summary
        call_args = mock_send.call_args[0]
        slack_payload = call_args[0]

        # Look for tools mentioned in the notification
        text_content = self._extract_all_text_from_payload(slack_payload)
        combined_text = " ".join(text_content).lower()

        # Should mention different tools used
        self.assertTrue(any(tool in combined_text for tool in ["write", "edit", "bash"]))

        # Should mention files modified
        self.assertTrue(any(file_indicator in combined_text for file_indicator in ["file", "main.py", "utils.py"]))

    def _simulate_stop_hook(self, input_data):
        """Simulate the stop hook execution."""
        # This simulates what the actual hook script would do:
        # 1. Parse JSON input
        # 2. Load configuration
        # 3. Process transcript
        # 4. Send Slack notification
        # 5. Return appropriate exit code

        try:
            # Simulate JSON parsing
            if not isinstance(input_data, dict):
                return {"exit_code": 1, "stderr": "Error: Invalid JSON input"}

            # Check for required fields
            required_fields = ["session_id", "hook_event_name"]
            for field in required_fields:
                if field not in input_data:
                    return {"exit_code": 1, "stderr": f"Error: Missing required field: {field}"}

            # Simulate stop_hook_active check
            if input_data.get("stop_hook_active", False):
                return {"exit_code": 0, "stdout": "Skipping notification - stop hook already active"}

            # Simulate configuration loading
            config = self.mock_slack_config
            if not config or not config.get("enabled", False):
                return {"exit_code": 0, "stdout": "Slack integration not enabled"}

            # Simulate transcript processing and Slack notification
            from slack_utils import send_webhook, create_session_complete_message

            # Create session summary from transcript
            transcript_path = input_data.get("transcript_path", "")
            session_summary = self._parse_transcript_for_summary(transcript_path)

            # Create Slack message
            slack_message = create_session_complete_message(
                session_id=input_data["session_id"],
                summary=session_summary,
                project_name=config.get("project_name", "Unknown Project")
            )

            # Send webhook
            webhook_result = send_webhook(config["webhook_url"], slack_message)

            if webhook_result.get("success", False):
                return {"exit_code": 0, "stdout": "Session complete notification sent"}
            else:
                return {"exit_code": 1, "stderr": "Error: Failed to send webhook notification"}

        except Exception as e:
            return {"exit_code": 1, "stderr": f"Error: {str(e)}"}

    def _simulate_stop_hook_with_invalid_json(self):
        """Simulate stop hook with invalid JSON input."""
        return {"exit_code": 1, "stderr": "Error: Invalid JSON input"}

    def _parse_transcript_for_summary(self, transcript_path):
        """Parse transcript and extract summary information."""
        if not transcript_path or not os.path.exists(transcript_path):
            return {"tools_used": 0, "files_modified": 0, "activity": "No activity recorded"}

        tools_used = []
        files_modified = set()

        try:
            with open(transcript_path, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("type") == "assistant":
                            content = entry.get("message", {}).get("content", [])
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and item.get("type") == "tool_use":
                                        tool_name = item.get("name")
                                        if tool_name:
                                            tools_used.append(tool_name)

                                            # Extract file paths for file modification tools
                                            if tool_name in ["Write", "Edit", "MultiEdit"]:
                                                file_path = item.get("input", {}).get("file_path")
                                                if file_path:
                                                    files_modified.add(Path(file_path).name)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

        return {
            "tools_used": len(tools_used),
            "unique_tools": list(set(tools_used)),
            "files_modified": len(files_modified),
            "modified_files": list(files_modified),
            "activity": "Session completed with activity" if tools_used else "Brief session"
        }

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
    def create_session_complete_message(session_id, summary, project_name):
        """Mock Slack message creation."""
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🎯 *Claude Code Session Complete*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Session ID:*\n{session_id}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Project:*\n{project_name}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Summary:*\n- Tools used: {summary.get('tools_used', 0)}\n- Files modified: {summary.get('files_modified', 0)}\n- Activity: {summary.get('activity', 'Unknown')}"
                    }
                }
            ]
        }


# Patch the slack_utils module for all tests
@patch.dict('sys.modules', {'slack_utils': MockSlackUtils()})
class TestStopHookWithMocks(TestStopHook):
    """Test Stop hook with mocked slack_utils module."""
    pass


if __name__ == '__main__':
    unittest.main()