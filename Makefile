# Competitive Intelligence Platform - Makefile
.PHONY: help install install-dev test test-unit test-integration lint format typecheck clean build run demo monitor docker-build docker-up docker-down

# Default target
help:
	@echo "Competitive Intelligence Platform - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install        Install production dependencies"
	@echo "  install-dev    Install development dependencies"
	@echo "  test           Run all tests"
	@echo "  test-unit      Run unit tests only"
	@echo "  test-integration Run integration tests (requires API keys)"
	@echo "  lint           Run ruff linter"
	@echo "  format         Format code with ruff"
	@echo "  typecheck      Run mypy type checking"
	@echo "  clean          Clean build artifacts"
	@echo ""
	@echo "Running:"
	@echo "  run            Run CLI help"
	@echo "  demo           Run quick demo"
	@echo "  monitor        Start continuous monitoring (interactive)"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build   Build Docker image"
	@echo "  docker-up      Start full stack with docker-compose"
	@echo "  docker-down    Stop docker-compose stack"
	@echo "  docker-logs    View docker-compose logs"
	@echo ""
	@echo "Examples:"
	@echo "  example-basic  Run basic research example"
	@echo "  example-monitor Run monitoring example"
	@echo "  example-advanced Run advanced custom agents example"

# Installation
install:
	uv sync --frozen --no-dev

install-dev:
	uv sync --frozen --all-extras
	uv run pre-commit install

# Testing
test: test-unit test-integration

test-unit:
	uv run pytest tests/unit -v --tb=short

test-integration:
	@if [ -z "$$SERPAPI_API_KEY" ] || [ -z "$$OPENAI_API_KEY" ]; then \
		echo "Skipping integration tests: SERPAPI_API_KEY and OPENAI_API_KEY required"; \
	else \
		uv run pytest tests/integration -v --tb=short; \
	fi

# Code Quality
lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

typecheck:
	uv run mypy src/

# Cleanup
clean:
	rm -rf build/ dist/ *.egg-info/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Build
build: clean
	uv build

# Run CLI
run:
	uv run competitive-intel --help

demo:
	uv run competitive-intel demo

monitor:
	@echo "Starting monitoring (Ctrl+C to stop)..."
	@echo "Configure entities in .env or pass as arguments"
	uv run competitive-intel monitor "AI Companies" --entity "OpenAI,Anthropic,Google" --interval 60

# Examples
example-basic:
	uv run python examples/basic_research.py

example-monitor:
	uv run python examples/continuous_monitoring.py

example-advanced:
	uv run python examples/advanced_custom_agents.py

# Docker
docker-build:
	docker build -t competitive-intel:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-ps:
	docker-compose ps

# Development utilities
dev-shell:
	uv run python -c "import competitive_intel; print('OK')"

check-env:
	@echo "SERPAPI_API_KEY: $${SERPAPI_API_KEY:-[NOT SET]}"
	@echo "OPENAI_API_KEY: $${OPENAI_API_KEY:-[NOT SET]}"
	@echo "ENVIRONMENT: $${ENVIRONMENT:-development}"

# Pre-commit
pre-commit:
	uv run pre-commit run --all-files

# Coverage
coverage:
	uv run pytest tests/unit --cov=competitive_intel --cov-report=html --cov-report=term
	@echo "Open htmlcov/index.html to view coverage report"