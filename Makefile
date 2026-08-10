.PHONY: up down build logs test lint migrate revision shell-api shell-db

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f api worker

test:
	pip install -r requirements-dev.txt -q
	pytest -v

lint:
	ruff check src tests
	mypy src

migrate:
	docker compose exec api alembic upgrade head

revision:
	docker compose exec api alembic revision --autogenerate -m "$(m)"

shell-api:
	docker compose exec api bash

shell-db:
	docker compose exec db psql -U rag_user -d rag_db
