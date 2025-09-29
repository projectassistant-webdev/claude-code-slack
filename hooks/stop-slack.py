#!/usr/bin/env python3
"""
Claude Code Slack Stop Hook

Handles Stop events by:
1. Reading JSON from stdin (session_id, transcript_path, stop_hook_active)
2. Parsing transcript to extract session summary if available
3. Sending "Session Complete" notification to Slack (green)
4. Exiting with code 0 on success, appropriate code on failure
5. Skipping if stop_hook_active is true (already in a stop hook)

Exit codes:
- 0: Success or silent exit
- 1: Non-blocking error (network, webhook)
- 2: Blocking error (should prevent stop)
"""

import sys
import json
import os
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add the project root to Python path for importing utilities
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from commands.slack.slack_utils import (
        load_configuration,
        validate_webhook_url,
        format_session_complete_message,
        truncate_message_content
    )
except ImportError:
    # Fallback implementation if slack_utils is not available
    def load_configuration(config_path=None):
        """Fallback configuration loader."""
        return None

    def validate_webhook_url(url):
        """Fallback webhook URL validator."""
        return "hooks.slack.com" in url if url else False

    def format_session_complete_message(data):
        """Fallback message formatter."""
        return {"text": "Session complete", "blocks": []}

    def truncate_message_content(content, max_length=2000):
        """Fallback content truncator."""
        return content[:max_length] + "..." if len(content) > max_length else content

# Set up logging
def setup_logging():
    """Configure logging to file."""
    log_dir = Path.home() / '.claude'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'slack-notifications.log'

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr)
        ]
    )
    return logging.getLogger('stop-slack')

def send_webhook(webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send webhook request to Slack with retry logic.

    Args:
        webhook_url: Slack webhook URL
        payload: Message payload

    Returns:
        Dictionary with success status and details
    """
    import urllib.request
    import urllib.error

    try:
        # Convert payload to JSON
        data = json.dumps(payload).encode('utf-8')

        # Create request
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        # Send request with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    response_text = response.read().decode('utf-8')
                    return {
                        "success": True,
                        "status_code": response.getcode(),
                        "response": response_text
                    }
            except urllib.error.HTTPError as e:
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "status_code": e.code,
                        "error": f"HTTP {e.code}: {e.reason}"
                    }
                time.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "status_code": 0,
                        "error": str(e)
                    }
                time.sleep(2 ** attempt)

    except Exception as e:
        return {
            "success": False,
            "status_code": 0,
            "error": f"Request preparation failed: {e}"
        }

def load_config() -> Optional[Dict[str, Any]]:
    """
    Load Slack configuration from .claude/slack-config.json.

    Returns:
        Configuration dictionary or None if not available
    """
    # Try CLAUDE_PROJECT_DIR first, then current directory
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
    config_path = Path(project_dir) / '.claude' / 'slack-config.json'

    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Validate required fields
        if not config.get('enabled', False):
            return None

        if not config.get('webhook_url'):
            return None

        return config
    except Exception:
        return None

def parse_transcript_for_summary(transcript_path: str) -> Dict[str, Any]:
    """
    Parse transcript file and extract session summary information.

    Args:
        transcript_path: Path to the transcript JSONL file

    Returns:
        Dictionary with session summary data
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return {
            "tools_used": 0,
            "files_modified": 0,
            "activity": "No activity recorded",
            "unique_tools": [],
            "modified_files": []
        }

    tools_used = []
    files_modified = set()
    user_messages = 0
    assistant_messages = 0

    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    entry_type = entry.get("type", "")

                    if entry_type == "user":
                        user_messages += 1
                    elif entry_type == "assistant":
                        assistant_messages += 1

                        # Extract tool usage
                        content = entry.get("message", {}).get("content", [])
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "tool_use":
                                    tool_name = item.get("name")
                                    if tool_name:
                                        tools_used.append(tool_name)

                                        # Extract file paths for file modification tools
                                        if tool_name in ["Write", "Edit", "MultiEdit"]:
                                            tool_input = item.get("input", {})
                                            file_path = tool_input.get("file_path")
                                            if file_path:
                                                files_modified.add(Path(file_path).name)

                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    # Determine activity level
    if tools_used:
        if len(tools_used) >= 5:
            activity = "Active session with significant work"
        elif len(tools_used) >= 2:
            activity = "Session completed with activity"
        else:
            activity = "Brief session"
    else:
        activity = "Empty session - no activity recorded"

    return {
        "tools_used": len(tools_used),
        "unique_tools": list(set(tools_used)),
        "files_modified": len(files_modified),
        "modified_files": list(files_modified),
        "user_messages": user_messages,
        "assistant_messages": assistant_messages,
        "activity": activity
    }

def create_session_complete_message(session_id: str, summary: Dict[str, Any], project_name: str) -> Dict[str, Any]:
    """
    Create Slack Block Kit message for session completion.

    Args:
        session_id: Session identifier
        summary: Session summary data
        project_name: Project name from config

    Returns:
        Slack Block Kit formatted message
    """
    # Determine emoji based on activity level
    tools_count = summary.get("tools_used", 0)
    if tools_count >= 5:
        emoji = "🎯"
        status = "Productive Session Complete"
    elif tools_count >= 1:
        emoji = "✅"
        status = "Session Complete"
    else:
        emoji = "💤"
        status = "Session Complete (No Activity)"

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{status}*"
            }
        }
    ]

    # Session details
    fields = [
        {
            "type": "mrkdwn",
            "text": f"*Session ID:*\n{session_id}"
        },
        {
            "type": "mrkdwn",
            "text": f"*Project:*\n{project_name}"
        }
    ]

    if summary.get("tools_used", 0) > 0:
        fields.extend([
            {
                "type": "mrkdwn",
                "text": f"*Tools Used:*\n{summary['tools_used']}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Files Modified:*\n{summary['files_modified']}"
            }
        ])

    blocks.append({
        "type": "section",
        "fields": fields
    })

    # Activity summary
    activity_text = f"*Summary:* {summary.get('activity', 'Unknown')}"

    if summary.get("unique_tools"):
        tools_list = ", ".join(summary["unique_tools"][:5])
        if len(summary["unique_tools"]) > 5:
            tools_list += f" (+{len(summary['unique_tools']) - 5} more)"
        activity_text += f"\n*Tools:* {tools_list}"

    if summary.get("modified_files"):
        files_list = ", ".join(summary["modified_files"][:3])
        if len(summary["modified_files"]) > 3:
            files_list += f" (+{len(summary['modified_files']) - 3} more)"
        activity_text += f"\n*Files:* {files_list}"

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": activity_text
        }
    })

    # Timestamp
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        ]
    })

    return {
        "text": f"Claude Code session {session_id} completed",
        "blocks": blocks
    }

def main():
    """Main entry point for the stop hook."""
    logger = setup_logging()

    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract required fields
        session_id = input_data.get("session_id", "")
        transcript_path = input_data.get("transcript_path", "")
        hook_event_name = input_data.get("hook_event_name", "")
        stop_hook_active = input_data.get("stop_hook_active", False)

        # Validate required fields
        if not session_id:
            logger.error("Missing required field: session_id")
            sys.exit(1)

        if hook_event_name != "Stop":
            logger.error(f"Invalid hook event: {hook_event_name}")
            sys.exit(1)

        # Skip if stop hook is already active
        if stop_hook_active:
            logger.info("Skipping notification - stop hook already active")
            print("Skipping notification - stop hook already active")
            sys.exit(0)

        # Load configuration
        config = load_config()
        if not config:
            logger.info("Slack integration not configured or disabled")
            sys.exit(0)

        # Validate webhook URL
        webhook_url = config.get("webhook_url", "")
        if not validate_webhook_url(webhook_url):
            logger.error("Invalid webhook URL in configuration")
            sys.exit(1)

        # Parse transcript for session summary
        logger.info(f"Parsing transcript: {transcript_path}")
        session_summary = parse_transcript_for_summary(transcript_path)

        # Create Slack message
        project_name = config.get("project_name", "Unknown Project")
        slack_message = create_session_complete_message(
            session_id=session_id,
            summary=session_summary,
            project_name=project_name
        )

        # Send webhook notification
        logger.info(f"Sending session complete notification for {session_id}")
        result = send_webhook(webhook_url, slack_message)

        if result["success"]:
            logger.info(f"Successfully sent notification: {result['status_code']}")
            print("Session complete notification sent")
            sys.exit(0)
        else:
            logger.error(f"Failed to send webhook: {result.get('error', 'Unknown error')}")
            print(f"Error: Failed to send webhook notification", file=sys.stderr)
            sys.exit(1)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        print("Error: Invalid JSON input", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Stop hook interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()