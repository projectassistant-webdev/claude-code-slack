#!/usr/bin/env python3
"""
Claude Code Slack Notification Hook

Handles Notification events by:
1. Reading JSON from stdin (session_id, transcript_path, message)
2. Determining notification type from message content
3. Sending appropriate notification to Slack (yellow for input needed)
4. Handling permission requests and idle waiting
5. Silent exit if no configuration

Exit codes:
- 0: Success or silent exit
- 1: Error occurred
"""

import sys
import json
import os
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add the project root to Python path for importing utilities
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from commands.slack.slack_utils import (
        load_configuration,
        validate_webhook_url,
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
    return logging.getLogger('notification-slack')

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

def classify_notification_message(message: str) -> Dict[str, str]:
    """
    Classify notification message type and return appropriate formatting.

    Args:
        message: The notification message to classify

    Returns:
        Dictionary with type, emoji, and title
    """
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

def create_notification_message(session_id: str, message: str, notification_type: Dict[str, str],
                               project_name: str, cwd: str = "") -> Dict[str, Any]:
    """
    Create Slack Block Kit message for notifications.

    Args:
        session_id: Session identifier
        message: Notification message content
        notification_type: Classification result with type, emoji, title
        project_name: Project name from config
        cwd: Current working directory

    Returns:
        Slack Block Kit formatted message
    """
    # Truncate long messages
    truncated_message = truncate_message_content(message, 2000)

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{notification_type['emoji']} *{notification_type['title']}*"
            }
        }
    ]

    # Main message content
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": truncated_message
        }
    })

    # Session and project details
    fields = [
        {
            "type": "mrkdwn",
            "text": f"*Session:*\n{session_id}"
        },
        {
            "type": "mrkdwn",
            "text": f"*Project:*\n{project_name}"
        }
    ]

    # Add working directory if provided and different from project name
    if cwd and cwd != project_name:
        cwd_short = Path(cwd).name if len(cwd) > 50 else cwd
        fields.append({
            "type": "mrkdwn",
            "text": f"*Directory:*\n{cwd_short}"
        })

    blocks.append({
        "type": "section",
        "fields": fields
    })

    # Add context based on notification type
    if notification_type["type"] == "permission":
        context_text = "Claude needs approval to proceed"
    elif notification_type["type"] == "idle":
        context_text = "Session is waiting for your input"
    else:
        context_text = "Notification from Claude Code"

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"{context_text} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        ]
    })

    return {
        "text": f"Claude Code notification: {message[:100]}",
        "blocks": blocks
    }

def main():
    """Main entry point for the notification hook."""
    logger = setup_logging()

    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract required fields
        session_id = input_data.get("session_id", "")
        message = input_data.get("message", "")
        hook_event_name = input_data.get("hook_event_name", "")
        transcript_path = input_data.get("transcript_path", "")
        cwd = input_data.get("cwd", "")

        # Validate required fields
        if not session_id:
            logger.error("Missing required field: session_id")
            sys.exit(1)

        if not message:
            logger.error("Missing required field: message")
            sys.exit(1)

        if hook_event_name != "Notification":
            logger.error(f"Invalid hook event: {hook_event_name}")
            sys.exit(1)

        # Load configuration
        config = load_config()
        if not config:
            logger.info("Slack integration not configured")
            print("Slack integration not configured")
            sys.exit(0)

        if not config.get("enabled", False):
            logger.info("Slack integration disabled")
            print("Slack integration disabled")
            sys.exit(0)

        # Validate webhook URL
        webhook_url = config.get("webhook_url", "")
        if not validate_webhook_url(webhook_url):
            logger.error("Invalid webhook URL in configuration")
            sys.exit(1)

        # Classify the notification message
        notification_type = classify_notification_message(message)
        logger.info(f"Classified notification as: {notification_type['type']}")

        # Create Slack message
        project_name = config.get("project_name", "Unknown Project")
        slack_message = create_notification_message(
            session_id=session_id,
            message=message,
            notification_type=notification_type,
            project_name=project_name,
            cwd=cwd
        )

        # Send webhook notification
        logger.info(f"Sending {notification_type['type']} notification for {session_id}")
        result = send_webhook(webhook_url, slack_message)

        if result["success"]:
            logger.info(f"Successfully sent notification: {result['status_code']}")
            print("Notification sent")
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
        logger.info("Notification hook interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()