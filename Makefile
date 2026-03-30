.PHONY: up down install dev logs test check

up:
	docker compose up -d

down:
	docker compose down

install:
	pip install -e ".[dev]"

dev:
	python scripts/dev_bootstrap.py

logs:
	docker compose logs -f

test:
	pytest

check:
	ruff check app/ tests/
