"""`GET /reflections/context`。09_API設計5.13、04_画面設計S-61。

目標0件でも空配列を返す(409にしない)ことと、複数領域にまたがる目標をまとめて返すことを確認する。
"""

import uuid

from fastapi.testclient import TestClient

from app.core.security import SESSION_COOKIE_NAME
from app.db import repository
from app.domain import area_plan as area_plan_domain
from app.domain import purpose as purpose_domain
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
