.PHONY: ci test lint typecheck contracts dev migrate

ci: lint typecheck contracts test

test:
	python -m pytest tests -q

lint:
	ruff check app tests

typecheck:
	mypy app

contracts:
	lint-imports --config .importlinter

dev:
	uvicorn app.main:app --reload

migrate:
	alembic upgrade head
