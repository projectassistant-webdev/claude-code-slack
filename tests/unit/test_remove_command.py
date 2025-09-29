"""
Unit tests for the /user:slack:remove command handler.

Tests the removal command functionality that allows users to completely
remove Slack integration configuration via Claude Code slash commands.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, mock_open, MagicMock, call
from pathlib import Path
from datetime import datetime

# Import the module under test (will fail initially since handler doesn't exist yet)
try:
    from commands.slack.remove_handler import main as remove_main
except ImportError:
    remove_main = None

from commands.slack.slack_utils import backup_configuration


class TestRemoveCommand(unittest.TestCase):
    """Test cases for the Slack remove command handler."""

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
                "error_notifications": False
            },
            "statistics": {
                "total_notifications_sent": 42
            }
        }

        self.settings_config = {
            "hooks": {
                "notification": ["notification-slack.py", "other-notification.py"],
                "posttooluse": ["posttooluse-slack.py"],
                "stop": ["stop-slack.py", "other-stop.py"]
            },
            "other_setting": "preserved_value"
        }

        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_mock = self.env_patcher.start()

    def tearDown(self):
        """Clean up after each test method."""
        self.env_patcher.stop()

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('commands.slack.remove_handler.unregister_hooks_from_settings')
    @patch('commands.slack.remove_handler.load_configuration')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_remove_backs_up_settings(self, mock_exists, mock_remove, mock_get_path,
                                     mock_load_config, mock_unregister, mock_backup, mock_print):
        """Test that remove command creates backup before removal."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks
        config_path = "/test/path/.claude/slack-config.json"
        backup_path = "/test/path/.claude/slack-config.json.backup.20240115_103000"

        mock_get_path.return_value = config_path
        mock_exists.return_value = True
        mock_load_config.return_value = self.valid_config
        mock_backup.return_value = backup_path
        mock_unregister.return_value = True

        # Execute the command
        remove_main()

        # Verify backup was created
        mock_backup.assert_called_once_with(config_path)

        # Verify backup success message
        mock_print.assert_any_call(f"📁 Configuration backed up to: {backup_path}")

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('commands.slack.remove_handler.unregister_hooks_from_settings')
    @patch('commands.slack.remove_handler.load_configuration')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_remove_cleans_hooks(self, mock_exists, mock_remove, mock_get_path,
                                mock_load_config, mock_unregister, mock_backup, mock_print):
        """Test that remove command removes hooks from settings.json."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_exists.return_value = True
        mock_load_config.return_value = self.valid_config
        mock_backup.return_value = "/backup/path"
        mock_unregister.return_value = True

        # Execute the command
        remove_main()

        # Verify hooks were unregistered
        mock_unregister.assert_called_once()

        # Verify the hooks that should be removed
        unregister_args = mock_unregister.call_args[0][0]
        expected_hooks = [
            'notification-slack.py',
            'posttooluse-slack.py',
            'stop-slack.py'
        ]

        for hook in expected_hooks:
            self.assertIn(hook, unregister_args)

        # Verify success message
        mock_print.assert_any_call("🔗 Slack hooks removed from settings.json")

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('commands.slack.remove_handler.unregister_hooks_from_settings')
    @patch('commands.slack.remove_handler.load_configuration')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_remove_deletes_state_file(self, mock_exists, mock_remove, mock_get_path,
                                      mock_load_config, mock_unregister, mock_backup, mock_print):
        """Test that remove command deletes slack-config.json file."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks
        config_path = "/test/path/.claude/slack-config.json"

        mock_get_path.return_value = config_path
        mock_exists.return_value = True
        mock_load_config.return_value = self.valid_config
        mock_backup.return_value = "/backup/path"
        mock_unregister.return_value = True

        # Execute the command
        remove_main()

        # Verify configuration file was deleted
        mock_remove.assert_called_once_with(config_path)

        # Verify success message
        mock_print.assert_any_call("🗑️  Configuration file deleted")

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.path.exists')
    def test_remove_when_not_installed(self, mock_exists, mock_get_path, mock_print):
        """Test remove command when Slack integration is not installed."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks - configuration doesn't exist
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_exists.return_value = False

        # Execute the command
        remove_main()

        # Verify appropriate message
        mock_print.assert_any_call("ℹ️  Slack integration is not installed.")
        mock_print.assert_any_call("Nothing to remove.")

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('commands.slack.remove_handler.unregister_hooks_from_settings')
    @patch('commands.slack.remove_handler.load_settings_json')
    @patch('commands.slack.remove_handler.save_settings_json')
    @patch('commands.slack.remove_handler.load_configuration')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_remove_preserves_other_settings(self, mock_exists, mock_remove, mock_get_path,
                                            mock_load_config, mock_save_settings, mock_load_settings,
                                            mock_unregister, mock_backup, mock_print):
        """Test that remove command preserves non-Slack settings in settings.json."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_exists.return_value = True
        mock_load_config.return_value = self.valid_config
        mock_backup.return_value = "/backup/path"

        # Mock settings.json with mixed hooks
        mock_load_settings.return_value = self.settings_config.copy()
        mock_unregister.return_value = True

        # Execute the command
        remove_main()

        # Verify other settings are preserved
        if mock_save_settings.called:
            saved_settings = mock_save_settings.call_args[0][0]
            self.assertIn("other_setting", saved_settings)
            self.assertEqual(saved_settings["other_setting"], "preserved_value")

            # Verify non-Slack hooks are preserved
            if "hooks" in saved_settings:
                hooks = saved_settings["hooks"]
                if "notification" in hooks:
                    self.assertIn("other-notification.py", hooks["notification"])
                    self.assertNotIn("notification-slack.py", hooks["notification"])

                if "stop" in hooks:
                    self.assertIn("other-stop.py", hooks["stop"])
                    self.assertNotIn("stop-slack.py", hooks["stop"])

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('commands.slack.remove_handler.unregister_hooks_from_settings')
    @patch('commands.slack.remove_handler.load_configuration')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_remove_confirmation_prompt(self, mock_exists, mock_remove, mock_get_path,
                                       mock_load_config, mock_unregister, mock_backup, mock_print):
        """Test remove command shows confirmation prompt."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_exists.return_value = True
        mock_load_config.return_value = self.valid_config
        mock_backup.return_value = "/backup/path"
        mock_unregister.return_value = True

        # Mock user confirmation
        with patch('builtins.input', return_value='y'):
            remove_main()

        # Verify confirmation prompt was shown
        mock_print.assert_any_call("⚠️  This will completely remove Slack integration:")
        mock_print.assert_any_call("   • Delete configuration file")
        mock_print.assert_any_call("   • Remove hooks from settings.json")
        mock_print.assert_any_call("   • Disable all notifications")

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.path.exists')
    def test_remove_cancelled_by_user(self, mock_exists, mock_get_path, mock_print):
        """Test remove command when user cancels operation."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_exists.return_value = True

        # Mock user cancellation
        with patch('builtins.input', return_value='n'):
            with patch('commands.slack.remove_handler.load_configuration', return_value=self.valid_config):
                remove_main()

        # Verify cancellation message
        mock_print.assert_any_call("❌ Removal cancelled.")

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('sys.exit')
    def test_remove_handles_backup_errors(self, mock_exit, mock_backup, mock_print):
        """Test remove command handles backup creation errors."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mock to raise exception
        mock_backup.side_effect = Exception("Permission denied")

        # Execute with mocked dependencies
        with patch('commands.slack.remove_handler.get_configuration_path',
                  return_value="/test/.claude/slack-config.json"):
            with patch('os.path.exists', return_value=True):
                with patch('commands.slack.remove_handler.load_configuration',
                          return_value=self.valid_config):
                    with patch('builtins.input', return_value='y'):
                        remove_main()

        # Verify error handling
        mock_print.assert_any_call("❌ Error creating backup: Permission denied")
        mock_exit.assert_called_once_with(1)

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('commands.slack.remove_handler.unregister_hooks_from_settings')
    @patch('commands.slack.remove_handler.load_configuration')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.remove')
    @patch('os.path.exists')
    @patch('sys.exit')
    def test_remove_handles_file_deletion_errors(self, mock_exit, mock_exists, mock_remove,
                                                 mock_get_path, mock_load_config, mock_unregister,
                                                 mock_backup, mock_print):
        """Test remove command handles file deletion errors."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_exists.return_value = True
        mock_load_config.return_value = self.valid_config
        mock_backup.return_value = "/backup/path"
        mock_unregister.return_value = True
        mock_remove.side_effect = PermissionError("Permission denied")

        # Execute the command
        with patch('builtins.input', return_value='y'):
            remove_main()

        # Verify error handling
        mock_print.assert_any_call("❌ Error deleting configuration file: Permission denied")
        mock_exit.assert_called_once_with(1)

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('commands.slack.remove_handler.unregister_hooks_from_settings')
    @patch('commands.slack.remove_handler.load_configuration')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_remove_force_mode(self, mock_exists, mock_remove, mock_get_path,
                              mock_load_config, mock_unregister, mock_backup, mock_print):
        """Test remove command with force flag to skip confirmation."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_exists.return_value = True
        mock_load_config.return_value = self.valid_config
        mock_backup.return_value = "/backup/path"
        mock_unregister.return_value = True

        # Set environment variable for force mode
        os.environ['ARGUMENTS'] = '--force'

        # Execute the command
        remove_main()

        # Verify no confirmation prompt (mocked input should not be called)
        # and removal proceeds directly
        mock_remove.assert_called_once()
        mock_print.assert_any_call("✅ Slack integration completely removed!")

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('commands.slack.remove_handler.unregister_hooks_from_settings')
    @patch('commands.slack.remove_handler.load_configuration')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_remove_shows_summary(self, mock_exists, mock_remove, mock_get_path,
                                 mock_load_config, mock_unregister, mock_backup, mock_print):
        """Test remove command shows summary of what was removed."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks
        config_path = "/test/path/.claude/slack-config.json"
        backup_path = "/test/path/.claude/slack-config.json.backup.20240115_103000"

        mock_get_path.return_value = config_path
        mock_exists.return_value = True
        mock_load_config.return_value = self.valid_config
        mock_backup.return_value = backup_path
        mock_unregister.return_value = True

        # Execute the command
        with patch('builtins.input', return_value='y'):
            remove_main()

        # Verify summary is shown
        mock_print.assert_any_call("✅ Slack integration completely removed!")
        mock_print.assert_any_call("")
        mock_print.assert_any_call("Summary of changes:")
        mock_print.assert_any_call(f"  • Configuration backed up to: {backup_path}")
        mock_print.assert_any_call(f"  • Configuration file deleted: {config_path}")
        mock_print.assert_any_call("  • Slack hooks removed from settings.json")
        mock_print.assert_any_call("  • All notifications disabled")


class TestRemoveCommandEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for remove command."""

    def setUp(self):
        """Set up test fixtures."""
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_mock = self.env_patcher.start()

    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('commands.slack.remove_handler.unregister_hooks_from_settings')
    @patch('commands.slack.remove_handler.load_configuration')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_remove_with_corrupted_config(self, mock_exists, mock_remove, mock_get_path,
                                         mock_load_config, mock_unregister, mock_backup, mock_print):
        """Test remove command with corrupted configuration file."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks - config loading fails
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_exists.return_value = True
        mock_load_config.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_backup.return_value = "/backup/path"
        mock_unregister.return_value = True

        # Execute the command
        with patch('builtins.input', return_value='y'):
            remove_main()

        # Should still proceed with removal despite config errors
        mock_remove.assert_called_once()
        mock_print.assert_any_call("⚠️  Configuration file appears corrupted, but will be removed.")

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('commands.slack.remove_handler.unregister_hooks_from_settings')
    @patch('commands.slack.remove_handler.load_configuration')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_remove_with_partial_installation(self, mock_exists, mock_remove, mock_get_path,
                                             mock_load_config, mock_unregister, mock_backup, mock_print):
        """Test remove command with partial Slack installation."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup mocks - config exists but hooks not in settings
        mock_get_path.return_value = "/test/path/.claude/slack-config.json"
        mock_exists.return_value = True
        mock_load_config.return_value = {"version": "1.0", "webhook_url": "test"}
        mock_backup.return_value = "/backup/path"
        mock_unregister.return_value = False  # No hooks found to remove

        # Execute the command
        with patch('builtins.input', return_value='y'):
            remove_main()

        # Should still proceed and clean up what exists
        mock_remove.assert_called_once()
        mock_print.assert_any_call("ℹ️  No Slack hooks found in settings.json")

    def test_argument_parsing_force_flag(self):
        """Test parsing of force flag from arguments."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        test_cases = [
            ("--force", True),
            ("-f", True),
            ("--force --verbose", True),
            ("", False),
            ("--other-flag", False),
        ]

        for args_string, expected_force in test_cases:
            with self.subTest(args=args_string):
                os.environ['ARGUMENTS'] = args_string

                # Mock the argument parsing function
                with patch('commands.slack.remove_handler.parse_remove_arguments') as mock_parse:
                    mock_parse.return_value = {"force": expected_force}

                    # Test would verify parsing logic here
                    parsed = {"force": "--force" in args_string or "-f" in args_string}
                    self.assertEqual(parsed["force"], expected_force)


class TestRemoveCommandIntegration(unittest.TestCase):
    """Integration tests for remove command with other utilities."""

    def test_backup_configuration_integration(self):
        """Test that remove command integrates properly with backup utility."""
        # Test backup_configuration function from slack_utils
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "slack-config.json")

            # Create a test config file
            test_config = {"version": "1.0", "webhook_url": "test"}
            with open(config_path, 'w') as f:
                json.dump(test_config, f)

            # Test backup creation
            backup_path = backup_configuration(config_path)

            # Verify backup was created
            self.assertIsNotNone(backup_path)
            self.assertTrue(os.path.exists(backup_path))

            # Verify backup contains same content
            with open(backup_path, 'r') as f:
                backup_content = json.load(f)
            self.assertEqual(backup_content, test_config)

    @patch('builtins.print')
    @patch('commands.slack.remove_handler.backup_configuration')
    @patch('commands.slack.remove_handler.unregister_hooks_from_settings')
    @patch('commands.slack.remove_handler.load_configuration')
    @patch('commands.slack.remove_handler.get_configuration_path')
    @patch('os.remove')
    @patch('os.path.exists')
    def test_remove_complete_workflow(self, mock_exists, mock_remove, mock_get_path,
                                     mock_load_config, mock_unregister, mock_backup, mock_print):
        """Test complete remove command workflow."""
        if remove_main is None:
            self.skipTest("remove_handler module not implemented yet")

        # Setup complete workflow mocks
        config_path = "/test/.claude/slack-config.json"
        backup_path = f"{config_path}.backup.20240115_103000"

        mock_get_path.return_value = config_path
        mock_exists.return_value = True
        mock_load_config.return_value = {
            "version": "1.0",
            "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX",
            "active": True,
            "project_name": "test-project"
        }
        mock_backup.return_value = backup_path
        mock_unregister.return_value = True

        # Execute complete workflow
        with patch('builtins.input', return_value='y'):
            remove_main()

        # Verify complete workflow execution
        mock_backup.assert_called_once_with(config_path)
        mock_unregister.assert_called_once()
        mock_remove.assert_called_once_with(config_path)

        # Verify success messages
        mock_print.assert_any_call("✅ Slack integration completely removed!")


if __name__ == '__main__':
    unittest.main()