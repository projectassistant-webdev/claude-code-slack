#!/usr/bin/env python3
"""
Claude Code Slack PostToolUse Hook

Handles PostToolUse events by:
1. Reading JSON from stdin (tool_name, tool_input, tool_response)
2. Generating tool-specific descriptions
3. Supporting aggregation for rapid tool usage
4. Sending "Work in Progress" notifications (blue)
5. Filtering based on tool types if configured

Exit codes:
- 0: Success or silent exit
- 1: Error occurred
- 2: Blocking error (should prevent tool execution)
"""

import sys
import json
import os
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import tempfile
import fcntl

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
    return logging.getLogger('posttooluse-slack')

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

def should_notify_for_tool(tool_name: str, config: Dict[str, Any]) -> bool:
    """
    Check if notifications should be sent for this tool based on configuration.

    Args:
        tool_name: Name of the tool that was used
        config: Configuration dictionary

    Returns:
        True if notifications should be sent
    """
    tool_filters = config.get("tool_filters", {})
    notify_on = tool_filters.get("notify_on", [])

    # If no filter is configured, notify for common tools
    if not notify_on:
        default_tools = ["Write", "Edit", "MultiEdit", "Bash"]
        return tool_name in default_tools

    return tool_name in notify_on

def generate_tool_description(tool_name: str, tool_input: Dict[str, Any], tool_response: Dict[str, Any]) -> str:
    """
    Generate contextual description based on tool type and operation result.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters
        tool_response: Tool response data

    Returns:
        Human-readable description of the tool operation
    """
    # Check if operation was successful
    success = tool_response.get("success", True)
    exit_code = tool_response.get("exit_code", 0)
    error = tool_response.get("error", "")

    if not success or exit_code != 0:
        error_prefix = "❌ Failed: "
    else:
        error_prefix = ""

    if tool_name in ["Write", "Edit", "MultiEdit"]:
        file_path = tool_input.get("file_path", "")
        filename = Path(file_path).name if file_path else "file"

        if tool_name == "Write":
            content_size = len(tool_input.get("content", ""))
            size_desc = f"({content_size} chars)" if content_size > 0 else ""
            return f"{error_prefix}📝 Created {filename} {size_desc}".strip()
        elif tool_name == "Edit":
            old_string = tool_input.get("old_string", "")
            new_string = tool_input.get("new_string", "")
            changes_desc = f"({len(old_string)} → {len(new_string)} chars)" if old_string and new_string else ""
            return f"{error_prefix}✏️ Modified {filename} {changes_desc}".strip()
        elif tool_name == "MultiEdit":
            edits = tool_input.get("edits", [])
            edit_count = len(edits) if isinstance(edits, list) else 1
            return f"{error_prefix}📝 Multi-edited {filename} ({edit_count} changes)".strip()

    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        description = tool_input.get("description", "")

        # Truncate long commands
        display_command = command[:50] + "..." if len(command) > 50 else command

        # Include description if available
        if description:
            display_text = f"{description} ({display_command})"
        else:
            display_text = display_command

        exit_code_info = f" [exit: {exit_code}]" if exit_code != 0 else ""
        return f"{error_prefix}⚡ Executed: {display_text}{exit_code_info}".strip()

    elif tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        filename = Path(file_path).name if file_path else "file"
        offset = tool_input.get("offset", 0)
        limit = tool_input.get("limit", 0)

        range_desc = ""
        if offset > 0 or limit > 0:
            range_desc = f" (lines {offset}-{offset + limit})" if limit > 0 else f" (from line {offset})"

        return f"{error_prefix}📖 Read {filename}{range_desc}".strip()

    elif tool_name in ["Grep", "Glob"]:
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")
        path_desc = f" in {Path(path).name}" if path else ""
        return f"{error_prefix}🔍 Searched for: {pattern}{path_desc}".strip()

    elif tool_name in ["TodoWrite", "TodoRead"]:
        return f"{error_prefix}📋 Updated task list".strip()

    elif tool_name in ["WebFetch", "WebSearch"]:
        url = tool_input.get("url", "")
        query = tool_input.get("query", "")
        search_term = url or query or "web content"
        return f"{error_prefix}🌐 Web research: {search_term[:50]}".strip()

    elif tool_name == "NotebookEdit":
        notebook_path = tool_input.get("notebook_path", "")
        filename = Path(notebook_path).name if notebook_path else "notebook"
        edit_mode = tool_input.get("edit_mode", "replace")
        return f"{error_prefix}📓 {edit_mode.title()} in {filename}".strip()

    else:
        return f"{error_prefix}🔧 Used {tool_name}".strip()

def get_aggregation_state_file(session_id: str) -> Path:
    """Get path to aggregation state file for session."""
    temp_dir = Path(tempfile.gettempdir())
    return temp_dir / f"claude-slack-aggregation-{session_id}.json"

def should_aggregate_notification(session_id: str, config: Dict[str, Any]) -> bool:
    """
    Check if this notification should be aggregated with recent ones.

    Args:
        session_id: Current session ID
        config: Configuration dictionary

    Returns:
        True if notification should be aggregated
    """
    tool_filters = config.get("tool_filters", {})
    aggregate_timeout = tool_filters.get("aggregate_timeout", 5)  # seconds

    if aggregate_timeout <= 0:
        return False

    state_file = get_aggregation_state_file(session_id)

    try:
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)

            last_notification = datetime.fromisoformat(state.get("last_notification", ""))
            time_since_last = datetime.now() - last_notification

            return time_since_last.total_seconds() < aggregate_timeout
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    return False

def update_aggregation_state(session_id: str, tool_name: str, description: str) -> None:
    """
    Update aggregation state for the session.

    Args:
        session_id: Current session ID
        tool_name: Tool that was used
        description: Generated description
    """
    state_file = get_aggregation_state_file(session_id)

    # Load existing state
    state = {
        "session_id": session_id,
        "tools": [],
        "last_notification": datetime.now().isoformat(),
        "notification_count": 0
    }

    try:
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
    except (json.JSONDecodeError, ValueError):
        pass

    # Add current tool
    state["tools"].append({
        "tool_name": tool_name,
        "description": description,
        "timestamp": datetime.now().isoformat()
    })

    # Keep only recent tools (last 10)
    state["tools"] = state["tools"][-10:]
    state["last_notification"] = datetime.now().isoformat()
    state["notification_count"] = state.get("notification_count", 0) + 1

    # Save state with file locking
    try:
        with open(state_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(state, f, indent=2)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        # If locking fails, write without lock
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

def create_aggregated_message(session_id: str, current_tool: str, current_description: str,
                             project_name: str) -> Dict[str, Any]:
    """
    Create aggregated notification message for multiple recent tool uses.

    Args:
        session_id: Session identifier
        current_tool: Current tool name
        current_description: Current tool description
        project_name: Project name from config

    Returns:
        Slack Block Kit formatted message
    """
    state_file = get_aggregation_state_file(session_id)
    tools = [{"tool_name": current_tool, "description": current_description}]

    try:
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
                tools = state.get("tools", []) + tools
    except (json.JSONDecodeError, ValueError):
        pass

    # Get unique tools and latest descriptions
    tool_summary = {}
    for tool in tools[-5:]:  # Last 5 tools
        tool_name = tool.get("tool_name", "")
        description = tool.get("description", "")
        tool_summary[tool_name] = description

    activity_list = list(tool_summary.values())

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🔄 *Recent Activity*"
            }
        }
    ]

    # Activity summary
    if len(activity_list) == 1:
        activity_text = activity_list[0]
    else:
        activity_text = "\n".join([f"• {desc}" for desc in activity_list])

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": activity_text
        }
    })

    # Session details
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

    if len(tools) > 1:
        fields.append({
            "type": "mrkdwn",
            "text": f"*Tools Used:*\n{len(tools)} operations"
        })

    blocks.append({
        "type": "section",
        "fields": fields
    })

    # Timestamp
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        ]
    })

    return {
        "text": f"Claude Code activity: {current_description}",
        "blocks": blocks
    }

def create_posttooluse_message(session_id: str, tool_name: str, tool_input: Dict[str, Any],
                              tool_response: Dict[str, Any], description: str,
                              project_name: str) -> Dict[str, Any]:
    """
    Create Slack Block Kit message for tool usage.

    Args:
        session_id: Session identifier
        tool_name: Name of the tool used
        tool_input: Tool input parameters
        tool_response: Tool response data
        description: Generated description
        project_name: Project name from config

    Returns:
        Slack Block Kit formatted message
    """
    # Determine if operation was successful
    success = tool_response.get("success", True)
    exit_code = tool_response.get("exit_code", 0)

    if not success or exit_code != 0:
        emoji = "❌"
        status = "Tool Failed"
    else:
        emoji = "🔧"
        status = "Work in Progress"

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{description}*"
            }
        }
    ]

    # Tool details
    fields = [
        {
            "type": "mrkdwn",
            "text": f"*Session:*\n{session_id}"
        },
        {
            "type": "mrkdwn",
            "text": f"*Tool:*\n{tool_name}"
        }
    ]

    # Add error details if failed
    if not success or exit_code != 0:
        error_msg = tool_response.get("error", "Unknown error")
        if error_msg:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Error:*\n{truncate_message_content(error_msg, 100)}"
            })

    blocks.append({
        "type": "section",
        "fields": fields
    })

    # Timestamp
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Executed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        ]
    })

    return {
        "text": f"Claude Code tool usage: {description}",
        "blocks": blocks
    }

def cleanup_old_aggregation_files():
    """Clean up old aggregation state files."""
    try:
        temp_dir = Path(tempfile.gettempdir())
        pattern = "claude-slack-aggregation-*.json"
        cutoff_time = datetime.now() - timedelta(hours=1)

        for file_path in temp_dir.glob(pattern):
            try:
                if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
                    file_path.unlink()
            except (OSError, ValueError):
                continue
    except Exception:
        pass

def main():
    """Main entry point for the PostToolUse hook."""
    logger = setup_logging()

    try:
        # Clean up old files periodically
        cleanup_old_aggregation_files()

        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract required fields
        session_id = input_data.get("session_id", "")
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", {})
        hook_event_name = input_data.get("hook_event_name", "")

        # Validate required fields
        if not session_id:
            logger.error("Missing required field: session_id")
            sys.exit(1)

        if not tool_name:
            logger.error("Missing required field: tool_name")
            sys.exit(1)

        if hook_event_name != "PostToolUse":
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

        # Check if we should notify for this tool
        if not should_notify_for_tool(tool_name, config):
            logger.info(f"Tool {tool_name} not in notification filter")
            print(f"Tool {tool_name} not in notification filter")
            sys.exit(0)

        # Validate webhook URL
        webhook_url = config.get("webhook_url", "")
        if not validate_webhook_url(webhook_url):
            logger.error("Invalid webhook URL in configuration")
            sys.exit(1)

        # Generate tool description
        description = generate_tool_description(tool_name, tool_input, tool_response)
        logger.info(f"Generated description for {tool_name}: {description}")

        # Check rate limiting
        tool_filters = config.get("tool_filters", {})
        max_notifications = tool_filters.get("max_notifications_per_session", 10)

        # Update aggregation state
        update_aggregation_state(session_id, tool_name, description)

        # Determine if we should aggregate
        project_name = config.get("project_name", "Unknown Project")

        if should_aggregate_notification(session_id, config):
            # Send aggregated message
            slack_message = create_aggregated_message(
                session_id=session_id,
                current_tool=tool_name,
                current_description=description,
                project_name=project_name
            )
            logger.info(f"Sending aggregated notification for {session_id}")
        else:
            # Send individual message
            slack_message = create_posttooluse_message(
                session_id=session_id,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_response=tool_response,
                description=description,
                project_name=project_name
            )
            logger.info(f"Sending individual notification for {tool_name}")

        # Send webhook notification
        result = send_webhook(webhook_url, slack_message)

        if result["success"]:
            logger.info(f"Successfully sent notification: {result['status_code']}")
            print("PostToolUse notification sent")
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
        logger.info("PostToolUse hook interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()