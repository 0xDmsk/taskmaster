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

4. Build the agent container(s):
```bash
make build              # Kali executor
make build-playwright   # Playwright executor (optional)
```

## 🛠 Development Workflow

### Running Tests

```bash
make test
```

Or directly with UV:
```bash
uv run pytest tests/
uv run pytest tests/unit/test_base_skill.py  # single file
```

### Starting the Server

```bash
make start
```

### Code Style

We use `black` and `ruff` for code formatting and linting:

```bash
uv run black .
uv run ruff check .
```

## 📝 Contribution Guidelines

### Creating Skills

New skills should be added to the `skills/` directory. Follow the template in `skills/TEMPLATE.md`.

**CLI skills** (run in the Kali executor, `action_type: "skill"`):

1. Inherit from `BaseSkill` (`skills/base.py`)
2. Set `tool` and `tool_version_command` class attributes
3. Implement `build_command(**kwargs) -> str` — construct the CLI command
4. Implement `parse_output(stdout, stderr, exit_code) -> dict` — parse raw output into structured findings
5. One tool per skill class — do not combine multiple tools in a single skill
6. Use `self.save_artifact()` / `self.save_json()` for loot (automatically tracked)

**Browser skills** (run in the Playwright executor, `action_type: "playwright_skill"`):

1. Inherit from `BaseBrowserSkill` (`skills/browser.py`)
2. Implement `run_browser(page, context, **kwargs) -> dict` — perform browser automation and return findings
3. Use `self.save_screenshot()`, `self.save_artifact()`, `self.save_json()` for loot
4. Set `BROWSER_PROXY` env var to route traffic through a proxy (e.g. Burp/ZAP)

Example:
```python
from skills.base import BaseSkill

class MyToolScan(BaseSkill):
    """Wraps mytool for scanning."""

    tool = "mytool"
    tool_version_command = "mytool --version"

    def build_command(self, **kwargs) -> str:
        host = kwargs.get("host") or self.target
        if not host:
            raise ValueError("host or target is required")
        return f"mytool scan {host} -o /loot/mytool_output.json"

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        # Parse and return structured findings
        return {"scanned": True, "results": [...]}
```

The concrete `run()` method in `BaseSkill` handles execution, timing, version detection, and assembles the JSON envelope automatically.

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
- Review [OPERATIONAL_GUIDE.md](OPERATIONAL_GUIDE.md) for operational guidance
- Open a discussion in GitHub Discussions
- Join our community channels (if available)

## 📜 License

By contributing to Taskmaster, you agree that your contributions will be licensed under the MIT License.
