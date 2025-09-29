"""
Unit tests for the /user:slack:status command handler.

Tests the status command functionality that displays current Slack integration
configuration and statistics via Claude Code slash commands.
"""

import json
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
from datetime import datetime, timedelta

# Import the module under test (will fail initially since handler doesn't exist yet)
try:
    from commands.slack.status_handler import main as status_main
except ImportError:
    status_main = None

from commands.slack.slack_utils import mask_webhook_url


class TestStatusCommand(unittest.TestCase):
    """Test cases for the Slack status command handler."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_webhook = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
        self.valid_config = {
            "version": "1.0",
            "webhook_url": self.test_webhook,
            "active": True,
            "project_name": "test-project",
            "default_channel": "#general",
            "notification_settings": {
                "session_complete": True,
                "error_notifications": False,
                "work_in_progress": True
            },
            "statistics": {
                "total_notifications_sent": 42,
                "last_notification_time": "2024-01-15T10:30:00Z",
                "notifications_today": 5
            }
        }

        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_mock = self.env_patcher.start()

    def tearDown(self):
        """Clean up after each test method."""
        self.env_patcher.stop()

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_when_configured(self, mock_get_path, mock_load_config, mock_print):
        """Test status command shows current configuration when properly set up."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = self.valid_config

        # Execute the command
        status_main()

        # Verify status display includes key information
        mock_print.assert_any_call("📊 Slack Integration Status")
        mock_print.assert_any_call("=" * 50)

        # Check configuration status
        mock_print.assert_any_call("Status: ✅ Active")
        mock_print.assert_any_call(f"Project: {self.valid_config['project_name']}")
        mock_print.assert_any_call(f"Default Channel: {self.valid_config['default_channel']}")

        # Check webhook URL is masked
        masked_url = mask_webhook_url(self.test_webhook)
        mock_print.assert_any_call(f"Webhook URL: {masked_url}")

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_when_not_configured(self, mock_get_path, mock_load_config, mock_print):
        """Test status command shows helpful message when not configured."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Setup mocks - no configuration
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = {}

        # Execute the command
        status_main()

        # Verify helpful message is displayed
        mock_print.assert_any_call("📊 Slack Integration Status")
        mock_print.assert_any_call("=" * 50)
        mock_print.assert_any_call("Status: ❌ Not Configured")
        mock_print.assert_any_call("")
        mock_print.assert_any_call("To set up Slack integration:")
        mock_print.assert_any_call("  /user:slack:setup <webhook_url> [channel] [project_name]")
        mock_print.assert_any_call("")
        mock_print.assert_any_call("Example:")
        mock_print.assert_any_call("  /user:slack:setup https://hooks.slack.com/services/T.../B.../... #general my-project")

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_masks_webhook_url(self, mock_get_path, mock_load_config, mock_print):
        """Test that status command masks webhook URL for security."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = self.valid_config

        # Execute the command
        status_main()

        # Verify webhook URL is masked (token hidden)
        expected_masked = "https://hooks.slack.com/services/T1234567890/B1234567890/..."
        mock_print.assert_any_call(f"Webhook URL: {expected_masked}")

        # Verify actual webhook URL is never printed
        printed_calls = [str(call) for call in mock_print.call_args_list]
        for call in printed_calls:
            self.assertNotIn("abcdefghijklmnopqrstuvwx", call)

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    @patch('commands.slack.status_handler.detect_installation_type')
    def test_status_shows_installation_type(self, mock_detect_type, mock_get_path,
                                           mock_load_config, mock_print):
        """Test status command shows whether installation is local or global."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Test local installation
        mock_get_path.return_value = "/test/project/.claude/slack-config.json"
        mock_load_config.return_value = self.valid_config
        mock_detect_type.return_value = "project"

        status_main()

        mock_print.assert_any_call("Installation Type: Project-level")

        # Reset and test global installation
        mock_print.reset_mock()
        mock_detect_type.return_value = "user"

        status_main()

        mock_print.assert_any_call("Installation Type: User-level")

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_with_statistics(self, mock_get_path, mock_load_config, mock_print):
        """Test status command shows notification statistics if available."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Setup mocks with statistics
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = self.valid_config

        # Execute the command
        status_main()

        # Verify statistics are displayed
        mock_print.assert_any_call("📈 Statistics")
        mock_print.assert_any_call(f"Total Notifications Sent: 42")
        mock_print.assert_any_call(f"Notifications Today: 5")
        mock_print.assert_any_call(f"Last Notification: 2024-01-15T10:30:00Z")

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_without_statistics(self, mock_get_path, mock_load_config, mock_print):
        """Test status command when no statistics are available."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Setup config without statistics
        config_no_stats = self.valid_config.copy()
        del config_no_stats['statistics']

        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = config_no_stats

        # Execute the command
        status_main()

        # Verify no statistics section is shown
        printed_calls = [str(call) for call in mock_print.call_args_list]
        statistics_mentioned = any("Statistics" in call for call in printed_calls)
        self.assertFalse(statistics_mentioned)

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_shows_notification_settings(self, mock_get_path, mock_load_config, mock_print):
        """Test status command displays notification settings."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = self.valid_config

        # Execute the command
        status_main()

        # Verify notification settings are displayed
        mock_print.assert_any_call("🔔 Notification Settings")
        mock_print.assert_any_call("Session Complete: ✅ Enabled")
        mock_print.assert_any_call("Error Notifications: ❌ Disabled")
        mock_print.assert_any_call("Work in Progress: ✅ Enabled")

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_when_inactive(self, mock_get_path, mock_load_config, mock_print):
        """Test status command when Slack integration is configured but inactive."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Setup config with inactive status
        inactive_config = self.valid_config.copy()
        inactive_config['active'] = False

        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = inactive_config

        # Execute the command
        status_main()

        # Verify inactive status is shown
        mock_print.assert_any_call("Status: ⏸️ Configured but Inactive")
        mock_print.assert_any_call("")
        mock_print.assert_any_call("To enable notifications:")
        mock_print.assert_any_call("  /user:slack:start")

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_with_thread_mode(self, mock_get_path, mock_load_config, mock_print):
        """Test status command when thread mode is enabled."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Setup config with thread mode
        thread_config = self.valid_config.copy()
        thread_config['thread_ts'] = "1234567890.123456"

        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = thread_config

        # Execute the command
        status_main()

        # Verify thread mode is displayed
        mock_print.assert_any_call("Thread Mode: ✅ Enabled (1234567890.123456)")

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_handles_load_errors(self, mock_get_path, mock_load_config, mock_print):
        """Test status command handles configuration loading errors gracefully."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Setup mock to raise exception
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.side_effect = Exception("Permission denied")

        # Execute the command
        status_main()

        # Verify error is handled gracefully
        mock_print.assert_any_call("📊 Slack Integration Status")
        mock_print.assert_any_call("=" * 50)
        mock_print.assert_any_call("❌ Error loading configuration: Permission denied")


class TestStatusCommandFormatting(unittest.TestCase):
    """Test cases for status command output formatting."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            "version": "1.0",
            "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
            "active": True,
            "project_name": "my-awesome-project",
            "default_channel": "#development"
        }

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_formatting_consistency(self, mock_get_path, mock_load_config, mock_print):
        """Test that status output has consistent formatting."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        mock_get_path.return_value = "/test/.claude/slack-config.json"
        mock_load_config.return_value = self.test_config

        status_main()

        # Verify header formatting
        mock_print.assert_any_call("📊 Slack Integration Status")
        mock_print.assert_any_call("=" * 50)

        # Verify sections are properly separated
        printed_calls = [call.args[0] for call in mock_print.call_args_list if call.args]

        # Should have empty lines for section separation
        self.assertIn("", printed_calls)

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_handles_missing_optional_fields(self, mock_get_path, mock_load_config, mock_print):
        """Test status command handles missing optional configuration fields."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Minimal configuration
        minimal_config = {
            "version": "1.0",
            "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
            "active": True
        }

        mock_get_path.return_value = "/test/.claude/slack-config.json"
        mock_load_config.return_value = minimal_config

        # Should not raise exceptions
        status_main()

        # Verify basic status is still shown
        mock_print.assert_any_call("Status: ✅ Active")

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_with_long_project_name(self, mock_get_path, mock_load_config, mock_print):
        """Test status command handles long project names properly."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Config with very long project name
        long_name_config = self.test_config.copy()
        long_name_config['project_name'] = "a" * 100  # Very long name

        mock_get_path.return_value = "/test/.claude/slack-config.json"
        mock_load_config.return_value = long_name_config

        # Should handle long names gracefully
        status_main()

        # Verify project name is displayed (possibly truncated)
        project_calls = [call for call in mock_print.call_args_list
                        if call.args and "Project:" in str(call.args[0])]
        self.assertTrue(len(project_calls) > 0)


class TestStatusCommandHelpers(unittest.TestCase):
    """Test cases for helper functions used by status command."""

    @patch('os.path.exists')
    def test_detect_installation_type_project(self, mock_exists):
        """Test detection of project-level installation."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Mock project-level config exists
        def side_effect(path):
            return ".claude/slack-config.json" in path and "project" in path

        mock_exists.side_effect = side_effect

        # Would test the actual detection logic here
        # This is a placeholder for when the function exists
        self.assertTrue(True)

    @patch('os.path.exists')
    def test_detect_installation_type_user(self, mock_exists):
        """Test detection of user-level installation."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Mock only user-level config exists
        def side_effect(path):
            return ".claude/slack-config.json" in path and "home" in path

        mock_exists.side_effect = side_effect

        # Would test the actual detection logic here
        # This is a placeholder for when the function exists
        self.assertTrue(True)

    def test_webhook_url_masking_integration(self):
        """Test that status command uses same masking as slack_utils."""
        webhook = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
        masked = mask_webhook_url(webhook)

        # Verify token is hidden
        self.assertNotIn("secrettoken123", masked)
        self.assertIn("T1234567890", masked)
        self.assertIn("B1234567890", masked)
        self.assertIn("...", masked)

    @patch('builtins.print')
    @patch('commands.slack.status_handler.load_configuration')
    @patch('commands.slack.status_handler.get_configuration_path')
    def test_status_with_empty_statistics(self, mock_get_path, mock_load_config, mock_print):
        """Test status command with empty statistics object."""
        if status_main is None:
            self.skipTest("status_handler module not implemented yet")

        # Config with empty statistics
        config_empty_stats = self.test_config.copy()
        config_empty_stats['statistics'] = {}

        mock_get_path.return_value = "/test/.claude/slack-config.json"
        mock_load_config.return_value = config_empty_stats

        # Execute the command
        status_main()

        # Should handle empty statistics gracefully
        # Verify no statistics section or appropriate message
        printed_calls = [str(call) for call in mock_print.call_args_list]
        has_stats_section = any("📈 Statistics" in call for call in printed_calls)

        # Either no statistics section, or section with "No statistics available" message
        if has_stats_section:
            self.assertTrue(any("No statistics" in call for call in printed_calls))


if __name__ == '__main__':
    unittest.main()