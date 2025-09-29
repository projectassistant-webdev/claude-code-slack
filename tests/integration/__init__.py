"""
Integration tests for Claude Code Slack hooks.

This module contains integration tests for the three main Claude Code hooks:
- Stop hook (test_stop_hook.py)
- Notification hook (test_notification_hook.py)
- PostToolUse hook (test_posttooluse_hook.py)

These tests verify that the hooks correctly:
1. Parse JSON input from stdin
2. Load configuration from .claude/slack-config.json
3. Format appropriate Slack Block Kit messages
4. Send webhook requests to Slack
5. Return correct exit codes

The tests are designed to fail initially since the actual hook scripts
don't exist yet, following TDD principles.
"""