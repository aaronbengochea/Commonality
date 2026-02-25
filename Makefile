PYTHON := python3.12

.PHONY: up down build restart logs clean setup \
        venv-backend install install-backend install-frontend \
        test lint shell-backend shell-frontend

# ─── Setup ────────────────────────────────────────────────────

# Copy .env.example to .env if it doesn't exist
setup:
	@test -f .env || cp .env.example .env
	@echo ".env file ready — fill in your API keys"

# ─── Local Development ────────────────────────────────────────

# Create backend virtual environment
venv-backend:
	$(PYTHON) -m venv backend/.venv
	@echo "Backend venv created at backend/.venv"

# Install all dependencies locally
install: install-backend install-frontend

# Install backend dependencies into its venv
install-backend:
	@test -d backend/.venv || $(PYTHON) -m venv backend/.venv
	backend/.venv/bin/pip install -e "backend[dev]"

# Install frontend dependencies
install-frontend:
	cd frontend && npm install

# Run backend tests locally
test:
	backend/.venv/bin/pytest backend

# Run frontend linter locally
lint:
	cd frontend && npm run lint

# ─── Docker ───────────────────────────────────────────────────

# Start all services
up:
	docker compose up -d

# Build images from scratch (no cache)
build:
	docker compose build --no-cache

# Stop all services
down:
	docker compose down

# Stop all services and remove volumes
clean:
	docker compose down -v

# Restart all services
restart:
	docker compose restart

# Tail logs for all services
logs:
	docker compose logs -f

# Tail logs for a specific service (usage: make logs-backend)
logs-%:
	docker compose logs -f $*

# Open a shell in the backend container
shell-backend:
	docker compose exec backend bash

# Open a shell in the frontend container
shell-frontend:
	docker compose exec frontend sh
