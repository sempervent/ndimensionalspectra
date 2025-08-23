.PHONY: help build run cli api test clean docker-build docker-run docker-cli

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build the package
	uv sync

run: ## Run the CLI (default mode)
	python -m ndimensionalspectra

cli: ## Run CLI with specific command (usage: make cli ARGS="schema")
	python -m ndimensionalspectra $(ARGS)

api: ## Run the API server
	python -m ndimensionalspectra --api

test: ## Run tests
	pytest

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage

docker-build: ## Build Docker image
	docker build -t ndimensionalspectra .

docker-run: ## Run Docker container in API mode
	docker run -p 8080:8080 ndimensionalspectra

docker-cli: ## Run Docker container in CLI mode (usage: make docker-cli ARGS="schema")
	docker run -e OM_MODE=cli -e OM_ARGS="$(ARGS)" ndimensionalspectra

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	docker-compose down

docker-compose-logs: ## View docker-compose logs
	docker-compose logs -f 