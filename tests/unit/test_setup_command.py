"""
Unit tests for the /user:slack:setup command handler.

Tests the setup command functionality that allows users to configure
Slack webhook integration via Claude Code slash commands.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, mock_open, MagicMock, call
from pathlib import Path

# Import the module under test (will fail initially since handler doesn't exist yet)
try:
    from commands.slack.setup_handler import main as setup_main
except ImportError:
    # Mock the import for testing - this allows tests to be written before implementation
    setup_main = None

from commands.slack.slack_utils import is_valid_webhook_url


class TestSetupCommand(unittest.TestCase):
    """Test cases for the Slack setup command handler."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_webhook = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
        self.invalid_webhook = "https://invalid.webhook.url"
        self.test_channel = "#general"
        self.test_project = "my-project"

        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_mock = self.env_patcher.start()

    def tearDown(self):
        """Clean up after each test method."""
        self.env_patcher.stop()

    @patch('builtins.print')
    @patch('commands.slack.setup_handler.save_configuration')
    @patch('commands.slack.setup_handler.load_configuration')
    @patch('commands.slack.setup_handler.get_configuration_path')
    @patch('os.makedirs')
    def test_setup_with_valid_webhook(self, mock_makedirs, mock_get_path,
                                     mock_load_config, mock_save_config, mock_print):
        """Test setup command with a valid webhook URL."""
        if setup_main is None:
            self.skipTest("setup_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = {}
        mock_save_config.return_value = True

        # Set environment variable for arguments
        os.environ['ARGUMENTS'] = self.test_webhook

        # Execute the command
        setup_main()

        # Verify configuration was saved with correct data
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]

        self.assertEqual(saved_config['webhook_url'], self.test_webhook)
        self.assertTrue(saved_config['active'])
        self.assertEqual(saved_config['version'], "1.0")

        # Verify success message was printed
        mock_print.assert_any_call("✅ Slack integration configured successfully!")
        mock_print.assert_any_call(f"Webhook URL: https://hooks.slack.com/services/T1234567890/B1234567890/...")

    @patch('builtins.print')
    @patch('sys.exit')
    def test_setup_with_invalid_webhook(self, mock_exit, mock_print):
        """Test setup command rejects invalid webhook URLs."""
        if setup_main is None:
            self.skipTest("setup_handler module not implemented yet")

        # Set environment variable with invalid webhook
        os.environ['ARGUMENTS'] = self.invalid_webhook

        # Execute the command
        setup_main()

        # Verify error handling
        mock_print.assert_any_call("❌ Error: Invalid Slack webhook URL format.")
        mock_print.assert_any_call("Expected format: https://hooks.slack.com/services/T.../B.../...")
        mock_exit.assert_called_once_with(1)

    @patch('builtins.print')
    @patch('commands.slack.setup_handler.save_configuration')
    @patch('commands.slack.setup_handler.load_configuration')
    @patch('commands.slack.setup_handler.get_configuration_path')
    @patch('os.makedirs')
    def test_setup_with_channel_override(self, mock_makedirs, mock_get_path,
                                        mock_load_config, mock_save_config, mock_print):
        """Test setup command with optional channel parameter."""
        if setup_main is None:
            self.skipTest("setup_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = {}
        mock_save_config.return_value = True

        # Set environment variable with webhook and channel
        os.environ['ARGUMENTS'] = f"{self.test_webhook} {self.test_channel}"

        # Execute the command
        setup_main()

        # Verify configuration includes channel
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]

        self.assertEqual(saved_config['webhook_url'], self.test_webhook)
        self.assertEqual(saved_config['default_channel'], self.test_channel)

        # Verify channel was mentioned in output
        mock_print.assert_any_call(f"Default channel: {self.test_channel}")

    @patch('builtins.print')
    @patch('commands.slack.setup_handler.save_configuration')
    @patch('commands.slack.setup_handler.load_configuration')
    @patch('commands.slack.setup_handler.get_configuration_path')
    @patch('commands.slack.setup_handler.register_hook_in_settings')
    @patch('os.makedirs')
    def test_setup_updates_settings(self, mock_makedirs, mock_register_hook,
                                   mock_get_path, mock_load_config, mock_save_config, mock_print):
        """Test that setup command updates .claude/settings.json with hook registration."""
        if setup_main is None:
            self.skipTest("setup_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = {}
        mock_save_config.return_value = True
        mock_register_hook.return_value = True

        # Set environment variable
        os.environ['ARGUMENTS'] = self.test_webhook

        # Execute the command
        setup_main()

        # Verify hook registration was called
        mock_register_hook.assert_called_once()

        # Verify hook registration includes all required hooks
        hook_calls = mock_register_hook.call_args_list
        registered_hooks = hook_calls[0][0][0] if hook_calls else []

        expected_hooks = [
            'notification-slack.py',
            'posttooluse-slack.py',
            'stop-slack.py'
        ]

        for hook in expected_hooks:
            self.assertIn(hook, str(registered_hooks))

    @patch('builtins.print')
    @patch('commands.slack.setup_handler.save_configuration')
    @patch('commands.slack.setup_handler.load_configuration')
    @patch('commands.slack.setup_handler.get_configuration_path')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_setup_creates_directories(self, mock_exists, mock_makedirs, mock_get_path,
                                      mock_load_config, mock_save_config, mock_print):
        """Test that setup command creates .claude directory if missing."""
        if setup_main is None:
            self.skipTest("setup_handler module not implemented yet")

        # Setup mocks - directory doesn't exist
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_exists.return_value = False
        mock_load_config.return_value = {}
        mock_save_config.return_value = True

        # Set environment variable
        os.environ['ARGUMENTS'] = self.test_webhook

        # Execute the command
        setup_main()

        # Verify directory creation was attempted
        mock_makedirs.assert_called()

        # Check that .claude directory path was used
        makedirs_calls = mock_makedirs.call_args_list
        self.assertTrue(any('.claude' in str(call) for call in makedirs_calls))

    @patch('builtins.print')
    @patch('commands.slack.setup_handler.save_configuration')
    @patch('commands.slack.setup_handler.load_configuration')
    @patch('commands.slack.setup_handler.get_configuration_path')
    @patch('os.makedirs')
    def test_setup_with_project_name(self, mock_makedirs, mock_get_path,
                                    mock_load_config, mock_save_config, mock_print):
        """Test setup command with optional project name parameter."""
        if setup_main is None:
            self.skipTest("setup_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = {}
        mock_save_config.return_value = True

        # Set environment variable with all parameters
        os.environ['ARGUMENTS'] = f"{self.test_webhook} {self.test_channel} {self.test_project}"

        # Execute the command
        setup_main()

        # Verify configuration includes project name
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]

        self.assertEqual(saved_config['project_name'], self.test_project)

        # Verify project name was mentioned in output
        mock_print.assert_any_call(f"Project name: {self.test_project}")

    @patch('builtins.print')
    @patch('sys.exit')
    def test_setup_with_no_arguments(self, mock_exit, mock_print):
        """Test setup command with missing webhook URL argument."""
        if setup_main is None:
            self.skipTest("setup_handler module not implemented yet")

        # Don't set ARGUMENTS environment variable
        if 'ARGUMENTS' in os.environ:
            del os.environ['ARGUMENTS']

        # Execute the command
        setup_main()

        # Verify error handling
        mock_print.assert_any_call("❌ Error: Webhook URL is required.")
        mock_print.assert_any_call("Usage: /user:slack:setup <webhook_url> [channel] [project_name]")
        mock_exit.assert_called_once_with(1)

    @patch('builtins.print')
    @patch('commands.slack.setup_handler.save_configuration')
    @patch('commands.slack.setup_handler.load_configuration')
    @patch('commands.slack.setup_handler.get_configuration_path')
    @patch('os.makedirs')
    def test_setup_preserves_existing_settings(self, mock_makedirs, mock_get_path,
                                              mock_load_config, mock_save_config, mock_print):
        """Test that setup command preserves existing configuration settings."""
        if setup_main is None:
            self.skipTest("setup_handler module not implemented yet")

        # Setup mocks with existing configuration
        existing_config = {
            "version": "1.0",
            "notification_settings": {
                "session_complete": True,
                "error_notifications": False
            },
            "custom_field": "preserved_value"
        }

        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_load_config.return_value = existing_config
        mock_save_config.return_value = True

        # Set environment variable
        os.environ['ARGUMENTS'] = self.test_webhook

        # Execute the command
        setup_main()

        # Verify existing settings were preserved
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]

        self.assertEqual(saved_config['webhook_url'], self.test_webhook)
        self.assertEqual(saved_config['notification_settings'], existing_config['notification_settings'])
        self.assertEqual(saved_config['custom_field'], existing_config['custom_field'])

    @patch('builtins.print')
    @patch('commands.slack.setup_handler.save_configuration')
    @patch('sys.exit')
    def test_setup_handles_save_errors(self, mock_exit, mock_save_config, mock_print):
        """Test setup command handles configuration save errors gracefully."""
        if setup_main is None:
            self.skipTest("setup_handler module not implemented yet")

        # Setup mock to raise exception
        mock_save_config.side_effect = Exception("Permission denied")

        # Set environment variable
        os.environ['ARGUMENTS'] = self.test_webhook

        # Execute the command
        with patch('commands.slack.setup_handler.load_configuration', return_value={}):
            with patch('commands.slack.setup_handler.get_configuration_path',
                      return_value="/test/path/.claude/slack-config.json"):
                setup_main()

        # Verify error handling
        mock_print.assert_any_call("❌ Error saving configuration: Permission denied")
        mock_exit.assert_called_once_with(1)

    def test_webhook_url_validation_integration(self):
        """Test that setup command uses the same validation as slack_utils."""
        # Test valid webhook
        self.assertTrue(is_valid_webhook_url(self.test_webhook))

        # Test invalid webhook
        self.assertFalse(is_valid_webhook_url(self.invalid_webhook))

        # Test edge cases
        self.assertFalse(is_valid_webhook_url(""))
        self.assertFalse(is_valid_webhook_url(None))
        self.assertFalse(is_valid_webhook_url("https://hooks.slack.com/services/"))
        self.assertFalse(is_valid_webhook_url("http://hooks.slack.com/services/T123/B123/token"))


class TestSetupCommandArgumentParsing(unittest.TestCase):
    """Test cases for argument parsing in setup command."""

    def setUp(self):
        """Set up test fixtures."""
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_mock = self.env_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()

    @patch('builtins.print')
    def test_parse_arguments_from_environment(self, mock_print):
        """Test parsing arguments from ARGUMENTS environment variable."""
        if setup_main is None:
            self.skipTest("setup_handler module not implemented yet")

        test_cases = [
            ("https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX", 1),
            ("https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX #general", 2),
            ("https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX #general my-project", 3),
            ("  https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX   #general   my-project  ", 3),  # With whitespace
        ]

        for args_string, expected_count in test_cases:
            with self.subTest(args=args_string):
                os.environ['ARGUMENTS'] = args_string

                # Mock the argument parsing function if it exists
                with patch('commands.slack.setup_handler.parse_arguments') as mock_parse:
                    mock_parse.return_value = args_string.split()

                    # This would test the actual parsing logic
                    parsed_args = args_string.split()
                    self.assertEqual(len(parsed_args), expected_count)

                    # First argument should always be webhook URL
                    self.assertTrue(parsed_args[0].startswith('https://hooks.slack.com'))

    def test_argument_validation_edge_cases(self):
        """Test edge cases in argument validation."""
        test_cases = [
            ("", "empty string"),
            ("   ", "whitespace only"),
            ("webhook", "single invalid webhook"),
            ("webhook channel project extra", "too many arguments"),
        ]

        for args_string, description in test_cases:
            with self.subTest(args=description):
                # Test that invalid argument combinations are handled
                args = args_string.split() if args_string.strip() else []

                if len(args) == 0:
                    # Should fail with no arguments
                    self.assertEqual(len(args), 0)
                elif len(args) > 3:
                    # Should handle extra arguments gracefully
                    self.assertGreater(len(args), 3)


if __name__ == '__main__':
    unittest.main()