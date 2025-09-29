# Slack Integration Test Suite

This directory contains comprehensive pytest tests for the Claude Code Slack integration utilities module. The tests are designed to initially **FAIL** since `slack_utils.py` doesn't exist yet - they define the implementation contract that the module must fulfill.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── __init__.py              # Package initialization
├── README.md               # This documentation
└── unit/                   # Unit tests directory
    ├── __init__.py         # Unit tests package init
    ├── test_url_validation.py      # URL validation tests
    ├── test_webhook_formatting.py  # Message formatting tests
    └── test_configuration.py       # Configuration management tests
```

## Test Files Overview

### 1. `test_url_validation.py`
Tests for webhook URL validation functionality:
- `test_valid_webhook_url()` - Valid Slack webhook format validation
- `test_invalid_webhook_url_format()` - Invalid URL patterns rejection
- `test_webhook_url_with_invalid_domain()` - Non-Slack domains rejection
- `test_webhook_url_parsing()` - Extract team/channel info from URLs
- `test_webhook_url_masking()` - Secure URL masking for display
- `test_webhook_url_edge_cases()` - Edge cases and special scenarios

### 2. `test_webhook_formatting.py`
Tests for Block Kit message formatting:
- `test_format_session_complete_message()` - Green success notifications
- `test_format_input_needed_message()` - Yellow warning notifications
- `test_format_work_in_progress_message()` - Blue progress notifications
- `test_block_kit_structure_validation()` - Valid JSON structure validation
- `test_message_truncation()` - Handle long messages properly
- `test_message_color_coding()` - Proper color scheme usage

### 3. `test_configuration.py`
Tests for configuration management:
- `test_load_configuration()` - Load from JSON file
- `test_save_configuration()` - Save to JSON file
- `test_configuration_validation()` - Validate required fields
- `test_merge_configurations()` - Merge user/project settings
- `test_configuration_file_not_found()` - Handle missing config
- `test_backup_configuration()` - Configuration backup functionality

## Expected Implementation

The tests expect the following module structure in `commands/slack/slack_utils.py`:

### URL Validation Functions
```python
def is_valid_webhook_url(url: str) -> bool
def validate_webhook_url(url: str) -> bool
def parse_webhook_url_components(url: str) -> dict
def mask_webhook_url(url: str) -> str
```

### Message Formatting Functions
```python
def format_session_complete_message(session_data: dict) -> dict
def format_input_needed_message(input_data: dict) -> dict
def format_work_in_progress_message(progress_data: dict) -> dict
def validate_block_kit_structure(payload: dict) -> bool
def truncate_message_content(content: str, max_length: int = 2000) -> str
```

### Configuration Management Functions
```python
def load_configuration(config_path: str = None) -> dict
def save_configuration(config_data: dict, config_path: str = None) -> bool
def validate_configuration(config_data: dict) -> bool
def merge_configurations(user_config: dict, project_config: dict) -> dict
def get_configuration_path(config_type: str = "project") -> str
def backup_configuration(config_path: str) -> str
def migrate_configuration(old_config: dict, target_version: str) -> dict

class ConfigurationError(Exception):
    pass
```

## Running the Tests

### Prerequisites
```bash
pip install pytest pytest-mock requests
```

### Run All Tests (Expected to Fail Initially)
```bash
# From project root
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_url_validation.py -v

# Run with coverage (after implementation)
pytest tests/ --cov=commands.slack.slack_utils --cov-report=html
```

### Test Markers
```bash
# Run only unit tests
pytest -m unit

# Run integration tests (when available)
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Test Data and Fixtures

### Common Test Data (from conftest.py)
- **sample_webhook_url**: Standard test webhook URL
- **sample_session_id**: Test session identifier
- **minimal_valid_config**: Minimal valid configuration
- **complete_valid_config**: Complete configuration with all options
- **session_complete_data**: Session completion test data
- **input_needed_data**: Input request test data
- **work_in_progress_data**: Progress update test data

### Validation Test Data
- **valid_webhook_urls**: Collection of valid Slack webhook URLs
- **invalid_webhook_urls**: Collection of invalid URLs for testing rejection
- **network_error_scenarios**: Network error simulation data
- **slack_api_error_responses**: Slack API error response scenarios

## Slack Integration Specifications

### Webhook URL Format
```
https://hooks.slack.com/services/{TEAM_ID}/{BOT_ID}/{TOKEN}
```
- **TEAM_ID**: Starts with 'T', followed by alphanumeric characters
- **BOT_ID**: Starts with 'B', followed by alphanumeric characters
- **TOKEN**: Alphanumeric string, typically 24 characters

### Block Kit Structure Requirements
- Must include top-level 'text' field for fallback
- Block types: header, section, context, actions, divider
- Text types: plain_text for headers, mrkdwn for content
- Limits: 50 blocks per message, 3000 chars per block, 10 fields per section

### Configuration Structure
```json
{
  "version": "1.0",
  "active": boolean,
  "webhook_url": "https://hooks.slack.com/services/...",
  "project_name": "optional-string",
  "notification_settings": {
    "session_complete": boolean,
    "input_needed": boolean,
    "work_in_progress": boolean,
    "error_notifications": boolean
  },
  "channel_settings": {
    "default_channel": "#channel-name",
    "mention_users": ["@user1", "@user2"],
    "quiet_hours": {
      "enabled": boolean,
      "start": "HH:MM",
      "end": "HH:MM",
      "timezone": "UTC"
    }
  },
  "message_settings": {
    "format": "block_kit" | "simple_text",
    "include_session_id": boolean,
    "include_project_name": boolean,
    "max_message_length": integer
  }
}
```

### Color Scheme Guidelines
- **Success**: Green (✅, 🎯, #36a64f)
- **Warning/Input**: Yellow (⚠️, 🤔, #ff9900)
- **Progress**: Blue (🔄, 📊, #3366ff)
- **Error**: Red (❌, 🚨, #ff0000)
- **Info**: Gray (ℹ️, 📢, #666666)

## Development Workflow

1. **Run Tests (Should Fail Initially)**
   ```bash
   pytest tests/ -v
   ```

2. **Implement Functions in `commands/slack/slack_utils.py`**
   - Start with URL validation functions
   - Implement message formatting functions
   - Add configuration management functions

3. **Run Tests Again (Should Pass After Implementation)**
   ```bash
   pytest tests/ -v
   ```

4. **Add Integration Tests**
   - Test actual Slack webhook calls (mocked)
   - Test file I/O operations
   - Test error handling scenarios

## Expected Test Results

### Before Implementation
All tests should fail with:
```
NotImplementedError: slack_utils.py not implemented yet
```

### After Implementation
All tests should pass, validating that:
- URL validation works correctly
- Message formatting produces valid Block Kit JSON
- Configuration management handles all scenarios
- Error cases are handled gracefully
- Edge cases are properly managed

## Contributing

When adding new tests:
1. Follow the existing naming conventions
2. Add comprehensive docstrings
3. Include both positive and negative test cases
4. Use appropriate fixtures from conftest.py
5. Mark tests with appropriate pytest markers
6. Update this README if adding new test categories

## Mock Usage

The tests use extensive mocking to isolate functionality:
- **File operations**: `mock_file_operations` fixture
- **Network requests**: `mock_slack_webhook` fixture
- **Environment variables**: `mock_environment` fixture
- **Configuration files**: `create_mock_config_file` fixture

This ensures tests run quickly and reliably without external dependencies.