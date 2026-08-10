from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.error_handlers import register_error_handlers
from app.core.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    ServiceUnavailableError,
    UnauthorizedError,
    UnprocessableEntityError,
)


class _Body(BaseModel):
    value: int


def _build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/errors/bad-request")
    def bad_request() -> None:
        raise BadRequestError("INVALID_FORMAT", "invalid request format")

    @app.get("/errors/unauthorized")
    def unauthorized() -> None:
        raise UnauthorizedError("UNAUTHENTICATED", "authentication required")

    @app.get("/errors/forbidden")
    def forbidden() -> None:
        raise ForbiddenError("FORBIDDEN_RESOURCE", "not your resource")

    @app.get("/errors/not-found")
    def not_found() -> None:
        raise NotFoundError("NOT_FOUND", "resource not found")

    @app.get("/errors/conflict")
    def conflict() -> None:
        raise ConflictError("GOALS_REQUIRED", "no goals exist")

    @app.get("/errors/unprocessable")
    def unprocessable() -> None:
        raise UnprocessableEntityError(
            "ANSWERS_INCOMPLETE",
            "scale answers must be exactly 24 (received 23)",
            details=[{"field": "scale_answers", "reason": "missing area=SOCIAL kind=COMMITMENT"}],
        )

    @app.get("/errors/rate-limited")
    def rate_limited() -> None:
        raise RateLimitedError("RATE_LIMITED", "too many requests", retry_after=30)

    @app.get("/errors/service-unavailable")
    def service_unavailable() -> None:
        raise ServiceUnavailableError("AI_PROVIDER_ERROR", "bedrock unavailable")

    @app.post("/errors/validation")
    def validation(body: _Body) -> dict[str, int]:
        return {"value": body.value}

    return app


client = TestClient(_build_app())


def test_bad_request_returns_400() -> None:
    response = client.get("/errors/bad-request")
    assert response.status_code == 400
    assert response.json() == {
        "error": {"code": "INVALID_FORMAT", "message": "invalid request format"},
    }


def test_unauthorized_returns_401() -> None:
    response = client.get("/errors/unauthorized")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_forbidden_returns_403() -> None:
    response = client.get("/errors/forbidden")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_RESOURCE"


def test_not_found_returns_404() -> None:
    response = client.get("/errors/not-found")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_conflict_returns_409() -> None:
    response = client.get("/errors/conflict")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GOALS_REQUIRED"


def test_unprocessable_entity_returns_422_with_details() -> None:
    response = client.get("/errors/unprocessable")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "ANSWERS_INCOMPLETE"
    assert body["error"]["details"] == [
        {"field": "scale_answers", "reason": "missing area=SOCIAL kind=COMMITMENT"},
    ]


def test_rate_limited_returns_429_with_retry_after_header() -> None:
    response = client.get("/errors/rate-limited")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert response.headers["retry-after"] == "30"


def test_service_unavailable_returns_503() -> None:
    response = client.get("/errors/service-unavailable")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_PROVIDER_ERROR"


def test_request_validation_error_returns_400_not_422() -> None:
    response = client.post("/errors/validation", json={"value": "not-an-int"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["field"] == "body.value"


def test_unmatched_route_returns_common_error_format() -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.json()
