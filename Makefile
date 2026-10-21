.PHONY: install migrate seed dev worker test lint evals build up down
install:
	uv sync --frozen
	cd frontend && npm ci
build:
	cd frontend && npm run build
migrate:
	uv run alembic upgrade head
seed:
	uv run python -m customerops_ai.seed
dev:
	uv run fastapi dev src/customerops_ai/api.py
worker:
	uv run celery -A customerops_ai.jobs:celery_app worker --loglevel=INFO --concurrency=2
test:
	uv run pytest -q
	cd frontend && npm test
lint:
	uv run ruff check src migrations tests scripts
	uv run ruff format --check src migrations tests scripts
	cd frontend && npm run format:check
evals:
	uv run python -m customerops_ai.evals
up:
	docker compose up -d --build
down:
	docker compose down
