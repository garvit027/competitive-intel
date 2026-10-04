# Contributing to Competitive Intelligence Platform

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating, you agree to abide by our Code of Conduct. Please be respectful and inclusive.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/competitive-intel.git`
3. Run setup: `./scripts/setup.sh`
4. Create a feature branch: `git checkout -b feature/your-feature-name`

## Development Workflow

### Prerequisites
- Python 3.11+
- uv (installed via setup script)
- SerpApi API key (for integration tests)
- OpenAI API key (or compatible provider)

### Making Changes

1. **Write tests first** (TDD approach)
2. **Implement your feature** following the existing patterns
3. **Run quality checks**:
   ```bash
   make lint
   make typecheck
   make test-unit
   ```
4. **Update documentation** if needed
5. **Commit with conventional commits**:
   ```bash
   git commit -m "feat: add new signal type for regulatory actions"
   ```

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks
- `perf:` - Performance improvements

### Pull Request Process

1. Ensure all checks pass (lint, typecheck, tests)
2. Update CHANGELOG.md with your changes
3. Create PR with clear description
4. Link any related issues
5. Request review from maintainers

## Project Structure

```
src/competitive_intel/
├── agents/           # Agent implementations
├── workflows/        # LangGraph workflows
├── tools/            # Search tool integrations
├── models/           # Pydantic domain models
├── reports/          # Report generation
├── config/           # Settings management
└── utils/            # Shared utilities
```

## Adding New Features

### New Signal Type

1. Add to `SignalType` enum in `models/__init__.py`
2. Add detection keywords in `agents/analyst.py`
3. Add test cases in `tests/unit/test_agents.py`
4. Update documentation

### New Search Tool

1. Add tool class in `tools/search_tools.py`
2. Register in `SearchToolset`
3. Add to `tools/__init__.py`
4. Add integration test

### New Agent

1. Create agent class in `agents/`
2. Inherit from `BaseAgent` or `StructuredOutputAgent`
3. Add factory function
4. Register in `agents/__init__.py`
5. Add to workflow if needed

### New Report Format

1. Create exporter in `reports/exporters.py`
2. Add to `ExportFormat` enum
3. Register in `get_exporter()`
4. Add test case

## Testing Guidelines

- **Unit tests**: Test individual components in isolation (mock external APIs)
- **Integration tests**: Test full workflows with real APIs (require keys)
- **Test naming**: `test_<component>_<scenario>_<expected>`
- **Coverage target**: >80% for new code

## Code Style

- **Formatter**: ruff (configured in pyproject.toml)
- **Type hints**: Required for all public APIs
- **Docstrings**: Google style for public classes/functions
- **Imports**: Sorted by ruff (stdlib, third-party, local)

## Performance Considerations

- Use caching for repeated searches
- Respect SerpApi rate limits
- Limit concurrent searches (configurable)
- Use compact Markdown responses by default

## Security

- Never commit API keys or secrets
- Use environment variables for configuration
- Report security issues privately to maintainers
- Keep dependencies updated (Dependabot handles this)

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release tag: `git tag v0.2.0`
4. Push tag: `git push origin v0.2.0`
5. GitHub Actions builds and publishes

## Getting Help

- Check existing issues and discussions
- Join our community chat (if available)
- Contact maintainers for guidance

## Recognition

Contributors are recognized in:
- CHANGELOG.md
- Release notes
- GitHub contributors page

Thank you for contributing! 🎉