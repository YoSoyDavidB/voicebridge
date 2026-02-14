.PHONY: help install install-dev test test-unit test-integration test-performance lint format typecheck clean run

help:
	@echo "VoiceBridge Development Commands"
	@echo "================================"
	@echo "install          - Install production dependencies"
	@echo "install-dev      - Install development dependencies"
	@echo "test             - Run all unit tests"
	@echo "test-unit        - Run unit tests only"
	@echo "test-integration - Run integration tests (requires API keys)"
	@echo "test-performance - Run performance benchmarks"
	@echo "lint             - Run linter (ruff)"
	@echo "format           - Format code with ruff"
	@echo "typecheck        - Run type checker (mypy)"
	@echo "clean            - Remove build artifacts and cache"
	@echo "run              - Run VoiceBridge application"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,test]"

test:
	pytest -m unit

test-unit:
	pytest -m unit -v

test-integration:
	pytest -m integration -v

test-performance:
	pytest -m performance -v

test-all:
	pytest -v

coverage:
	pytest --cov=src/voicebridge --cov-report=html --cov-report=term

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/voicebridge

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	python -m voicebridge

# Development helpers
check: lint typecheck test-unit
	@echo "✅ All checks passed!"

watch-test:
	pytest-watch -m unit
