.PHONY: ci test lint typecheck contracts dev migrate install-hooks

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

install-hooks:
	cp scripts/git-hooks/pre-commit ../../.git/hooks/pre-commit
	chmod +x ../../.git/hooks/pre-commit
	@echo "pre-commit hook installed. See v1/backend/scripts/git-hooks/README.md"
