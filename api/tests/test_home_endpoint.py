"""`GET /home`。09_API設計5.9、04_画面設計S-41。BatchGet 1回でありたい姿・4領域・
振り返り導線の可否・テーマ設定をまとめて返すことを確認する。
"""

import uuid

from fastapi.testclient import TestClient

from app.core.security import SESSION_COOKIE_NAME
from app.db import repository
from app.domain import area_plan as area_plan_domain
from app.domain import purpose as purpose_domain
from app.domain.session import create_session
from app.domain.user import build_profile_item, update_theme_preference
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


def _save_area_plan(user_id: str, area: str, *, goal_count: int = 1) -> None:
    area_plan_domain.save_area_plan(
        user_id=user_id,
        area=area,
        choices=[],
        conversation=[],
        selected_direction="DEEPEN",
        selected_label="今の場所で深める",
        original_ideal_state="今の理想状態。",
        ideal_state="今の理想状態。",
        goals=[
            area_plan_domain.GoalInput(body=f"目標{i}") for i in range(1, goal_count + 1)
        ],
    )


def test_returns_401_without_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.get("/api/v1/home")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_returns_null_purpose_and_empty_areas_before_anything_is_created() -> None:
    client, _ = _client_with_logged_in_user()

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    body = response.json()
    assert body["purpose"] is None
    assert body["areas"] == [
        {"area": "CAREER", "status": "EMPTY"},
        {"area": "FINANCIAL", "status": "EMPTY"},
        {"area": "PHYSICAL", "status": "EMPTY"},
        {"area": "SOCIAL", "status": "EMPTY"},
    ]
    assert body["reflection_available"] is False
    assert body["theme_preference"] == "AUTO"


def test_returns_purpose_and_created_areas_with_goal_counts() -> None:
    client, user_id = _client_with_logged_in_user()
    _save_purpose(user_id)
    _save_area_plan(user_id, "CAREER", goal_count=2)

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    body = response.json()
    assert body["purpose"] == {
        "statement": "まわりの人が安心して力を出せる存在でありたい。",
        "version": 1,
    }
    career = next(area for area in body["areas"] if area["area"] == "CAREER")
    assert career["status"] == "CREATED"
    assert career["ideal_state_summary"] == "今の理想状態。"
    assert career["goal_count"] == 2
    financial = next(area for area in body["areas"] if area["area"] == "FINANCIAL")
    assert financial == {"area": "FINANCIAL", "status": "EMPTY"}
    assert body["reflection_available"] is True


def test_reflection_unavailable_when_no_area_has_a_goal_yet() -> None:
    """4領域とも未作成なら、目標の合計も0のため振り返り導線は無効(screen-list.md S-41)。"""
    client, user_id = _client_with_logged_in_user()
    _save_purpose(user_id)

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    assert response.json()["reflection_available"] is False


def test_theme_preference_reflects_the_saved_profile_value() -> None:
    client, user_id = _client_with_logged_in_user()

    update_theme_preference(user_id, "DARK")

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    assert response.json()["theme_preference"] == "DARK"
