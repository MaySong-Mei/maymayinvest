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
	rm -f ../../.git/hooks/pre-commit  # remove any stale pre-commit hook from earlier design
	cp scripts/git-hooks/commit-msg ../../.git/hooks/commit-msg
	chmod +x ../../.git/hooks/commit-msg
	@echo "commit-msg hook installed (stale pre-commit removed if present). See v1/backend/scripts/git-hooks/README.md"
