from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.core.security import (
    clear_auth_cookie,
    generate_token,
    hash_token,
    set_auth_cookie,
)


def test_generate_token_is_unique_and_url_safe() -> None:
    token_a = generate_token()
    token_b = generate_token()

    assert token_a != token_b
    assert len(token_a) >= 32
    assert all(c.isalnum() or c in "-_" for c in token_a)


def test_hash_token_is_deterministic_and_one_way() -> None:
    token = generate_token()

    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token


def test_hash_token_differs_for_different_tokens() -> None:
    assert hash_token(generate_token()) != hash_token(generate_token())


def _build_cookie_app() -> FastAPI:
    app = FastAPI()

    @app.post("/set")
    def set_cookie(response: Response) -> dict[str, bool]:
        set_auth_cookie(response, "fs_test", "token-value")
        return {"ok": True}

    @app.post("/clear")
    def clear_cookie(response: Response) -> dict[str, bool]:
        clear_auth_cookie(response, "fs_test")
        return {"ok": True}

    return app


client = TestClient(_build_cookie_app(), base_url="https://testserver")


def test_set_auth_cookie_has_expected_attributes() -> None:
    response = client.post("/set")

    set_cookie_header = response.headers["set-cookie"]
    assert "fs_test=token-value" in set_cookie_header
    assert "HttpOnly" in set_cookie_header
    assert "Secure" in set_cookie_header
    assert "SameSite=lax" in set_cookie_header
    assert "Max-Age=2592000" in set_cookie_header
    assert "Path=/" in set_cookie_header


def test_clear_auth_cookie_expires_immediately() -> None:
    response = client.post("/clear")

    set_cookie_header = response.headers["set-cookie"]
    assert 'fs_test=""' in set_cookie_header or "fs_test=" in set_cookie_header
    assert "Max-Age=0" in set_cookie_header
