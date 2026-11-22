# ==============================================================================
# Makefile — Commerce API Developer Commands
# ==============================================================================
# Usage: make <target>
#
# Examples:
#   make install    → Set up virtual environment and install all dependencies
#   make run        → Start the development server
#   make test       → Run the full automated test suite
#   make coverage   → Run tests + generate HTML coverage report
#   make demo       → Run interactive live scenario demo
#   make lint       → Run ruff linter
#   make clean      → Remove generated files and caches
# ==============================================================================

VENV       := .venv
PYTHON     := $(VENV)/bin/python
PIP        := $(VENV)/bin/pip
PYTEST     := $(VENV)/bin/pytest
UVICORN    := $(VENV)/bin/uvicorn
RUFF       := $(VENV)/bin/ruff

.PHONY: install run test coverage demo lint clean help

# ── Default target ─────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Commerce API — Available Commands:"
	@echo "------------------------------------"
	@echo "  make install   → Set up virtual environment & install dependencies"
	@echo "  make run       → Start the development server (http://127.0.0.1:8000)"
	@echo "  make test      → Run all 29 automated tests"
	@echo "  make coverage  → Run tests + open HTML coverage report"
	@echo "  make demo      → Run interactive live scenario demo"
	@echo "  make lint      → Run ruff linter (zero tolerance)"
	@echo "  make clean     → Remove all generated caches and reports"
	@echo ""

# ── Setup ──────────────────────────────────────────────────────────────────────
install:
	@echo "🐍 Creating virtual environment..."
	python3 -m venv $(VENV)
	@echo "📦 Upgrading pip..."
	$(PIP) install --upgrade pip
	@echo "📦 Installing dependencies..."
	$(PIP) install -r requirements-dev.txt
	@echo "✅ Setup complete! Run 'make run' to start the server."

# ── Run ────────────────────────────────────────────────────────────────────────
run:
	@echo "🚀 Starting Commerce API..."
	@echo "   Swagger UI: http://127.0.0.1:8000/docs"
	@echo "   Press CTRL+C to stop."
	$(UVICORN) app.main:app --host 127.0.0.1 --port 8000 --reload

# ── Testing ────────────────────────────────────────────────────────────────────
test:
	@echo "🧪 Running full test suite..."
	$(PYTEST) -v

coverage:
	@echo "🧪 Running tests with HTML coverage report..."
	$(PYTEST) -v --cov=app --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "📊 HTML Coverage Report: file://$(PWD)/htmlcov/index.html"

# ── Live Demo ──────────────────────────────────────────────────────────────────
demo:
	@echo "🎬 Running interactive live scenario demo..."
	./scripts/demo_test.sh

# ── Lint ───────────────────────────────────────────────────────────────────────
lint:
	@echo "🔍 Running ruff linter..."
	$(RUFF) check app/ tests/
	@echo "✅ All checks passed!"

# ── Clean ──────────────────────────────────────────────────────────────────────
clean:
	@echo "🧹 Cleaning up generated files..."
	rm -rf htmlcov/ .coverage .pytest_cache/ .ruff_cache/
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Clean complete!"
