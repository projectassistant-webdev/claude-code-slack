#!/bin/bash

# Create Release Package Script
# Creates a distributable release package for Claude Code Slack Integration

set -e

# Configuration
VERSION=$(cat VERSION)
RELEASE_NAME="claude-code-slack-v${VERSION}"
RELEASE_DIR="releases/${RELEASE_NAME}"
ARCHIVE_NAME="${RELEASE_NAME}.tar.gz"

echo "🚀 Creating Release Package for Claude Code Slack Integration v${VERSION}"
echo "================================================================"

# Create release directory
echo "📁 Creating release directory..."
mkdir -p "${RELEASE_DIR}"

# Copy essential files
echo "📦 Copying essential files..."

# Core files
cp -v README.md "${RELEASE_DIR}/"
cp -v CHANGELOG.md "${RELEASE_DIR}/"
cp -v VERSION "${RELEASE_DIR}/"
cp -v install.sh "${RELEASE_DIR}/"
cp -v uninstall.sh "${RELEASE_DIR}/"

# Copy directories
echo "📂 Copying directories..."
cp -r commands "${RELEASE_DIR}/"
cp -r hooks "${RELEASE_DIR}/"

# Copy documentation (excluding development docs)
mkdir -p "${RELEASE_DIR}/docs"
cp docs/INSTALLATION.md "${RELEASE_DIR}/docs/"
cp docs/CONFIGURATION.md "${RELEASE_DIR}/docs/"
cp docs/TROUBLESHOOTING.md "${RELEASE_DIR}/docs/"
cp docs/TESTING.md "${RELEASE_DIR}/docs/"

# Create minimal test suite
echo "🧪 Including essential tests..."
mkdir -p "${RELEASE_DIR}/tests"
cp tests/run_tests.py "${RELEASE_DIR}/tests/"
cp tests/conftest.py "${RELEASE_DIR}/tests/" 2>/dev/null || true
cp -r tests/unit "${RELEASE_DIR}/tests/"

# Create release notes
echo "📝 Generating release notes..."
cat > "${RELEASE_DIR}/RELEASE_NOTES.md" << EOF
# Claude Code Slack Integration v${VERSION}

## Release Date: $(date +%Y-%m-%d)

## Installation

### Quick Install (Recommended)
\`\`\`bash
curl -fsSL https://raw.githubusercontent.com/projectassistant-webdev/claude-code-slack/v${VERSION}/install.sh | bash
\`\`\`

### Manual Install
\`\`\`bash
tar -xzf ${ARCHIVE_NAME}
cd ${RELEASE_NAME}
./install.sh
\`\`\`

## What's Included

- Complete Slack integration for Claude Code
- Support for all three hook types (Stop, Notification, PostToolUse)
- Five slash commands for management
- Rich Block Kit message formatting
- Comprehensive documentation
- Test suite for validation

## Quick Start

1. Install the integration (see above)
2. Configure your Slack webhook:
   \`\`\`bash
   /user:slack:setup https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   \`\`\`
3. Enable notifications:
   \`\`\`bash
   /user:slack:start
   \`\`\`

## Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- [Testing Guide](docs/TESTING.md)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed changes in this release.

## Support

Report issues at: https://github.com/projectassistant-webdev/claude-code-slack/issues

---
*Claude Code Slack Integration v${VERSION} - Built with ❤️ for the Claude Code community*
EOF

# Create archive
echo "📦 Creating archive..."
cd releases
tar -czf "${ARCHIVE_NAME}" "${RELEASE_NAME}/"
cd ..

# Generate checksums
echo "🔐 Generating checksums..."
cd releases
sha256sum "${ARCHIVE_NAME}" > "${ARCHIVE_NAME}.sha256"
md5sum "${ARCHIVE_NAME}" > "${ARCHIVE_NAME}.md5"
cd ..

# Calculate package size
PACKAGE_SIZE=$(du -h "releases/${ARCHIVE_NAME}" | cut -f1)

# Create release manifest
echo "📋 Creating release manifest..."
cat > "releases/${RELEASE_NAME}.manifest.json" << EOF
{
  "version": "${VERSION}",
  "release_date": "$(date -Iseconds)",
  "package_name": "${ARCHIVE_NAME}",
  "package_size": "${PACKAGE_SIZE}",
  "sha256": "$(cat releases/${ARCHIVE_NAME}.sha256 | cut -d' ' -f1)",
  "md5": "$(cat releases/${ARCHIVE_NAME}.md5 | cut -d' ' -f1)",
  "files_count": $(find "${RELEASE_DIR}" -type f | wc -l),
  "platform_support": ["linux", "macos", "wsl"],
  "python_required": "3.6+",
  "dependencies": "none",
  "repository": "https://github.com/projectassistant-webdev/claude-code-slack",
  "documentation": "https://github.com/projectassistant-webdev/claude-code-slack/wiki"
}
EOF

# Display summary
echo ""
echo "✅ Release Package Created Successfully!"
echo "========================================"
echo "📦 Package: releases/${ARCHIVE_NAME}"
echo "📏 Size: ${PACKAGE_SIZE}"
echo "📁 Files: $(find "${RELEASE_DIR}" -type f | wc -l)"
echo "🔐 SHA256: $(cat releases/${ARCHIVE_NAME}.sha256 | cut -d' ' -f1)"
echo ""
echo "📤 Next Steps:"
echo "1. Test the package: tar -xzf releases/${ARCHIVE_NAME} && cd ${RELEASE_NAME} && ./install.sh"
echo "2. Upload to releases: git add releases/ && git commit -m 'Release v${VERSION}'"
echo "3. Create git tag: git tag -a v${VERSION} -m 'Release version ${VERSION}'"
echo "4. Push to repository: git push origin main --tags"
echo "5. Create Bitbucket release with the archive"

# Optionally create a quick test
if [ "$1" = "--test" ]; then
    echo ""
    echo "🧪 Testing release package..."
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    tar -xzf "${OLDPWD}/releases/${ARCHIVE_NAME}"
    cd "${RELEASE_NAME}"
    echo "✓ Archive extracted successfully"

    # Check essential files
    for file in README.md install.sh uninstall.sh hooks/stop-slack.py; do
        if [ -f "$file" ]; then
            echo "✓ $file exists"
        else
            echo "✗ $file missing!"
            exit 1
        fi
    done

    echo "✅ Release package validated successfully!"
    cd "$OLDPWD"
    rm -rf "$TEMP_DIR"
fi