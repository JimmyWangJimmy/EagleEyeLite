# Contributing to EagleEye Lite

Thank you for your interest in contributing! Here's a guide to help you get started.

## Code of Conduct

Please maintain respectful and constructive interactions with other contributors.

## How to Contribute?

### Report Bugs

Found a bug? Please [submit an Issue](https://github.com/JimmyWangJimmy/EagleEyeLite/issues).

Include:
- Clear title and description
- Steps to reproduce
- Expected behavior
- Actual behavior
- System information (OS, Python version, etc.)

### Submit Feature Requests

Have an idea? Please start a discussion in [Discussions](https://github.com/JimmyWangJimmy/EagleEyeLite/discussions).

### Submit Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Modify code and ensure:
   - Tests pass: `pytest`
   - Code formatting: `black src/`
   - No lint errors: `pylint src/`
4. Commit: `git commit -m 'Add amazing feature'`
5. Push: `git push origin feature/amazing-feature`
6. Submit Pull Request

## Development Setup

```bash
# Clone and enter project
git clone https://github.com/JimmyWangJimmy/EagleEyeLite.git
cd EagleEyeLite

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate     # Windows

# Install dev dependencies
pip install -e ".[dev]"
```

## Code Style

- **Language**: Python 3.8+
- **Format**: `black src/` (line length 88)
- **Lint**: `pylint src/`
- **Type hints**: Use them
- **Tests**: Required for new features

## Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_retrieval.py -v

# Coverage report
pytest --cov=src tests/
```

## Commit Message Format

```
type(scope): subject

body

footer
```

Example:
```
feat(rag): add hybrid retrieval

Implement both keyword-based and semantic retrieval
for better relevance ranking.

Fixes #123
```

Types: feat, fix, docs, style, refactor, perf, test, chore

---

Thank you for contributing! 🎉
