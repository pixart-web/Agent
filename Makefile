PNPM ?= pnpm
PYTHON ?= python

.PHONY: up down logs test lint format migrate migration seed typecheck ci

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	$(PYTHON) -m pytest apps/api

lint:
	$(PNPM) lint
	$(PYTHON) -m ruff check apps/api

format:
	$(PNPM) format
	$(PYTHON) -m ruff format apps/api

migrate:
	cd apps/api && $(PYTHON) -m alembic upgrade head

migration:
	@test -n "$(name)" || (echo "Usage: make migration name=\"description\"" && exit 1)
	cd apps/api && $(PYTHON) -m alembic revision --autogenerate -m "$(name)"

seed:
	cd apps/api && $(PYTHON) -m app.scripts.seed_agents

typecheck:
	$(PNPM) typecheck

ci:
	$(PNPM) format:check
	$(PNPM) lint
	$(PNPM) typecheck
	$(PNPM) build
	$(PYTHON) -m ruff check apps/api
	$(PYTHON) -m ruff format --check apps/api
	cd apps/api && $(PYTHON) -m alembic upgrade head --sql
	$(PYTHON) -m pytest apps/api
