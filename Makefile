PNPM ?= pnpm
PYTHON ?= python

.PHONY: up down logs test lint format

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd apps/api && $(PYTHON) -m pytest

lint:
	$(PNPM) lint
	cd apps/api && $(PYTHON) -m ruff check .

format:
	$(PNPM) format
	cd apps/api && $(PYTHON) -m ruff format .
