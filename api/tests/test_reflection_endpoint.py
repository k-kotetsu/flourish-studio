"""`GET /reflections/context`、`POST /reflections`、`GET /reflections/{id}`。
09_API設計5.13〜5.15、04_画面設計S-61〜S-63。

目標0件でも空配列を返す(409にしない)ことと、複数領域にまたがる目標をまとめて返すことを確認する。
実際のBedrock呼び出し・SQS送信は行わない(`send_job_message`をフェイクに差し替える)。
生成成功時の保存・失敗時に何も残らないことは`test_worker_handler.py`で確認する。
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.security import SESSION_COOKIE_NAME
from app.db import repository
from app.domain import area_plan as area_plan_domain
from app.domain import job as job_domain
from app.domain import purpose as purpose_domain
from app.domain.reflection import ResolvedStatus, build_reflection_item, now_iso
from app.domain.session import create_session
from app.domain.user import build_profile_item
from app.main import app


def _client_with_logged_in_user() -> tuple[TestClient, str]:
    user_id = uuid.uuid4().hex
    repository.put_item(build_profile_item(user_id, guest_session_id=None))
    token, _ = create_session(user_id)
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client, user_id


def _save_purpose(user_id: str) -> None:
    purpose_domain.save_purpose(
        user_id=user_id,
        statement="まわりの人が安心して力を出せる存在でありたい。",
        original_statement="まわりの人が安心して力を出せる存在でありたい。",
        selected_direction="OTHERS",
        selected_label="まわりの人とともに",
        choices=[],
        conversation=[],
    )


def _save_area_plan(user_id: str, area: str, *, goal_bodies: list[str]) -> None:
    area_plan_domain.save_area_plan(
        user_id=user_id,
        area=area,
        choices=[],
        conversation=[],
        selected_direction="DEEPEN",
        selected_label="今の場所で深める",
        original_ideal_state="今の理想状態。",
        ideal_state="今の理想状態。",
        goals=[area_plan_domain.GoalInput(body=body) for body in goal_bodies],
    )


def test_returns_401_without_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.get("/api/v1/reflections/context")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_returns_empty_array_when_no_area_has_been_created_yet() -> None:
    """5.13「目標が0件の場合は空配列を返す。409にしない」。"""
    client, _ = _client_with_logged_in_user()

    response = client.get("/api/v1/reflections/context")

    assert response.status_code == 200
    assert response.json() == {"goals": []}


def test_returns_goals_from_every_created_area_in_area_and_sort_order() -> None:
    client, user_id = _client_with_logged_in_user()
    _save_purpose(user_id)
    _save_area_plan(
        user_id, "CAREER", goal_bodies=["職務経歴書を書き上げる", "月に1回、社外の人と話す"]
    )
    _save_area_plan(user_id, "SOCIAL", goal_bodies=["家族と週末に話す時間を取る"])

    response = client.get("/api/v1/reflections/context")

    assert response.status_code == 200
    goals = response.json()["goals"]
    assert [goal["area"] for goal in goals] == ["CAREER", "CAREER", "SOCIAL"]
    assert [goal["body"] for goal in goals] == [
        "職務経歴書を書き上げる",
        "月に1回、社外の人と話す",
        "家族と週末に話す時間を取る",
    ]
    assert all(isinstance(goal["goal_key"], str) and goal["goal_key"] for goal in goals)
    # goal_id(Version 0.2で廃止、08_データモデル5.3)は返さない
    assert all("goal_id" not in goal for goal in goals)


def test_goal_key_matches_the_area_plan_so_the_frontend_can_correlate_with_edits() -> None:
    client, user_id = _client_with_logged_in_user()
    _save_purpose(user_id)
    _save_area_plan(user_id, "PHYSICAL", goal_bodies=["週2回歩く"])
    plan = area_plan_domain.get_area_plan(user_id, "PHYSICAL")
    assert plan is not None
    expected_key = plan["goals"][0]["goal_key"]

    response = client.get("/api/v1/reflections/context")

    goals = response.json()["goals"]
    assert goals == [{"goal_key": expected_key, "area": "PHYSICAL", "body": "週2回歩く"}]


# --- POST /reflections ---


class _FakeSendJobMessage:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, job_id: str, kind: str, payload: dict[str, Any] | None = None) -> None:
        self.calls.append({"job_id": job_id, "kind": kind, "payload": payload})


def _install_fake_send(monkeypatch: pytest.MonkeyPatch) -> _FakeSendJobMessage:
    fake_send = _FakeSendJobMessage()
    monkeypatch.setattr("app.api.v1.reflections.send_job_message", fake_send)
    return fake_send


def test_post_reflections_returns_409_when_no_goals_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5.14「目標0件: 409 NO_GOALS」。"""
    fake_send = _install_fake_send(monkeypatch)
    client, _ = _client_with_logged_in_user()

    response = client.post("/api/v1/reflections", json={"statuses": [], "note": None})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NO_GOALS"
    assert fake_send.calls == []


def test_post_reflections_returns_422_when_statuses_do_not_cover_every_goal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5.14「網羅: 現行の全目標に対して1件ずつ必要。欠けていれば422」。"""
    fake_send = _install_fake_send(monkeypatch)
    client, user_id = _client_with_logged_in_user()
    _save_purpose(user_id)
    _save_area_plan(user_id, "CAREER", goal_bodies=["職務経歴書を書き上げる", "社外の人と話す"])

    response = client.post(
        "/api/v1/reflections",
        json={"statuses": [{"goal_key": "not-a-real-key", "status": "ON_TRACK"}], "note": None},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "STATUSES_INCOMPLETE"
    assert fake_send.calls == []


def test_post_reflections_returns_202_and_queues_a_job(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_send = _install_fake_send(monkeypatch)
    client, user_id = _client_with_logged_in_user()
    _save_purpose(user_id)
    _save_area_plan(user_id, "CAREER", goal_bodies=["職務経歴書を書き上げる"])
    plan = area_plan_domain.get_area_plan(user_id, "CAREER")
    assert plan is not None
    goal_key = plan["goals"][0]["goal_key"]

    response = client.post(
        "/api/v1/reflections",
        json={
            "statuses": [{"goal_key": goal_key, "status": "STALLED"}],
            "note": "今週は時間が取れなかった",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["poll_after_ms"] == 1500
    job_id = body["job_id"]

    job_item = job_domain.get_job(job_id)
    assert job_item is not None
    assert job_item["kind"] == "REFLECTION_SUMMARY"
    assert job_item["status"] == "QUEUED"

    assert len(fake_send.calls) == 1
    payload = fake_send.calls[0]["payload"]
    assert payload["purpose_statement"] == "まわりの人が安心して力を出せる存在でありたい。"
    assert payload["statuses"] == [
        {
            "goal_key": goal_key,
            "area": "CAREER",
            "goal_body": "職務経歴書を書き上げる",
            "status": "STALLED",
        }
    ]
    assert payload["area_ideal_states"] == {"CAREER": "今の理想状態。"}
    assert payload["note"] == "今週は時間が取れなかった"
    assert "answered_at" in payload
    assert "reflection_id" in payload


def test_post_reflections_idempotency_key_reuses_the_same_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_send = _install_fake_send(monkeypatch)
    client, user_id = _client_with_logged_in_user()
    _save_purpose(user_id)
    _save_area_plan(user_id, "CAREER", goal_bodies=["職務経歴書を書き上げる"])
    plan = area_plan_domain.get_area_plan(user_id, "CAREER")
    assert plan is not None
    goal_key = plan["goals"][0]["goal_key"]
    body = {"statuses": [{"goal_key": goal_key, "status": "ON_TRACK"}], "note": None}
    headers = {"Idempotency-Key": "retry-key-1"}

    first = client.post("/api/v1/reflections", json=body, headers=headers)
    second = client.post("/api/v1/reflections", json=body, headers=headers)

    assert first.json()["job_id"] == second.json()["job_id"]
    assert len(fake_send.calls) == 1  # 2回目はジョブを作らない


def test_post_reflections_is_not_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    """5.14「頻度: 制限しない。同じ日に何度でも記録できる」。"""
    _install_fake_send(monkeypatch)
    client, user_id = _client_with_logged_in_user()
    _save_purpose(user_id)
    _save_area_plan(user_id, "CAREER", goal_bodies=["職務経歴書を書き上げる"])
    plan = area_plan_domain.get_area_plan(user_id, "CAREER")
    assert plan is not None
    goal_key = plan["goals"][0]["goal_key"]
    body = {"statuses": [{"goal_key": goal_key, "status": "ON_TRACK"}], "note": None}

    for _ in range(35):  # 登録済みユーザーの生成系一般則(1時間30回)を上回る回数
        response = client.post("/api/v1/reflections", json=body)
        assert response.status_code == 202


# --- GET /reflections/{id} ---


def _stored_reflection_item(
    user_id: str, reflection_id: str, *, answered_at: str
) -> dict[str, Any]:
    return build_reflection_item(
        user_id=user_id,
        reflection_id=reflection_id,
        statuses=[
            ResolvedStatus(
                goal_key="g-1", area="CAREER", goal_body="職務経歴書を書き上げる", status="ON_TRACK"
            )
        ],
        note="今週は時間が取れなかった",
        ai_output={
            "looking_back": "前に進みました。",
            "insight": "小さく区切れると動けるようです。",
            "next_step": "来週は1日1回だけ開いてみるのはどうでしょう。",
            "safety_flag": False,
        },
        answered_at=answered_at,
        generated_at=answered_at,
    )


def test_get_reflection_returns_result_for_the_owner() -> None:
    client, user_id = _client_with_logged_in_user()
    reflection_id = uuid.uuid4().hex
    answered_at = now_iso()
    repository.put_item(_stored_reflection_item(user_id, reflection_id, answered_at=answered_at))

    response = client.get(f"/api/v1/reflections/{reflection_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["next_step"] == "来週は1日1回だけ開いてみるのはどうでしょう。"
    assert body["safety_flag"] is False
    assert body["answered_at"] == answered_at


def test_get_reflection_returns_403_for_another_owner() -> None:
    _, other_user_id = _client_with_logged_in_user()
    reflection_id = uuid.uuid4().hex
    repository.put_item(
        _stored_reflection_item(other_user_id, reflection_id, answered_at=now_iso())
    )
    client, _ = _client_with_logged_in_user()

    response = client.get(f"/api/v1/reflections/{reflection_id}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REFLECTION_FORBIDDEN"


def test_get_reflection_returns_403_when_it_does_not_exist() -> None:
    client, _ = _client_with_logged_in_user()

    response = client.get(f"/api/v1/reflections/{uuid.uuid4().hex}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REFLECTION_FORBIDDEN"
