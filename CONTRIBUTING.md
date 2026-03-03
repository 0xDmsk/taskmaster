# Contributing to Taskmaster

Thank you for your interest in contributing to Taskmaster! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Docker or Podman
- `uv` package manager
- `socat` for MCP server bridge

### Setup Development Environment

1. Clone the repository:
```bash
git clone <repository-url>
cd taskmaster
```

2. Install dependencies:
```bash
uv sync
```

3. Copy environment configuration:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Build the agent container:
```bash
./scripts/build.sh
```

## 🛠 Development Workflow

### Running Tests

```bash
./scripts/test.sh
```

Or manually:
```bash
uv run python test_workflow.py
```

### Starting the Server

```bash
./scripts/start-server.sh
```

### Code Style

We use `black` and `ruff` for code formatting and linting:

```bash
uv run black .
uv run ruff check .
```

## 📝 Contribution Guidelines

### Creating Skills

New skills should be added to the `skills/` directory. Follow the template in `skills/TEMPLATE.md`:

1. Inherit from `BaseSkill`
2. Implement the `run()` method
3. Return structured data (dict with `status` and `data` keys)
4. Save artifacts to `/loot` when appropriate
5. Document parameters in docstrings

Example:
```python
from skills.base import BaseSkill

class MySkill(BaseSkill):
    """Description of what this skill does."""

    def run(self, **kwargs):
        target = kwargs.get("target")
        # ... implementation
        return {"status": "success", "data": result}
```

### Adding Tools

New MCP tools should be added to the `tools/` directory:

1. Create a new Python file (e.g., `my_tool.py`)
2. Implement a `handle_*` function
3. Register it in `server.py`
4. Add JSON schema if needed

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

### Commit Message Convention

Use clear, descriptive commit messages:

```
feat: add subdomain takeover detection skill
fix: resolve target locking race condition
docs: update agent mission template
refactor: simplify state management logic
test: add unit tests for spawn_agent tool
```

Prefixes:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test additions or changes
- `chore:` - Maintenance tasks

## 🐛 Reporting Issues

When reporting issues, please include:

1. Description of the problem
2. Steps to reproduce
3. Expected behavior
4. Actual behavior
5. Environment details (OS, Python version, Docker version)
6. Relevant logs or error messages

## 🔒 Security

For security vulnerabilities, please see [SECURITY.md](SECURITY.md) for responsible disclosure guidelines.

## 📋 Areas for Contribution

We welcome contributions in these areas:

- **Skills**: New security assessment skills (web, network, cloud)
- **Tools**: Additional MCP tools for orchestration
- **Documentation**: Tutorials, examples, architecture docs
- **Testing**: Unit tests, integration tests, test coverage
- **Performance**: Optimization and efficiency improvements
- **Integrations**: Support for additional tools and platforms

## 💬 Questions?

- Check the [README.md](README.md) for basic information
- Review [GEMINI.md](GEMINI.md) for operational guidance
- Open a discussion in GitHub Discussions
- Join our community channels (if available)

## 📜 License

By contributing to Taskmaster, you agree that your contributions will be licensed under the MIT License.
