# System Tests for Claude Code Slack Integration

This directory contains comprehensive system tests for the installation and uninstallation scripts that need to be implemented for the Claude Code Slack integration.

## Overview

The system tests are designed to **fail initially** since the actual installation and uninstallation scripts (`install.sh` and `uninstall.sh`) don't exist yet. These tests serve as detailed specifications for the expected behavior of these scripts.

## Test Categories

### 1. Installation Flow (`test_installation_flow.py`)
Tests for the `install.sh` script functionality:
- Fresh installation on new systems
- Installation with existing hooks
- Local vs global installation modes
- Dependency checking (Python 3.6+, curl/wget)
- Hook registration in settings.json
- File permissions (making scripts executable)
- Idempotent installation (safe to run multiple times)

### 2. Hook Registration (`test_hook_registration.py`)
Tests for settings.json modification:
- Adding hooks to empty settings
- Merging with existing settings (preserving non-Slack hooks)
- Verifying correct paths with `$CLAUDE_PROJECT_DIR`
- Settings backup functionality
- Error handling for malformed JSON
- Hook structure validation

### 3. Cross-Platform Compatibility (`test_cross_platform.py`)
Tests for platform-specific behavior:
- macOS installation (Homebrew vs system Python)
- Linux installation (various distributions)
- WSL compatibility and detection
- Path normalization across platforms
- Shell compatibility (bash, zsh, sh)
- Package manager detection

### 4. Uninstallation (`test_uninstallation.py`)
Tests for the `uninstall.sh` script functionality:
- Complete removal of all Slack components
- Preservation of user data (backup creation)
- Hook removal from settings.json (preserve non-Slack hooks)
- Directory cleanup (remove empty directories)
- Partial installation handling
- Dry-run mode (show what would be removed)

## Test Structure

Each test file contains:
- **Mock implementations** in `mock_*.py` files that simulate script behavior
- **Test classes** that verify specific functionality
- **Both success and failure scenarios**
- **Edge case handling** (permissions, malformed files, etc.)
- **Idempotency tests** (running operations multiple times safely)

## Running the Tests

### Quick Test Report
```bash
# Show detailed test requirements (works without pytest)
python3 tests/system/test_runner.py report
```

### Running Specific Test Categories
```bash
# Install pytest first
pip install pytest

# Run all system tests
pytest tests/system/

# Run specific test categories
pytest tests/system/test_installation_flow.py
pytest tests/system/test_hook_registration.py
pytest tests/system/test_cross_platform.py
pytest tests/system/test_uninstallation.py

# Or use the test runner
python3 tests/system/test_runner.py install      # Installation tests
python3 tests/system/test_runner.py uninstall    # Uninstallation tests
python3 tests/system/test_runner.py cross-platform  # Cross-platform tests
python3 tests/system/test_runner.py hooks        # Hook registration tests
python3 tests/system/test_runner.py all          # All system tests
```

### Integration with Main Test Suite
```bash
# Run system tests through main test runner
python3 tests/run_tests.py system
```

## Expected Behavior

### Before Implementation
- **All tests will FAIL** with import errors or missing functionality
- Tests define the contract for what needs to be implemented
- Mock implementations show expected behavior patterns

### After Implementation
- Tests should PASS when scripts are correctly implemented
- Tests validate that scripts handle all required scenarios
- Tests ensure cross-platform compatibility and error handling

## Implementation Requirements

Based on these tests, you need to implement:

### 1. `install.sh` Script
- **Location**: Root of project or `scripts/` directory
- **Functionality**:
  - Check dependencies (Python 3.6+, curl/wget)
  - Create `.claude/hooks/` directory structure
  - Copy hook files and set executable permissions
  - Register hooks in `settings.json` with proper paths
  - Support `--global` flag for system-wide installation
  - Handle existing installations gracefully
  - Provide clear error messages and exit codes

### 2. `uninstall.sh` Script
- **Location**: Root of project or `scripts/` directory
- **Functionality**:
  - Remove Slack hook files
  - Clean up `settings.json` (remove only Slack hooks)
  - Create backups before making changes
  - Support `--dry-run` flag to preview changes
  - Handle partial installations gracefully
  - Clean up empty directories
  - Preserve user data and non-Slack components

### 3. Hook Registration Logic
- **Function**: Modify `settings.json` safely
- **Requirements**:
  - Parse and validate existing JSON
  - Merge new hooks with existing ones
  - Use `$CLAUDE_PROJECT_DIR` variable in paths
  - Create backups before modifications
  - Handle malformed JSON gracefully
  - Preserve non-Slack hooks and settings

### 4. Cross-Platform Support
- **Platforms**: macOS, Linux, WSL
- **Requirements**:
  - Detect platform and adjust paths accordingly
  - Handle different Python installation methods
  - Support various package managers
  - Normalize paths across platforms
  - Work with different shells (bash, zsh, sh)

## Mock Files

The `mock_*.py` files provide reference implementations:
- `mock_install_script.py` - Installation functionality patterns
- `mock_hook_registration.py` - Settings.json modification patterns
- `mock_cross_platform.py` - Platform detection and compatibility patterns
- `mock_uninstall_script.py` - Uninstallation functionality patterns

These mocks show the expected API and behavior for the actual implementations.

## Error Handling

Tests verify comprehensive error handling for:
- **Permission errors** (read-only files, insufficient privileges)
- **Missing dependencies** (Python, curl/wget not installed)
- **Malformed files** (invalid JSON in settings.json)
- **Disk space issues** (no space left for backups)
- **Network issues** (download failures)
- **Partial installations** (incomplete previous attempts)

## Security Considerations

Tests ensure:
- **No privilege escalation** without explicit `--global` flag
- **Safe file operations** (backups before modifications)
- **Path traversal protection** (validate paths before operations)
- **Permission validation** (check before attempting operations)

## Contributing

When implementing the actual scripts:
1. Start with the mock implementations as reference
2. Run tests frequently to verify compliance
3. Ensure all test scenarios pass
4. Add platform-specific testing as needed
5. Validate on multiple systems before release

The comprehensive test suite ensures that the installation and uninstallation scripts will be robust, user-friendly, and work reliably across different environments.