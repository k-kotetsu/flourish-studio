PYTHON := python3.12

.PHONY: setup setup-api setup-tools setup-web setup-infra \
	dev test lint lint-api lint-tools lint-web lint-infra \
	test-api test-infra deploy-dev

setup: setup-api setup-tools setup-web setup-infra

setup-api:
	cd api && $(PYTHON) -m venv .venv && .venv/bin/pip install -q -U pip ruff mypy pytest

setup-tools:
	cd tools && $(PYTHON) -m venv .venv && .venv/bin/pip install -q -U pip ruff mypy

setup-web:
	cd web && npm ci

setup-infra:
	cd infra && npm ci

lint: lint-api lint-tools lint-web lint-infra

lint-api:
	cd api && .venv/bin/ruff check . && .venv/bin/mypy .

lint-tools:
	cd tools && .venv/bin/ruff check . && .venv/bin/mypy .

lint-web:
	cd web && npm run lint && npm run typecheck

lint-infra:
	cd infra && npm run lint && npm run typecheck

test: test-api test-infra

test-api:
	cd api && .venv/bin/pytest

test-infra:
	cd infra && npm test

dev:
	@echo "未実装（P1-8: FastAPI雛形、P1-9: DynamoDB Local を参照）"

deploy-dev:
	@echo "未実装（P1-6: AppStack、P1-7: EdgeStack を参照。cdk deploy に置き換える）"
