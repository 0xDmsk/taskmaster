.PHONY: help install build start test clean lint format dev

# Default target
help:
	@echo "Taskmaster - Agentic Security Orchestration Platform"
	@echo ""
	@echo "Available targets:"
	@echo "  make install    - Install dependencies with UV"
	@echo "  make build      - Build the Kali agent container"
	@echo "  make start      - Start the MCP server"
	@echo "  make test       - Run the test suite"
	@echo "  make lint       - Run code linters (ruff)"
	@echo "  make format     - Format code with black"
	@echo "  make clean      - Clean runtime state and cache"
	@echo "  make spawn      - Spawn an interactive agent"
	@echo "  make dev        - Setup development environment"
	@echo ""

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	uv sync
	@echo "✅ Dependencies installed"

# Build agent container
build:
	@echo "🏗️  Building agent container..."
	./scripts/build.sh

# Start MCP server
start:
	@echo "🚀 Starting MCP server..."
	./scripts/start-server.sh

# Run tests
test:
	@echo "🧪 Running tests..."
	./scripts/test.sh

# Run linters
lint:
	@echo "🔍 Running linters..."
	uv run ruff check .

# Format code
format:
	@echo "✨ Formatting code..."
	uv run black .

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	./scripts/cleanup.sh

# Spawn agent
spawn:
	@echo "🤖 Spawning agent..."
	./scripts/spawn-agent.sh

# Development setup
dev: install
	@echo "🛠️  Setting up development environment..."
	@cp -n .env.example .env 2>/dev/null || true
	@mkdir -p audit/loot state
	@echo "✅ Development environment ready"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Run 'make build' to build the agent container"
	@echo "  3. Run 'make start' to start the server"

# Check status
status:
	@echo "📊 Taskmaster Status"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Dependencies:"
	@command -v uv >/dev/null 2>&1 && echo "  ✅ UV installed" || echo "  ❌ UV not found"
	@command -v docker >/dev/null 2>&1 && echo "  ✅ Docker installed" || echo "  ❌ Docker not found"
	@command -v socat >/dev/null 2>&1 && echo "  ✅ Socat installed" || echo "  ❌ Socat not found"
	@echo ""
	@echo "Configuration:"
	@test -f .env && echo "  ✅ .env configured" || echo "  ⚠️  .env missing (run: cp .env.example .env)"
	@echo ""
	@echo "Agent Container:"
	@docker images kali-smart-operator:latest --format "  ✅ {{.Repository}}:{{.Tag}} ({{.Size}})" 2>/dev/null || echo "  ⚠️  Not built (run: make build)"
	@echo ""
	@echo "Runtime State:"
	@test -f state/executions.json && echo "  📝 Executions: $$(cat state/executions.json | wc -l)" || echo "  📝 Executions: 0 (fresh state)"
	@test -d audit/loot && echo "  📦 Loot items: $$(find audit/loot -type f ! -name .gitkeep | wc -l)" || echo "  📦 Loot items: 0"
