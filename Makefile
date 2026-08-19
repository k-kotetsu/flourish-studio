PYTHON := python3.12

.PHONY: setup setup-api setup-tools setup-web setup-infra \
	dev test lint lint-api lint-tools lint-web lint-infra \
	test-api test-tools test-web test-infra deploy-dev dynamodb-local-up dynamodb-local-down eval

# DynamoDB Localはリクエスト署名を検証しないが、boto3のクライアント生成には
# 認証情報が要る。値そのものに意味はない。
LOCAL_AWS_ENV := AWS_ACCESS_KEY_ID=local AWS_SECRET_ACCESS_KEY=local \
	DYNAMODB_ENDPOINT_URL=http://localhost:8000

setup: setup-api setup-tools setup-web setup-infra

setup-api:
	cd api && $(PYTHON) -m venv .venv && .venv/bin/pip install -q -U pip ruff mypy pytest httpx "boto3-stubs[dynamodb,sqs,cognito-idp]" types-jsonschema -r requirements.txt

setup-tools:
	cd tools && $(PYTHON) -m venv .venv && .venv/bin/pip install -q -U pip ruff mypy pytest boto3 "boto3-stubs[dynamodb]"

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

test: test-api test-tools test-web test-infra

test-api: dynamodb-local-up
	cd api && $(LOCAL_AWS_ENV) .venv/bin/pytest

test-tools: dynamodb-local-up
	cd tools && $(LOCAL_AWS_ENV) .venv/bin/pytest

test-web:
	cd web && npm test

test-infra:
	cd infra && npm test

dynamodb-local-up:
	docker compose up -d dynamodb-local

dynamodb-local-down:
	docker compose down

dev: dynamodb-local-up
	@trap 'kill 0' EXIT; \
	(cd api && $(LOCAL_AWS_ENV) .venv/bin/uvicorn app.main:app --reload --port 8080) & \
	(cd web && npm run dev) & \
	wait

deploy-dev:
	@echo "未実装（P1-6: AppStack、P1-7: EdgeStack を参照。cdk deploy に置き換える）"

# 評価セット(10_AIプロンプト設計6.1)を実行し、api/eval_output/にJSONで書き出す。
# 実際にBedrockを呼ぶため、事前に `aws sso login --profile flourish-dev` などで認証が要る。
eval:
	cd api && .venv/bin/python -m app.eval.run
