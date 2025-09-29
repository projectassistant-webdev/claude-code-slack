# Contributing to Claude Code Slack Integration

Thank you for your interest in contributing to Claude Code Slack Integration! We welcome contributions from the community.

## How to Contribute

### Reporting Issues

If you find a bug or have a feature request, please open an issue on GitHub:
1. Search existing issues to avoid duplicates
2. Use a clear, descriptive title
3. Provide detailed information about the problem or suggestion
4. Include steps to reproduce (for bugs)

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure everything works
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/claude-code-slack.git
cd claude-code-slack

# Install for development
./install.sh

# Run tests
python3 tests/run_tests.py
```

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions
- Keep functions focused and small
- Write tests for new features

### Testing

Before submitting a PR, ensure:
- All existing tests pass
- New features have tests
- Code coverage remains above 80%
- Manual testing completed

Run the test suite:
```bash
python3 tests/run_tests.py
```

### Documentation

- Update README.md if adding features
- Add docstrings to new functions
- Update relevant documentation in docs/
- Include examples where helpful

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Accept feedback gracefully

## License

By contributing to Claude Code Slack Integration, you agree that your contributions will be licensed under the MIT License.