.PHONY: help install dev test lint build clean api frontend docker-up docker-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -e ".[dev]"

dev: ## Start API + frontend dev servers (background)
	py -m uvicorn api.main:app --reload --port 8000 &
	cd web && npm run dev

api: ## Start API server only
	py -m uvicorn api.main:app --reload --port 8000

frontend: ## Start frontend dev server only
	cd web && npm run dev

test: ## Run all Python tests (excluding matplotlib crash on Windows)
	py -m pytest tests/test_agents.py tests/test_lob_matching.py tests/test_pnl_accounting.py \
		tests/test_risk_manager.py tests/test_price_process.py tests/test_multi_asset.py \
		tests/test_execution_quality.py tests/test_stat_tests.py tests/test_dqn_integration.py -q

lint: ## Run frontend type check + build
	cd web && npx tsc --noEmit

build: ## Build frontend for production
	cd web && npm run build

clean: ## Remove build artifacts
	rm -rf web/dist web/node_modules __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docker-up: ## Build and start Docker stack
	docker compose up --build -d

docker-down: ## Stop Docker stack
	docker compose down
