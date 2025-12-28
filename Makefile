.PHONY: help install dev test lint format clean docker-up docker-down sync-data build-index

help:
	@echo "Medical RAG System - Available Commands"
	@echo "========================================"
	@echo "install      - Install all dependencies"
	@echo "dev          - Start development servers"
	@echo "test         - Run all tests"
	@echo "lint         - Run linters"
	@echo "format       - Format code"
	@echo "clean        - Clean build artifacts"
	@echo "docker-up    - Start Docker services"
	@echo "docker-down  - Stop Docker services"
	@echo "sync-data    - Sync drug data from API"
	@echo "build-index  - Build vector index"

# Installation
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

# Development
dev:
	@echo "Starting development servers..."
	@make -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

# Testing
test:
	cd backend && pytest -v
	cd frontend && npm test

test-backend:
	cd backend && pytest -v --cov=app --cov-report=term-missing

test-frontend:
	cd frontend && npm test

# Linting & Formatting
lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd frontend && npm run format

# Docker
docker-up:
	docker-compose -f docker/docker-compose.yml up -d

docker-down:
	docker-compose -f docker/docker-compose.yml down

docker-build:
	docker-compose -f docker/docker-compose.yml build

docker-logs:
	docker-compose -f docker/docker-compose.yml logs -f

# Data Management
sync-data:
	cd backend && python -m scripts.sync_data --pages 10

build-index:
	cd backend && python -m scripts.build_index

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf backend/.pytest_cache
	rm -rf frontend/dist
	rm -rf frontend/node_modules/.cache

# Database
db-migrate:
	cd backend && alembic upgrade head

db-rollback:
	cd backend && alembic downgrade -1

db-reset:
	cd backend && alembic downgrade base && alembic upgrade head
