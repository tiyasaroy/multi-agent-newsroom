.PHONY: install dev dev-web dev-api infra-up infra-down check

install:
	pnpm install
	python3 -m venv .venv
	.venv/bin/pip install -e "services/api[dev]"

dev:
	@echo "Run 'make dev-web' and 'make dev-api' in separate terminals."

dev-web:
	pnpm dev:web

dev-api:
	.venv/bin/uvicorn newsroom_api.main:app --app-dir services/api/src --reload --port 8000

infra-up:
	docker compose -f infra/compose.yaml up -d

infra-down:
	docker compose -f infra/compose.yaml down

check:
	pnpm lint
	pnpm typecheck
	.venv/bin/ruff check services/api
	.venv/bin/pytest services/api/tests
