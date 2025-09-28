# AI-Maga Development Commands

.PHONY: help install run test lint clean docker-build docker-run

help: ## Show this help message
	@echo "AI-Maga Development Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

run: ## Run the application locally
	python -m app.main

test: ## Run tests
	pytest tests/ -v

lint: ## Run linting (requires ruff)
	ruff check app/ tests/
	ruff format app/ tests/

format: ## Format code (requires ruff)
	ruff format app/ tests/

docker-build: ## Build Docker image
	docker build -t ai-maga-bot .

docker-run: ## Run Docker container
	docker run -p 8080:8080 --env-file .env ai-maga-bot

docker-compose-up: ## Run with docker-compose
	docker-compose up --build

docker-compose-down: ## Stop docker-compose
	docker-compose down

clean: ## Clean up Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

health-check: ## Check health endpoint
	curl -f http://localhost:8080/healthz || echo "Health check failed"

setup: ## Initial setup - copy env and install deps
	cp .env.example .env
	$(MAKE) install
