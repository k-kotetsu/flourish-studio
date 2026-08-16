"""`POST /auth/register`。09_API設計5.5、08_データモデル3.4、完了条件

「登録でレポートがアカウントへ移る。ゲスト側はTTLに委ねる」の確認。実際のCognito呼び出しは
行わない。`app.domain.cognito.sign_up_and_confirm`をフェイクに差し替える。
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.security import GUEST_COOKIE_NAME, SESSION_COOKIE_NAME
from app.db import repository
from app.db.keys import PROFILE_SK, assessment_sk, guest_pk, user_pk
from app.domain import cognito
from app.domain.assessment import build_assessment_item, now_iso
from app.domain.assessment_precompute import CommitmentResult
from app.main import app

_REGISTER_BODY = {"email": "new-user@example.com", "password": "correct-horse-battery-9"}


def _install_fake_sign_up(monkeypatch: pytest.MonkeyPatch, user_id: str) -> None:
    def fake_sign_up_and_confirm(*, email: str, password: str) -> str:
        return user_id

    monkeypatch.setattr(cognito, "sign_up_and_confirm", fake_sign_up_and_confirm)


def test_returns_201_and_sets_session_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid.uuid4().hex
    _install_fake_sign_up(monkeypatch, user_id)
    client = TestClient(app, base_url="https://testserver")

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "fresh@example.com", "password": "correct-horse-battery-9"},
    )

    assert response.status_code == 201
    assert SESSION_COOKIE_NAME in client.cookies
    profile = repository.get_item(user_pk(user_id), PROFILE_SK)
    assert profile is not None
    assert profile["entity"] == "USER"
    assert profile["guest_session_id"] is None


def test_returns_409_email_taken_when_cognito_reports_username_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_sign_up_and_confirm(*, email: str, password: str) -> str:
        raise cognito.EmailTakenError

    monkeypatch.setattr(cognito, "sign_up_and_confirm", fake_sign_up_and_confirm)
    client = TestClient(app, base_url="https://testserver")

    response = client.post("/api/v1/auth/register", json=_REGISTER_BODY)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"
    assert SESSION_COOKIE_NAME not in client.cookies


def test_returns_422_weak_password_for_common_password(monkeypatch: pytest.MonkeyPatch) -> None:
    # 流出パスワードリストでの拒否はCognitoを呼ぶ前に行われる(11_技術構成7.4)。
    # 呼ばれたら失敗させ、リストでの拒否がここより先に効いていることを保証する。
    def fail_if_called(*, email: str, password: str) -> str:
        raise AssertionError("common password must be rejected before calling Cognito")

    monkeypatch.setattr(cognito, "sign_up_and_confirm", fail_if_called)
    client = TestClient(app, base_url="https://testserver")

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "password1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "WEAK_PASSWORD"


def test_returns_422_weak_password_when_cognito_rejects_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_sign_up_and_confirm(*, email: str, password: str) -> str:
        raise cognito.InvalidPasswordError

    monkeypatch.setattr(cognito, "sign_up_and_confirm", fake_sign_up_and_confirm)
    client = TestClient(app, base_url="https://testserver")

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak2@example.com", "password": "Zx8!Qwzmvt"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "WEAK_PASSWORD"


def _fake_guest_assessment_item(guest_token: str) -> dict[str, Any]:
    return build_assessment_item(
        owner=guest_pk(guest_token),
        assessment_id=uuid.uuid4().hex,
        question_set_version="2026-08-v1",
        scale_answers=[],
        free_text_answers=[],
        ai_output={
            "nickname": "テストのあだ名",
            "articulation_stage": "SPROUT",
            "safety_flag": False,
            "areas": [],
        },
        commitment=CommitmentResult(stage="SEED", score=3),
        started_at=now_iso(),
        completed_at=now_iso(),
    )


def test_guest_assessment_and_cookie_migrate_to_new_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4().hex
    _install_fake_sign_up(monkeypatch, user_id)

    # `fs_guest`はサーバーからのSet-Cookieで発行させる(手動で`client.cookies.set`すると
    # ドメイン属性が空文字になり、後続のCookie削除がhttpxのCookieJarで別エントリとして
    # 扱われてしまうため)。
    client = TestClient(app, base_url="https://testserver")
    client.post("/api/v1/guest-sessions")
    guest_token = client.cookies[GUEST_COOKIE_NAME]

    report_item = _fake_guest_assessment_item(guest_token)
    repository.put_item(report_item)
    assert "expires_at" in report_item

    response = client.post("/api/v1/auth/register", json=_REGISTER_BODY)

    assert response.status_code == 201
    # ゲストCookieは破棄し、ログインセッションへ切り替わる(11_技術構成7.3)
    assert GUEST_COOKIE_NAME not in client.cookies
    assert SESSION_COOKIE_NAME in client.cookies

    migrated = repository.get_item(user_pk(user_id), assessment_sk(report_item["assessment_id"]))
    assert migrated is not None
    assert "expires_at" not in migrated
    assert migrated["guest_session_id"] == guest_token

    # ゲスト側のアイテムはTTLに委ねて消さない(08_データモデル3.4)
    guest_item_still_present = repository.get_item(guest_pk(guest_token), "GUEST")
    assert guest_item_still_present is not None
    assert guest_item_still_present["converted_user_id"] == user_id
    original_report_still_present = repository.get_item(
        guest_pk(guest_token), assessment_sk(report_item["assessment_id"])
    )
    assert original_report_still_present is not None
