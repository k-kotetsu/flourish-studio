"""`POST /area-plans`。09_API設計5.11、08_データモデル4.2〜4.4の保存・バージョン管理を確認する。"""

import uuid
from typing import Any

from fastapi.testclient import TestClient

from app.core.security import SESSION_COOKIE_NAME
from app.db import repository
from app.db.keys import area_current_sk, history_sk, user_pk
from app.domain import purpose as purpose_domain
from app.domain.session import create_session
from app.domain.user import build_profile_item
from app.main import app

_VALID_CHOICES = [
    {"question_code": "Q1", "option_codes": ["CAREER_OUTLOOK"]},
    {"question_code": "Q2", "option_codes": ["CAREER_VALUE_GROWTH"]},
    {"question_code": "Q3", "option_codes": ["CAREER_POSITION_GROWTH"]},
]
_VALID_MESSAGES = [
    {"role": "AI", "body": "「今後のキャリアの見通し」を選ばれていました。"},
    {"role": "USER", "body": "前の職場で実感しました。"},
]


def _client_with_logged_in_user(*, with_purpose: bool = True) -> tuple[TestClient, str]:
    user_id = uuid.uuid4().hex
    repository.put_item(build_profile_item(user_id, guest_session_id=None))
    if with_purpose:
        purpose_domain.save_purpose(
            user_id=user_id,
            statement="まわりの人が安心して力を出せる存在でありたい。",
            original_statement="まわりの人が安心して力を出せる存在でありたい。",
            selected_direction="OTHERS",
            selected_label="まわりの人とともに",
            choices=[],
            conversation=[],
        )
    token, _ = create_session(user_id)
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client, user_id


def _request_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "area": "CAREER",
        "choices": _VALID_CHOICES,
        "messages": _VALID_MESSAGES,
        "selected_direction": "DEEPEN",
        "selected_label": "今の場所で深める",
        "original_ideal_state": "今の仕事の中で自分の強みが言葉になっている。",
        "ideal_state": (
            "今の仕事の中で自分の強みが言葉になっていて、次に何を任されたいかを自分から言えている。"
        ),
        "goals": [{"body": "職務経歴書を書き上げる", "sort_order": 1}],
    }
    body.update(overrides)
    return body


def test_returns_401_without_session_cookie() -> None:
    client = TestClient(app, base_url="https://testserver")

    response = client.post("/api/v1/area-plans", json=_request_body())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_returns_422_when_choices_are_missing_a_question() -> None:
    client, _ = _client_with_logged_in_user()

    response = client.post(
        "/api/v1/area-plans", json=_request_body(choices=_VALID_CHOICES[:2])
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CHOICES_INVALID"


def test_returns_409_when_no_purpose_is_confirmed_yet() -> None:
    client, _ = _client_with_logged_in_user(with_purpose=False)

    response = client.post("/api/v1/area-plans", json=_request_body())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PURPOSE_REQUIRED"


def test_returns_422_when_goals_are_empty() -> None:
    client, _ = _client_with_logged_in_user()

    response = client.post("/api/v1/area-plans", json=_request_body(goals=[]))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "GOALS_REQUIRED"


def test_returns_422_when_goals_exceed_3() -> None:
    client, _ = _client_with_logged_in_user()
    goals = [{"body": f"目標{i}", "sort_order": i} for i in range(1, 5)]

    response = client.post("/api/v1/area-plans", json=_request_body(goals=goals))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "GOALS_REQUIRED"


def test_creates_area_plan_and_assigns_goal_keys_from_list_order() -> None:
    client, user_id = _client_with_logged_in_user()
    # クライアントが送るsort_orderは意図的に位置と食い違わせる。サーバーは配列の位置から
    # 採番し直すため、レスポンス・保存内容とも1・2の連番になる(area_plan.py `_build_goals`)。
    goals = [
        {"body": "職務経歴書を書き上げる", "sort_order": 9},
        {"body": "月に1回、社外の人と話す", "sort_order": 1},
    ]

    response = client.post("/api/v1/area-plans", json=_request_body(goals=goals))

    assert response.status_code == 201
    body = response.json()
    assert body["version"] == 1
    assert body["area"] == "CAREER"
    assert body["selected_direction"] == "DEEPEN"
    assert len(body["goals"]) == 2
    assert body["goals"][0]["body"] == "職務経歴書を書き上げる"
    assert body["goals"][0]["sort_order"] == 1
    assert body["goals"][1]["body"] == "月に1回、社外の人と話す"
    assert body["goals"][1]["sort_order"] == 2
    assert body["goals"][0]["goal_key"] != body["goals"][1]["goal_key"]

    item = repository.get_item(user_pk(user_id), area_current_sk("CAREER"))
    assert item is not None
    assert item["entity"] == "AREA_PLAN"
    assert item["purpose_version"] == 1
    assert len(item["choices"]) == 3
    assert item["conversation"] == [
        {"seq": 1, "role": "AI", "body": "「今後のキャリアの見通し」を選ばれていました。"},
        {"seq": 2, "role": "USER", "body": "前の職場で実感しました。"},
    ]


def test_second_create_makes_a_new_version_and_moves_old_to_history() -> None:
    client, user_id = _client_with_logged_in_user()
    client.post("/api/v1/area-plans", json=_request_body(ideal_state="最初の理想状態"))

    response = client.post(
        "/api/v1/area-plans", json=_request_body(ideal_state="作り直した理想状態")
    )

    assert response.status_code == 201
    assert response.json()["version"] == 2

    current = repository.get_item(user_pk(user_id), area_current_sk("CAREER"))
    assert current is not None
    assert current["ideal_state"] == "作り直した理想状態"

    history = repository.get_item(user_pk(user_id), history_sk("AREA#CAREER", 1))
    assert history is not None
    assert history["ideal_state"] == "最初の理想状態"
