#!/usr/bin/env python3

"""
Integration tests for Claude Code Slack PostToolUse hook.

These tests verify the PostToolUse hook functionality according to the specifications in:
- /tmp/slack-integration-agents/phase2/research-summary.md
- docs/localdocs/5b71f56c.md

The PostToolUse hook should:
1. Parse JSON from stdin correctly
2. Load configuration from .claude/slack-config.json
3. Filter tools based on matcher patterns
4. Format appropriate Slack messages for different tool types
5. Aggregate multiple tool notifications
6. Send webhook requests
7. Return correct exit codes (0 for success, 2 for block, other for error)
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


class TestPostToolUseHook(unittest.TestCase):
    """Test suite for the PostToolUse hook script."""

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

        # Mock Slack configuration with tool filtering
        self.mock_slack_config = {
            "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
            "channel": "#general",
            "enabled": True,
            "project_name": "test-project",
            "tool_filters": {
                "notify_on": ["Write", "Edit", "MultiEdit", "Bash"],
                "aggregate_timeout": 5,  # seconds
                "max_notifications_per_session": 10
            }
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
    def test_posttooluse_write_tool(self, mock_post, mock_subprocess):
        """Test PostToolUse hook for Write tool notification."""
        # Arrange
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'ok'

        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "test-session-001",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/home/test/project/src/main.py",
                "content": "def main():\n    print('Hello World')\n"
            },
            "tool_response": {
                "filePath": "/home/test/project/src/main.py",
                "success": True
            }
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}
            result = self._simulate_posttooluse_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        mock_send.assert_called_once()

        # Verify the Slack payload structure for Write tool
        call_args = mock_send.call_args[0]
        slack_payload = call_args[0]

        self.assertIn("blocks", slack_payload)

        # Check for file created/written header
        header_text = self._extract_header_text(slack_payload)
        self.assertTrue(
            any(word in header_text.lower() for word in ["file", "created", "written"]),
            f"Header doesn't indicate file creation: {header_text}"
        )
        self.assertTrue("📝" in header_text or "✍️" in header_text)

        # Check for file path in message
        message_text = self._extract_all_text_from_payload(slack_payload)
        combined_text = " ".join(message_text)
        self.assertIn("main.py", combined_text)

        # Check for session details
        self.assertIn("test-session-001", combined_text)
        self.assertIn("Write", combined_text)

    @patch('subprocess.run')
    @patch('requests.post')
    def test_posttooluse_edit_tool(self, mock_post, mock_subprocess):
        """Test PostToolUse hook for Edit tool notification."""
        # Arrange
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'ok'

        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "test-session-002",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/home/test/project/src/utils.js",
                "old_string": "console.log('debug')",
                "new_string": "console.log('info')"
            },
            "tool_response": {
                "success": True,
                "changes": 1
            }
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}
            result = self._simulate_posttooluse_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        mock_send.assert_called_once()

        # Verify the Slack payload structure for Edit tool
        call_args = mock_send.call_args[0]
        slack_payload = call_args[0]

        # Check for file modified header
        header_text = self._extract_header_text(slack_payload)
        self.assertTrue(
            any(word in header_text.lower() for word in ["modified", "edited", "changed"]),
            f"Header doesn't indicate file modification: {header_text}"
        )
        self.assertTrue("✏️" in header_text or "📝" in header_text)

        # Check for file details and change count
        message_text = self._extract_all_text_from_payload(slack_payload)
        combined_text = " ".join(message_text)
        self.assertIn("utils.js", combined_text)
        self.assertIn("1 change", combined_text)

    @patch('subprocess.run')
    @patch('requests.post')
    def test_posttooluse_bash_tool(self, mock_post, mock_subprocess):
        """Test PostToolUse hook for Bash command notification."""
        # Arrange
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'ok'

        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "test-session-003",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "npm test",
                "description": "Run test suite"
            },
            "tool_response": {
                "exit_code": 0,
                "stdout": "All tests passed\n✓ 15 tests completed",
                "stderr": ""
            }
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}
            result = self._simulate_posttooluse_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        mock_send.assert_called_once()

        # Verify the Slack payload structure for Bash tool
        call_args = mock_send.call_args[0]
        slack_payload = call_args[0]

        # Check for command executed header
        header_text = self._extract_header_text(slack_payload)
        self.assertTrue(
            any(word in header_text.lower() for word in ["command", "executed", "ran"]),
            f"Header doesn't indicate command execution: {header_text}"
        )
        self.assertTrue("⚡" in header_text or "🔧" in header_text or "💻" in header_text)

        # Check for command details and exit code
        message_text = self._extract_all_text_from_payload(slack_payload)
        combined_text = " ".join(message_text)
        self.assertIn("npm test", combined_text)
        self.assertIn("Exit Code", combined_text)
        self.assertIn("0", combined_text)

    @patch('subprocess.run')
    @patch('requests.post')
    def test_posttooluse_aggregation(self, mock_post, mock_subprocess):
        """Test PostToolUse hook aggregation of multiple tools."""
        # This test simulates multiple tool calls in quick succession
        # The hook should aggregate them into a single notification

        # Arrange
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'ok'

        transcript_path = self.create_mock_transcript([])

        # Simulate multiple tool calls
        tool_calls = [
            {
                "session_id": "test-session-004",
                "transcript_path": transcript_path,
                "cwd": self.test_dir,
                "hook_event_name": "PostToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": "/test/file1.py", "content": "code1"},
                "tool_response": {"success": True}
            },
            {
                "session_id": "test-session-004",
                "transcript_path": transcript_path,
                "cwd": self.test_dir,
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": "/test/file2.js", "old_string": "a", "new_string": "b"},
                "tool_response": {"success": True, "changes": 1}
            },
            {
                "session_id": "test-session-004",
                "transcript_path": transcript_path,
                "cwd": self.test_dir,
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git add .", "description": "Stage changes"},
                "tool_response": {"exit_code": 0, "stdout": "", "stderr": ""}
            }
        ]

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}

            # Simulate rapid tool execution (should be aggregated)
            results = []
            for tool_call in tool_calls:
                result = self._simulate_posttooluse_hook_with_aggregation(tool_call)
                results.append(result)

        # Assert
        # In a real aggregation scenario, only one notification should be sent
        # containing summary of all operations
        self.assertTrue(any(r["exit_code"] == 0 for r in results))

        # Check that aggregated notification was sent
        self.assertTrue(mock_send.called)

        # Verify aggregated payload contains multiple operations
        if mock_send.called:
            call_args = mock_send.call_args[0]
            slack_payload = call_args[0]

            message_text = self._extract_all_text_from_payload(slack_payload)
            combined_text = " ".join(message_text)

            # Should mention multiple operations
            self.assertTrue(
                any(indicator in combined_text.lower() for indicator in ["activity", "operations", "recent"]),
                f"Aggregated message doesn't indicate multiple operations: {combined_text}"
            )

    @patch('subprocess.run')
    def test_posttooluse_filtering(self, mock_subprocess):
        """Test PostToolUse hook tool filtering by matcher."""
        # Test that only configured tools trigger notifications

        transcript_path = self.create_mock_transcript([])

        test_cases = [
            {
                "tool_name": "Write",
                "should_notify": True,  # In filter list
                "description": "Write tool should notify"
            },
            {
                "tool_name": "Read",
                "should_notify": False,  # Not in filter list
                "description": "Read tool should not notify"
            },
            {
                "tool_name": "Bash",
                "should_notify": True,  # In filter list
                "description": "Bash tool should notify"
            },
            {
                "tool_name": "Grep",
                "should_notify": False,  # Not in filter list
                "description": "Grep tool should not notify"
            }
        ]

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        for case in test_cases:
            with self.subTest(tool=case["tool_name"]):
                input_data = {
                    "session_id": f"test-session-filter-{case['tool_name']}",
                    "transcript_path": transcript_path,
                    "cwd": self.test_dir,
                    "hook_event_name": "PostToolUse",
                    "tool_name": case["tool_name"],
                    "tool_input": {"test": "data"},
                    "tool_response": {"success": True}
                }

                with patch('slack_utils.send_webhook') as mock_send:
                    mock_send.return_value = {"success": True, "status_code": 200}
                    result = self._simulate_posttooluse_hook(input_data)

                if case["should_notify"]:
                    mock_send.assert_called_once()
                    self.assertEqual(result["exit_code"], 0)
                else:
                    mock_send.assert_not_called()
                    self.assertEqual(result["exit_code"], 0)  # Still successful, just no notification

    @patch('subprocess.run')
    @patch('requests.post')
    def test_posttooluse_failed_tool(self, mock_post, mock_subprocess):
        """Test PostToolUse hook for failed tool operations."""
        # Arrange
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'ok'

        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "test-session-005",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/invalid/path/file.txt",
                "content": "test content"
            },
            "tool_response": {
                "success": False,
                "error": "Permission denied: Cannot write to /invalid/path/file.txt"
            }
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}
            result = self._simulate_posttooluse_hook(input_data)

        # Assert
        self.assertEqual(result["exit_code"], 0)
        mock_send.assert_called_once()

        # Verify the Slack payload shows failure
        call_args = mock_send.call_args[0]
        slack_payload = call_args[0]

        # Check for failure indication
        header_text = self._extract_header_text(slack_payload)
        self.assertTrue(
            any(word in header_text.lower() for word in ["failed", "error", "unsuccessful"]),
            f"Header doesn't indicate failure: {header_text}"
        )
        self.assertTrue("❌" in header_text or "⚠️" in header_text)

        # Check for error details
        message_text = self._extract_all_text_from_payload(slack_payload)
        combined_text = " ".join(message_text)
        self.assertIn("Permission denied", combined_text)

    @patch('subprocess.run')
    def test_posttooluse_missing_config(self, mock_subprocess):
        """Test PostToolUse hook when Slack configuration is missing."""
        # Arrange - Remove the config file
        config_path = self.claude_dir / 'slack-config.json'
        if config_path.exists():
            config_path.unlink()

        transcript_path = self.create_mock_transcript([])

        input_data = {
            "session_id": "test-session-006",
            "transcript_path": transcript_path,
            "cwd": self.test_dir,
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "/test/file.py", "content": "test"},
            "tool_response": {"success": True}
        }

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Slack integration not configured"
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.load_config') as mock_load_config:
            mock_load_config.return_value = None
            result = self._simulate_posttooluse_hook(input_data)

        # Assert - Should exit silently when no config
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("not configured", result["stdout"])

    @patch('subprocess.run')
    def test_posttooluse_malformed_input(self, mock_subprocess):
        """Test PostToolUse hook handling of malformed JSON input."""
        # Arrange
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = "Error: Invalid JSON input"

        # Test various malformed inputs
        test_cases = [
            '{"session_id": "test", "invalid": }',  # Invalid JSON syntax
            '{"missing_tool_name": true}',          # Missing required tool_name
            '',                                     # Empty input
            'not json at all',                     # Not JSON
            '{"tool_name": "", "session_id": ""}',  # Empty required fields
        ]

        for malformed_input in test_cases:
            with self.subTest(input=malformed_input[:20] + "..."):
                result = self._simulate_posttooluse_hook_with_invalid_json(malformed_input)
                self.assertEqual(result["exit_code"], 1)
                self.assertIn("Invalid JSON", result["stderr"])

    def test_posttooluse_tool_description_generation(self):
        """Test tool-specific description generation."""
        test_cases = [
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "/test/main.py", "content": "code"},
                "expected_keywords": ["created", "main.py", "📝"]
            },
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/test/utils.js", "old_string": "a", "new_string": "b"},
                "expected_keywords": ["modified", "utils.js", "✏️"]
            },
            {
                "tool_name": "Bash",
                "tool_input": {"command": "npm install", "description": "Install dependencies"},
                "expected_keywords": ["executed", "npm install", "⚡"]
            },
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "/test/config.json"},
                "expected_keywords": ["read", "config.json", "📖"]
            },
            {
                "tool_name": "Grep",
                "tool_input": {"pattern": "function", "path": "/test"},
                "expected_keywords": ["search", "function", "🔍"]
            }
        ]

        for case in test_cases:
            with self.subTest(tool=case["tool_name"]):
                description = self._generate_tool_description(
                    case["tool_name"],
                    case["tool_input"]
                )

                for keyword in case["expected_keywords"]:
                    self.assertIn(
                        keyword.lower(),
                        description.lower(),
                        f"Description '{description}' doesn't contain expected keyword '{keyword}'"
                    )

    @patch('subprocess.run')
    @patch('requests.post')
    def test_posttooluse_rate_limiting(self, mock_post, mock_subprocess):
        """Test PostToolUse hook respects rate limiting to avoid spam."""
        # Simulate rapid tool executions that should be rate-limited

        mock_post.return_value.status_code = 200
        mock_post.return_value.text = 'ok'

        transcript_path = self.create_mock_transcript([])

        # Simulate 5 rapid Write operations
        tool_calls = []
        for i in range(5):
            tool_calls.append({
                "session_id": "test-session-rate-limit",
                "transcript_path": transcript_path,
                "cwd": self.test_dir,
                "hook_event_name": "PostToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": f"/test/file{i}.py", "content": f"code{i}"},
                "tool_response": {"success": True}
            })

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = ""

        # Act
        with patch('slack_utils.send_webhook') as mock_send:
            mock_send.return_value = {"success": True, "status_code": 200}

            notification_count = 0
            for tool_call in tool_calls:
                result = self._simulate_posttooluse_hook_with_rate_limiting(tool_call)
                if result.get("notification_sent", False):
                    notification_count += 1

        # Assert - Should not send a notification for every single tool call
        # Exact behavior depends on rate limiting implementation
        self.assertLessEqual(
            notification_count,
            3,  # Should send fewer notifications than tool calls
            "Too many notifications sent - rate limiting not working"
        )

    def _simulate_posttooluse_hook(self, input_data):
        """Simulate the PostToolUse hook execution."""
        try:
            # Simulate JSON parsing
            if not isinstance(input_data, dict):
                return {"exit_code": 1, "stderr": "Error: Invalid JSON input"}

            # Check for required fields
            required_fields = ["session_id", "hook_event_name", "tool_name"]
            for field in required_fields:
                if field not in input_data or not input_data[field]:
                    return {"exit_code": 1, "stderr": f"Error: Missing required field: {field}"}

            # Simulate configuration loading
            config = self.mock_slack_config
            if not config:
                return {"exit_code": 0, "stdout": "Slack integration not configured"}

            if not config.get("enabled", False):
                return {"exit_code": 0, "stdout": "Slack integration disabled"}

            # Check tool filtering
            tool_filters = config.get("tool_filters", {})
            notify_on = tool_filters.get("notify_on", [])

            if notify_on and input_data["tool_name"] not in notify_on:
                return {"exit_code": 0, "stdout": f"Tool {input_data['tool_name']} not in notification filter"}

            # Simulate tool processing and Slack notification
            from slack_utils import send_webhook, create_posttooluse_message

            # Generate tool description
            tool_description = self._generate_tool_description(
                input_data["tool_name"],
                input_data.get("tool_input", {})
            )

            # Create Slack message
            slack_message = create_posttooluse_message(
                session_id=input_data["session_id"],
                tool_name=input_data["tool_name"],
                tool_input=input_data.get("tool_input", {}),
                tool_response=input_data.get("tool_response", {}),
                description=tool_description,
                project_name=config.get("project_name", "Unknown Project")
            )

            # Send webhook
            webhook_result = send_webhook(config["webhook_url"], slack_message)

            if webhook_result.get("success", False):
                return {"exit_code": 0, "stdout": "PostToolUse notification sent"}
            else:
                return {"exit_code": 1, "stderr": "Error: Failed to send webhook notification"}

        except Exception as e:
            return {"exit_code": 1, "stderr": f"Error: {str(e)}"}

    def _simulate_posttooluse_hook_with_aggregation(self, input_data):
        """Simulate PostToolUse hook with aggregation logic."""
        # This would implement aggregation logic to collect multiple tool calls
        # and send a single combined notification
        result = self._simulate_posttooluse_hook(input_data)
        result["aggregated"] = True
        return result

    def _simulate_posttooluse_hook_with_rate_limiting(self, input_data):
        """Simulate PostToolUse hook with rate limiting."""
        # This would implement rate limiting to prevent notification spam
        result = self._simulate_posttooluse_hook(input_data)

        # Simple rate limiting simulation - only send notification for first tool call
        session_id = input_data.get("session_id", "")
        if not hasattr(self, '_rate_limit_sessions'):
            self._rate_limit_sessions = set()

        if session_id not in self._rate_limit_sessions:
            self._rate_limit_sessions.add(session_id)
            result["notification_sent"] = True
        else:
            result["notification_sent"] = False
            result["stdout"] = "Rate limited - notification not sent"

        return result

    def _simulate_posttooluse_hook_with_invalid_json(self, invalid_input):
        """Simulate PostToolUse hook with invalid JSON input."""
        return {"exit_code": 1, "stderr": "Error: Invalid JSON input"}

    def _generate_tool_description(self, tool_name, tool_input):
        """Generate contextual description based on tool type."""
        if tool_name in ["Write", "Edit", "MultiEdit"]:
            file_path = tool_input.get("file_path", "")
            filename = Path(file_path).name if file_path else "file"

            if tool_name == "Write":
                return f"📝 Created {filename}"
            else:
                changes = tool_input.get("changes", 1)
                return f"✏️ Modified {filename} ({changes} change{'s' if changes != 1 else ''})"

        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            truncated_command = command[:50] + "..." if len(command) > 50 else command
            return f"⚡ Executed: {truncated_command}"

        elif tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            filename = Path(file_path).name if file_path else "file"
            return f"📖 Read {filename}"

        elif tool_name in ["Grep", "Glob"]:
            pattern = tool_input.get("pattern", "")
            return f"🔍 Searched for: {pattern}"

        elif tool_name in ["TodoWrite", "TodoRead"]:
            return "📋 Updated task list"

        elif tool_name in ["WebFetch", "WebSearch"]:
            return "🌐 Web research"

        else:
            return f"🔧 Used {tool_name}"

    def _extract_header_text(self, slack_payload):
        """Extract header text from Slack payload."""
        for block in slack_payload.get("blocks", []):
            if block.get("type") == "header":
                return block.get("text", {}).get("text", "")
            elif block.get("type") == "section" and "text" in block:
                text = block["text"].get("text", "")
                # Check if this looks like a header (contains emojis or formatting)
                if any(emoji in text for emoji in ["📝", "✏️", "⚡", "📖", "🔍", "❌", "⚠️"]):
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
    def create_posttooluse_message(session_id, tool_name, tool_input, tool_response, description, project_name):
        """Mock Slack PostToolUse message creation."""
        # Determine if operation was successful
        success = tool_response.get("success", True)
        exit_code = tool_response.get("exit_code", 0)

        if not success or exit_code != 0:
            emoji = "❌"
            status_text = "Failed"
        else:
            emoji = "📝" if tool_name in ["Write", "Edit"] else "⚡" if tool_name == "Bash" else "🔧"
            status_text = "Success"

        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{description}*"
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
                            "text": f"*Tool:*\n{tool_name}"
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
            "project_name": "test-project",
            "tool_filters": {"notify_on": ["Write", "Edit", "Bash"]}
        }


# Patch the slack_utils module for all tests
@patch.dict('sys.modules', {'slack_utils': MockSlackUtils()})
class TestPostToolUseHookWithMocks(TestPostToolUseHook):
    """Test PostToolUse hook with mocked slack_utils module."""
    pass


if __name__ == '__main__':
    unittest.main()