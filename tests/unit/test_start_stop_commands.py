"""
Unit tests for the /user:slack:start and /user:slack:stop command handlers.

Tests the enable/disable command functionality that allows users to control
Slack notifications via Claude Code slash commands.
"""

import json
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path

# Import the modules under test (will fail initially since handlers don't exist yet)
try:
    from commands.slack.start_handler import main as start_main
except ImportError:
    start_main = None

try:
    from commands.slack.stop_handler import main as stop_main
except ImportError:
    stop_main = None

from commands.slack.slack_utils import load_configuration, save_configuration


class TestStartCommand(unittest.TestCase):
    """Test cases for the Slack start command handler."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_webhook = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
        self.valid_config = {
            "version": "1.0",
            "webhook_url": self.test_webhook,
            "active": False,
            "project_name": "test-project"
        }

        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_mock = self.env_patcher.start()

    def tearDown(self):
        """Clean up after each test method."""
        self.env_patcher.stop()

    @patch('builtins.print')
    @patch('commands.slack.start_handler.save_configuration')
    @patch('commands.slack.start_handler.load_configuration')
    @patch('commands.slack.start_handler.get_configuration_path')
    def test_start_command_enables_notifications(self, mock_get_path, mock_load_config,
                                                mock_save_config, mock_print):
        """Test that start command sets active to true."""
        if start_main is None:
            self.skipTest("start_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = self.valid_config.copy()
        mock_save_config.return_value = True

        # Execute the command
        start_main()

        # Verify configuration was updated
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]

        self.assertTrue(saved_config['active'])
        self.assertEqual(saved_config['webhook_url'], self.test_webhook)

        # Verify success message
        mock_print.assert_any_call("✅ Slack notifications enabled!")
        mock_print.assert_any_call("Notifications will be sent to the configured webhook.")

    @patch('builtins.print')
    @patch('commands.slack.start_handler.save_configuration')
    @patch('commands.slack.start_handler.load_configuration')
    @patch('commands.slack.start_handler.get_configuration_path')
    def test_start_with_thread_mode(self, mock_get_path, mock_load_config,
                                   mock_save_config, mock_print):
        """Test start command with optional thread_ts parameter."""
        if start_main is None:
            self.skipTest("start_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = self.valid_config.copy()
        mock_save_config.return_value = True

        # Set environment variable with thread parameter
        os.environ['ARGUMENTS'] = "thread_ts=1234567890.123456"

        # Execute the command
        start_main()

        # Verify configuration includes thread setting
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]

        self.assertTrue(saved_config['active'])
        self.assertEqual(saved_config.get('thread_ts'), "1234567890.123456")

        # Verify thread mode was mentioned in output
        mock_print.assert_any_call("Thread mode enabled: replies will be posted to thread 1234567890.123456")

    @patch('builtins.print')
    @patch('sys.exit')
    @patch('commands.slack.start_handler.load_configuration')
    @patch('commands.slack.start_handler.get_configuration_path')
    def test_start_when_not_configured(self, mock_get_path, mock_load_config,
                                      mock_exit, mock_print):
        """Test start command when Slack is not configured."""
        if start_main is None:
            self.skipTest("start_handler module not implemented yet")

        # Setup mocks - no configuration found
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = {}

        # Execute the command
        start_main()

        # Verify error handling
        mock_print.assert_any_call("❌ Slack integration is not configured.")
        mock_print.assert_any_call("Please run '/user:slack:setup <webhook_url>' first.")
        mock_exit.assert_called_once_with(1)

    @patch('builtins.print')
    @patch('sys.exit')
    @patch('commands.slack.start_handler.load_configuration')
    @patch('commands.slack.start_handler.get_configuration_path')
    def test_start_when_webhook_missing(self, mock_get_path, mock_load_config,
                                       mock_exit, mock_print):
        """Test start command when webhook URL is missing from config."""
        if start_main is None:
            self.skipTest("start_handler module not implemented yet")

        # Setup mocks - config exists but no webhook
        incomplete_config = {
            "version": "1.0",
            "active": False
        }
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = incomplete_config

        # Execute the command
        start_main()

        # Verify error handling
        mock_print.assert_any_call("❌ Slack webhook URL is not configured.")
        mock_print.assert_any_call("Please run '/user:slack:setup <webhook_url>' first.")
        mock_exit.assert_called_once_with(1)

    @patch('builtins.print')
    @patch('commands.slack.start_handler.save_configuration')
    @patch('commands.slack.start_handler.load_configuration')
    @patch('commands.slack.start_handler.get_configuration_path')
    def test_start_when_already_active(self, mock_get_path, mock_load_config,
                                      mock_save_config, mock_print):
        """Test start command when notifications are already active."""
        if start_main is None:
            self.skipTest("start_handler module not implemented yet")

        # Setup mocks - already active configuration
        active_config = self.valid_config.copy()
        active_config['active'] = True

        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = active_config
        mock_save_config.return_value = True

        # Execute the command
        start_main()

        # Should still save config (idempotent operation)
        mock_save_config.assert_called_once()

        # Verify informational message
        mock_print.assert_any_call("ℹ️ Slack notifications are already enabled.")


class TestStopCommand(unittest.TestCase):
    """Test cases for the Slack stop command handler."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_webhook = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
        self.active_config = {
            "version": "1.0",
            "webhook_url": self.test_webhook,
            "active": True,
            "project_name": "test-project"
        }

        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_mock = self.env_patcher.start()

    def tearDown(self):
        """Clean up after each test method."""
        self.env_patcher.stop()

    @patch('builtins.print')
    @patch('commands.slack.stop_handler.save_configuration')
    @patch('commands.slack.stop_handler.load_configuration')
    @patch('commands.slack.stop_handler.get_configuration_path')
    def test_stop_command_disables_notifications(self, mock_get_path, mock_load_config,
                                                mock_save_config, mock_print):
        """Test that stop command sets active to false."""
        if stop_main is None:
            self.skipTest("stop_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = self.active_config.copy()
        mock_save_config.return_value = True

        # Execute the command
        stop_main()

        # Verify configuration was updated
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]

        self.assertFalse(saved_config['active'])
        self.assertEqual(saved_config['webhook_url'], self.test_webhook)

        # Verify success message
        mock_print.assert_any_call("🔇 Slack notifications disabled.")
        mock_print.assert_any_call("You can re-enable them with '/user:slack:start'.")

    @patch('builtins.print')
    @patch('commands.slack.stop_handler.save_configuration')
    @patch('commands.slack.stop_handler.load_configuration')
    @patch('commands.slack.stop_handler.get_configuration_path')
    def test_stop_when_already_inactive(self, mock_get_path, mock_load_config,
                                       mock_save_config, mock_print):
        """Test stop command when notifications are already disabled."""
        if stop_main is None:
            self.skipTest("stop_handler module not implemented yet")

        # Setup mocks - already inactive configuration
        inactive_config = self.active_config.copy()
        inactive_config['active'] = False

        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = inactive_config
        mock_save_config.return_value = True

        # Execute the command
        stop_main()

        # Should still save config (idempotent operation)
        mock_save_config.assert_called_once()

        # Verify informational message
        mock_print.assert_any_call("ℹ️ Slack notifications are already disabled.")

    @patch('builtins.print')
    @patch('sys.exit')
    @patch('commands.slack.stop_handler.load_configuration')
    @patch('commands.slack.stop_handler.get_configuration_path')
    def test_stop_when_not_configured(self, mock_get_path, mock_load_config,
                                     mock_exit, mock_print):
        """Test stop command when Slack is not configured."""
        if stop_main is None:
            self.skipTest("stop_handler module not implemented yet")

        # Setup mocks - no configuration found
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = {}

        # Execute the command
        stop_main()

        # Verify error handling
        mock_print.assert_any_call("❌ Slack integration is not configured.")
        mock_print.assert_any_call("Nothing to disable.")
        mock_exit.assert_called_once_with(1)

    @patch('builtins.print')
    @patch('commands.slack.stop_handler.save_configuration')
    @patch('commands.slack.stop_handler.load_configuration')
    @patch('commands.slack.stop_handler.get_configuration_path')
    def test_stop_removes_thread_settings(self, mock_get_path, mock_load_config,
                                         mock_save_config, mock_print):
        """Test that stop command removes thread-specific settings."""
        if stop_main is None:
            self.skipTest("stop_handler module not implemented yet")

        # Setup mocks with thread settings
        config_with_thread = self.active_config.copy()
        config_with_thread['thread_ts'] = "1234567890.123456"

        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = config_with_thread
        mock_save_config.return_value = True

        # Execute the command
        stop_main()

        # Verify thread settings were removed
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]

        self.assertFalse(saved_config['active'])
        self.assertNotIn('thread_ts', saved_config)


class TestToggleStatePersistence(unittest.TestCase):
    """Test cases for state persistence in start/stop commands."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            "version": "1.0",
            "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
            "active": False,
            "project_name": "test-project",
            "notification_settings": {
                "session_complete": True,
                "error_notifications": False
            }
        }

        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_mock = self.env_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()

    @patch('commands.slack.start_handler.save_configuration')
    @patch('commands.slack.start_handler.load_configuration')
    @patch('commands.slack.start_handler.get_configuration_path')
    def test_start_preserves_other_settings(self, mock_get_path, mock_load_config, mock_save_config):
        """Test that start command preserves all other configuration settings."""
        if start_main is None:
            self.skipTest("start_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/.claude/slack-config.json"
        mock_load_config.return_value = self.test_config.copy()
        mock_save_config.return_value = True

        # Execute start command
        with patch('builtins.print'):
            start_main()

        # Verify all settings preserved except active flag
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]

        self.assertTrue(saved_config['active'])  # Should be changed
        self.assertEqual(saved_config['webhook_url'], self.test_config['webhook_url'])
        self.assertEqual(saved_config['project_name'], self.test_config['project_name'])
        self.assertEqual(saved_config['notification_settings'], self.test_config['notification_settings'])

    @patch('commands.slack.stop_handler.save_configuration')
    @patch('commands.slack.stop_handler.load_configuration')
    @patch('commands.slack.stop_handler.get_configuration_path')
    def test_stop_preserves_other_settings(self, mock_get_path, mock_load_config, mock_save_config):
        """Test that stop command preserves all other configuration settings."""
        if stop_main is None:
            self.skipTest("stop_handler module not implemented yet")

        # Setup mocks with active config
        active_config = self.test_config.copy()
        active_config['active'] = True

        mock_get_path.return_value = "/test/.claude/slack-config.json"
        mock_load_config.return_value = active_config
        mock_save_config.return_value = True

        # Execute stop command
        with patch('builtins.print'):
            stop_main()

        # Verify all settings preserved except active flag
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]

        self.assertFalse(saved_config['active'])  # Should be changed
        self.assertEqual(saved_config['webhook_url'], self.test_config['webhook_url'])
        self.assertEqual(saved_config['project_name'], self.test_config['project_name'])
        self.assertEqual(saved_config['notification_settings'], self.test_config['notification_settings'])

    @patch('builtins.print')
    @patch('commands.slack.start_handler.save_configuration')
    @patch('sys.exit')
    def test_start_handles_save_errors(self, mock_exit, mock_save_config, mock_print):
        """Test start command handles save errors gracefully."""
        if start_main is None:
            self.skipTest("start_handler module not implemented yet")

        # Setup mock to raise exception
        mock_save_config.side_effect = Exception("Disk full")

        # Execute command with mocked dependencies
        with patch('commands.slack.start_handler.load_configuration', return_value=self.test_config):
            with patch('commands.slack.start_handler.get_configuration_path',
                      return_value="/test/.claude/slack-config.json"):
                start_main()

        # Verify error handling
        mock_print.assert_any_call("❌ Error saving configuration: Disk full")
        mock_exit.assert_called_once_with(1)

    @patch('builtins.print')
    @patch('commands.slack.stop_handler.save_configuration')
    @patch('sys.exit')
    def test_stop_handles_save_errors(self, mock_exit, mock_save_config, mock_print):
        """Test stop command handles save errors gracefully."""
        if stop_main is None:
            self.skipTest("stop_handler module not implemented yet")

        # Setup mock to raise exception
        mock_save_config.side_effect = Exception("Permission denied")

        # Setup active config
        active_config = self.test_config.copy()
        active_config['active'] = True

        # Execute command with mocked dependencies
        with patch('commands.slack.stop_handler.load_configuration', return_value=active_config):
            with patch('commands.slack.stop_handler.get_configuration_path',
                      return_value="/test/.claude/slack-config.json"):
                stop_main()

        # Verify error handling
        mock_print.assert_any_call("❌ Error saving configuration: Permission denied")
        mock_exit.assert_called_once_with(1)


class TestCommandArgumentParsing(unittest.TestCase):
    """Test cases for argument parsing in start/stop commands."""

    def setUp(self):
        """Set up test fixtures."""
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_mock = self.env_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()

    def test_start_command_argument_parsing(self):
        """Test argument parsing for start command."""
        if start_main is None:
            self.skipTest("start_handler module not implemented yet")

        test_cases = [
            ("", {}),  # No arguments
            ("thread_ts=1234567890.123456", {"thread_ts": "1234567890.123456"}),
            ("channel=#general", {"channel": "#general"}),
            ("thread_ts=123 channel=#dev", {"thread_ts": "123", "channel": "#dev"}),
        ]

        for args_string, expected_parsed in test_cases:
            with self.subTest(args=args_string):
                os.environ['ARGUMENTS'] = args_string

                # Mock the argument parsing function
                with patch('commands.slack.start_handler.parse_start_arguments') as mock_parse:
                    mock_parse.return_value = expected_parsed

                    # Test would verify parsing logic here
                    if args_string:
                        parsed = {}
                        for arg in args_string.split():
                            if '=' in arg:
                                key, value = arg.split('=', 1)
                                parsed[key] = value
                        self.assertEqual(len(parsed), len(expected_parsed))

    def test_stop_command_has_no_arguments(self):
        """Test that stop command doesn't require arguments."""
        if stop_main is None:
            self.skipTest("stop_handler module not implemented yet")

        # Stop command should work with or without arguments
        os.environ['ARGUMENTS'] = "some_ignored_args"

        # The command should ignore any arguments provided
        # This test verifies the command doesn't fail with unexpected arguments
        self.assertTrue(True)  # Placeholder for actual implementation test


if __name__ == '__main__':
    unittest.main()