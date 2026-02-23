.DEFAULT_GOAL := help
PYTHON        := .venv/bin/python
PIP           := .venv/bin/pip
PYTEST        := .venv/bin/pytest

# ─── Docker ──────────────────────────────────────────────────────────────────

.PHONY: up
up: ## Start all services (build if needed)
	docker compose up --build

.PHONY: up-detach
up-detach: ## Start all services in the background
	docker compose up --build -d

.PHONY: down
down: ## Stop and remove containers
	docker compose down

.PHONY: down-volumes
down-volumes: ## Stop containers and delete volumes (resets DB)
	docker compose down -v

.PHONY: logs
logs: ## Follow logs for all services
	docker compose logs -f

.PHONY: logs-backend
logs-backend: ## Follow logs for the gRPC server
	docker compose logs -f grpc-server

.PHONY: logs-frontend
logs-frontend: ## Follow logs for the frontend
	docker compose logs -f frontend

.PHONY: build
build: ## Rebuild all Docker images without starting
	docker compose build

.PHONY: ps
ps: ## Show running containers
	docker compose ps

# ─── Python environment ───────────────────────────────────────────────────────

.PHONY: venv
venv: ## Create the virtual environment
	python3 -m venv .venv

.PHONY: install
install: venv ## Install backend runtime + test dependencies
	$(PIP) install --upgrade pip -q
	$(PIP) install -r backend/requirements.txt -r backend/requirements-test.txt

# ─── Tests ───────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Run unit tests
	cd backend && ../$(PYTEST) tests/ -v

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	cd backend && ../$(PYTEST) tests/ -v --cov=server --cov-report=term-missing

# ─── Proto generation ─────────────────────────────────────────────────────────

.PHONY: proto
proto: ## Regenerate protobuf stubs for backend and frontend
	$(PYTHON) -m grpc_tools.protoc \
		-I backend \
		--python_out=backend \
		--grpc_python_out=backend \
		backend/metrics.proto
	$(PYTHON) -m grpc_tools.protoc \
		-I frontend \
		--python_out=frontend \
		--grpc_python_out=frontend \
		frontend/metrics.proto

# ─── Help ─────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
