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

docker-build: ## Build Docker images with buildx bake
	docker buildx bake

docker-build-api: ## Build API Docker image
	docker buildx bake api

docker-build-ui: ## Build UI Docker image
	docker buildx bake ui

docker-build-nginx: ## Build NGINX Docker image
	docker buildx bake nginx

docker-push: ## Push all Docker images to registry
	docker buildx bake push

docker-run-api: ## Run API container
	docker run -d --name api -p 8080:8080 ghcr.io/your-org/ndimensionalspectra-api:latest

docker-run-ui: ## Run UI container
	docker run -d --name ui -e API_BASE=http://nginx/api ghcr.io/your-org/ndimensionalspectra-ui:latest

docker-run-nginx: ## Run NGINX container
	docker run -d --name nginx -p 80:80 --link api --link ui ghcr.io/your-org/ndimensionalspectra-nginx:latest

docker-compose-up: ## Start all services with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop all services with docker-compose
	docker-compose down

docker-compose-logs: ## View docker-compose logs
	docker-compose logs -f

docker-compose-build: ## Build all services with docker-compose
	docker-compose build 