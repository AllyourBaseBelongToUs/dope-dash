.PHONY: help install dev build test clean docker-up docker-down docker-logs lint format

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install all dependencies
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Installing Playwright browsers..."
	cd frontend && npx playwright install
	@echo "Setting up Python virtual environment..."
	cd backend && python3 -m venv venv || echo "Note: Requires 'apt install python3.12-venv'"
	@echo "Installing backend dependencies..."
	cd backend && ./venv/bin/pip install -r requirements.txt || echo "Note: Install venv first"

dev: ## Start development servers (frontend and backend)
	@echo "Starting development environment..."
	@make -j2 dev-frontend dev-backend

dev-frontend: ## Start frontend dev server
	cd frontend && npm run dev

dev-backend: ## Start backend dev server
	cd backend && ./venv/bin/uvicorn app.main:app --reload --port 8000

build: ## Build frontend for production
	cd frontend && npm run build

build-backend: ## Build backend Docker image
	docker build -t dope-dash-backend ./backend

build-frontend: ## Build frontend Docker image
	docker build -t dope-dash-frontend ./frontend

test: ## Run all tests
	@make test-frontend test-backend

test-frontend: ## Run frontend tests
	cd frontend && npm run test

test-backend: ## Run backend tests
	cd backend && ./venv/bin/pytest

lint: ## Run linters
	@make lint-frontend lint-backend

lint-frontend: ## Lint frontend code
	cd frontend && npm run lint
	cd frontend && npm run type-check

lint-backend: ## Lint backend code
	cd backend && ./venv/bin/ruff check app
	cd backend && ./venv/bin/mypy app

format: ## Format code
	@make format-frontend format-backend

format-frontend: ## Format frontend code (prettier)
	cd frontend && npm run lint -- --fix

format-backend: ## Format backend code
	cd backend && ./venv/bin/black app
	cd backend && ./venv/bin/ruff check --fix app

docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

clean: ## Clean build artifacts
	rm -rf frontend/node_modules frontend/.next frontend/dist
	rm -rf backend/venv backend/__pycache__
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache
	docker-compose down -v
