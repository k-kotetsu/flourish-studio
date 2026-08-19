"""P7-8: 通しの結合テスト。03_ユーザーフロー1章の全体フロー
（S-01 → S-16 → 登録 → ありたい姿 → 領域 → ホーム → 振り返り）を、実際のFastAPIルーター
（`app.main.app`）に対して1つの`TestClient`でCookieを引き継ぎながら一連のHTTPリクエストとして
再現する。

S-01自体は`/app`の外にある静的サイト（`web/`側に実装なし、tools/generate_site.py）のため
このテストの対象外。それ以外の各画面はすべて対応するエンドポイントを実HTTP経由で呼ぶ
（`test_auth_flow.py`の「1つのclientでCookieを引き継ぐ」手法をP1〜P6の全エンドポイントに
拡張したもの）。

実際にAWSへ接続する箇所（Bedrock・Cognito・SQS）は、各既存テストと同じ手法でフェイクに
差し替える：
- Bedrock（ジョブ生成系）：`app.ai.runner.get_client`をフェイクにし、SQS送信を横取りして
  ワーカー(`app.worker.handler.handler`)を直接呼ぶ（test_worker_handler.pyと同じ）
- Bedrock（SSE対話）：各対話モジュールの`get_client`／`check_safety`をフェイクにする
  （test_ai_purpose_dialogue_endpoint.pyと同じ）
- Cognito：`app.domain.cognito.sign_up_and_confirm`をフェイクにする
  （test_auth_register_endpoint.pyと同じ）
"""

import json
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.security import GUEST_COOKIE_NAME, SESSION_COOKIE_NAME
from app.domain import cognito, questions
from app.main import app
from app.worker.handler import handler

_QUESTION_SET = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)


# ---------------------------------------------------------------------------
# Bedrock(ジョブ生成系)をフェイクにする。test_worker_handler.pyと同じ手法。
# ---------------------------------------------------------------------------


def _fake_message(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=500, output_tokens=200, cache_read_input_tokens=0),
    )


class _FakeMessages:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)

    def create(self, **kwargs: Any) -> Any:
        return self._responses.pop(0)


class _FakeRunnerClient:
    def __init__(self, texts: list[str]) -> None:
        self.messages = _FakeMessages([_fake_message(text) for text in texts])


class _SendJobCapture:
    """`send_job_message`を横取りし、実際のSQS送信を行わずペイロードだけ記録する。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, job_id: str, kind: str, payload: dict[str, Any] | None = None) -> None:
        self.calls.append({"job_id": job_id, "kind": kind, "payload": payload})


def _run_worker(job_id: str, kind: str, payload: dict[str, Any] | None) -> None:
    body: dict[str, Any] = {"job_id": job_id, "kind": kind}
    if payload is not None:
        body["payload"] = payload
    handler({"Records": [{"body": json.dumps(body)}]}, object())


def _create_job_and_advance(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    *,
    send_module: str,
    result_texts: list[str],
    url: str,
    json_body: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """ジョブ登録エンドポイントを呼び、SQS送信を横取りしてワーカーへ直接渡し、
    `GET /jobs/{id}`が返す最終状態を返す。"""
    capture = _SendJobCapture()
    monkeypatch.setattr(send_module, capture)
    monkeypatch.setattr("app.ai.runner.get_client", lambda: _FakeRunnerClient(result_texts))

    response = client.post(url, json=json_body, headers=headers or {})
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]

    assert len(capture.calls) == 1
    call = capture.calls[0]
    _run_worker(call["job_id"], call["kind"], call["payload"])

    job_response: dict[str, Any] = client.get(f"/api/v1/jobs/{job_id}").json()
    return job_response


# ---------------------------------------------------------------------------
# Bedrock(SSE対話)をフェイクにする。test_ai_purpose_dialogue_endpoint.pyと同じ手法。
# ---------------------------------------------------------------------------


class _FakeMessageStream:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    def __enter__(self) -> "_FakeMessageStream":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    @property
    def text_stream(self) -> Any:
        return iter(self._chunks)

    def get_final_message(self) -> SimpleNamespace:
        return SimpleNamespace(
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=50, output_tokens=20, cache_read_input_tokens=0),
        )


def _install_fake_dialogue_client(
    monkeypatch: pytest.MonkeyPatch, module: str, chunks: list[str]
) -> None:
    fake_stream = _FakeMessageStream(chunks)
    fake_client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kwargs: fake_stream))
    monkeypatch.setattr(f"{module}.get_client", lambda: fake_client)
    monkeypatch.setattr(
        f"{module}.check_safety",
        lambda *args, **kwargs: SimpleNamespace(flagged=False, category="NONE"),
    )


# ---------------------------------------------------------------------------
# 各AI出力(JSON)の組み立て。
# ---------------------------------------------------------------------------


def _valid_questions_json(areas: list[str]) -> str:
    questions_out = []
    for area in areas:
        questions_out.append({"area": area, "slot": "SATISFIED", "text": "いまどんな状況ですか。"})
        questions_out.append(
            {"area": area, "slot": "CONCERN", "text": "これからどうしていきたいですか。"}
        )
    return json.dumps({"questions": questions_out})


def _valid_report_json(*, safety_flag: bool = False) -> str:
    areas_out = [
        {
            "area": area,
            "satisfied_text": "満たされている点があります。",
            "concern_text": "気になる点もあります。",
            "advice_text": "少しずつ試してみるのはどうでしょう。",
        }
        for area in questions.AREAS
    ]
    return json.dumps(
        {
            "nickname": "全速前進、燃料計は未確認",
            "areas": areas_out,
            "articulation_stage": "SPROUT",
            "articulation_reason": "具体的な状況が書かれているため。",
            "safety_flag": safety_flag,
        }
    )


def _valid_purpose_proposals_json() -> str:
    return json.dumps(
        {
            "proposals": [
                {
                    "direction": "SELF",
                    "label": "自分の納得を軸に",
                    "statement": "自分で選んだと言えることを積み重ねて生きていきたい。",
                },
                {
                    "direction": "OTHERS",
                    "label": "まわりの人とともに",
                    "statement": "まわりの人が安心して力を出せる存在でありたい。",
                },
                {
                    "direction": "SOCIETY",
                    "label": "もっと広く",
                    "statement": "人の可能性が広がる場をつくっていきたい。",
                },
            ],
            "safety_flag": False,
        }
    )


def _valid_area_proposals_json() -> str:
    return json.dumps(
        {
            "proposals": [
                {
                    "direction": "DEEPEN",
                    "label": "今の場所で深める",
                    "ideal_state": "今の仕事の中で自分の強みが言葉になっている。",
                },
                {
                    "direction": "CHANGE",
                    "label": "やり方を変える",
                    "ideal_state": "働き方や役割を組み替えて、自分に合う進め方が見つかっている。",
                },
                {
                    "direction": "EXPAND",
                    "label": "外に出る",
                    "ideal_state": "社外の人と接点があり、会社の外でも通用する選択肢を持てている。",
                },
            ],
            "safety_flag": False,
        }
    )


def _valid_reflection_summary_json() -> str:
    return json.dumps(
        {
            "looking_back": "Careerは前に進んでいるようです。",
            "insight": "動けた目標には、その日のうちに終わる大きさがありました。",
            "next_step": "来週は、1日1回アプリを開くだけにしてみるのはどうでしょう。",
            "safety_flag": False,
        }
    )


# ---------------------------------------------------------------------------
# フローの各段で使う入力の組み立て。
# ---------------------------------------------------------------------------


def _full_scale_answers() -> list[dict[str, Any]]:
    """S-12：選択式24問(4領域 x (満足度5項目 + コミット度1問))。"""
    answers = []
    for area in questions.AREAS:
        item_codes = [item.code for item in _QUESTION_SET.items if item.area == area]
        for code, score in zip(item_codes, [4, 3, 2, 1, 0], strict=True):
            answers.append(
                {"area": area, "question_kind": "SATISFACTION", "item_code": code, "score": score}
            )
        answers.append({"area": area, "question_kind": "COMMITMENT", "score": 2})
    return answers


def _free_text_answers_from_questions(
    scale_answers: list[dict[str, Any]], generated_questions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """S-14：AIが生成した8件の問いに、ユーザーが自由記述で答える(1件はスキップして送る)。"""
    question_by_key = {(q["area"], q["slot"]): q for q in generated_questions}
    answers = []
    for (area, slot), q in question_by_key.items():
        skip = area == "SOCIAL" and slot == "CONCERN"  # 自由記述は空欄でも成立することの確認
        answers.append(
            {
                "area": area,
                "slot": slot,
                "target_item_code": q["target_item_code"],
                "generated_question": q["text"],
                "body": None if skip else "今の会社で任される範囲が広がってきた",
            }
        )
    return answers


_PURPOSE_CHOICES = [
    {"question_code": "Q1", "option_codes": ["GROWTH", "FREEDOM"]},
    {"question_code": "Q2", "option_codes": ["SELF_DETERMINED"]},
    {"question_code": "Q3", "option_codes": ["HAVING_OPTIONS"]},
]


def _area_choices(area: str) -> list[dict[str, Any]]:
    item_code = next(item.code for item in _QUESTION_SET.items if item.area == area)
    values_code, position_code = {
        "CAREER": ("CAREER_VALUE_GROWTH", "CAREER_POSITION_GROWTH"),
        "FINANCIAL": ("FINANCIAL_VALUE_INCOME_GROWTH", "FINANCIAL_POSITION_OPTIONS"),
        "PHYSICAL": ("PHYSICAL_VALUE_DAILY_ENERGY", "PHYSICAL_POSITION_CONFIDENCE"),
        "SOCIAL": ("SOCIAL_VALUE_ENJOYMENT", "SOCIAL_POSITION_MUTUAL_SUPPORT"),
    }[area]
    return [
        {"question_code": "Q1", "option_codes": [item_code]},
        {"question_code": "Q2", "option_codes": [values_code]},
        {"question_code": "Q3", "option_codes": [position_code]},
    ]


def _run_dialogue_turns(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    module: str,
    url: str,
    total_turns: int,
    extra_body: dict[str, Any],
) -> list[dict[str, str]]:
    """S-32/S-52のAI対話をtotal_turns往復ぶん進め、最終的な対話全文を返す。"""
    messages: list[dict[str, str]] = []
    for turn in range(1, total_turns + 1):
        _install_fake_dialogue_client(monkeypatch, module, [f"問い{turn}"])
        response = client.post(url, json={**extra_body, "messages": messages})
        assert response.status_code == 200, response.text
        assert f'"turn": {turn}' in response.text
        messages = [
            *messages,
            {"role": "AI", "body": f"問い{turn}"},
            {"role": "USER", "body": f"回答{turn}"},
        ]
    return messages


# ===========================================================================
# 通しの結合テスト本体
# ===========================================================================


def test_full_journey_from_assessment_through_first_reflection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """03_ユーザーフロー1章の全経路：
    現在地レポート開始→4領域の質問→結果(S-16)→登録(S-21)→ありたい姿(S-31〜S-37)→
    最初の領域を選ぶ→理想状態と目標(S-51〜S-56)→ホーム(S-41)→Weekly Reflection(S-61〜S-63)。
    S-01(公開サイト)は`web/`外の静的サイトのためAPI結合テストの対象外。
    """
    client = TestClient(app, base_url="https://testserver")

    # --- Step 1: 現在地レポート開始(ゲストセッション発行) ---
    guest_response = client.post("/api/v1/guest-sessions")
    assert guest_response.status_code == 201
    assert GUEST_COOKIE_NAME in client.cookies

    # --- Step 2: 4領域の質問(S-12選択式24問 → S-13 AI生成 → S-14自由記述8問) ---
    scale_answers = _full_scale_answers()
    questions_job = _create_job_and_advance(
        monkeypatch,
        client,
        send_module="app.api.v1.ai_assessment_questions.send_job_message",
        result_texts=[_valid_questions_json(list(questions.AREAS))],
        url="/api/v1/ai/assessment-questions",
        json_body={
            "scale_answers": scale_answers,
            "question_set_version": questions.CURRENT_QUESTION_SET_VERSION,
        },
    )
    assert questions_job["status"] == "SUCCEEDED"
    assert len(questions_job["result"]["questions"]) == 8

    free_text_answers = _free_text_answers_from_questions(
        scale_answers, questions_job["result"]["questions"]
    )

    # --- Step 3: 現在地レポート結果(S-15生成→S-16表示。全文を未登録のまま表示) ---
    report_job = _create_job_and_advance(
        monkeypatch,
        client,
        send_module="app.api.v1.assessments.send_job_message",
        result_texts=[_valid_report_json()],
        url="/api/v1/assessments",
        json_body={
            "scale_answers": scale_answers,
            "free_text_answers": free_text_answers,
            "question_set_version": questions.CURRENT_QUESTION_SET_VERSION,
        },
    )
    assert report_job["status"] == "SUCCEEDED"
    assessment_id = report_job["result"]["assessment_id"]

    report_response = client.get(f"/api/v1/assessments/{assessment_id}")
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["nickname"] == "全速前進、燃料計は未確認"
    assert report["safety_flag"] is False
    assert len(report["areas"]) == 4

    # --- Step 4: アカウント登録(S-21。ゲストセッションをアカウントへ紐付け) ---
    user_id = uuid.uuid4().hex
    monkeypatch.setattr(
        cognito, "sign_up_and_confirm", lambda *, email, password: user_id
    )
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": f"{user_id}@example.com", "password": "correct-horse-battery-9"},
    )
    assert register_response.status_code == 201
    assert SESSION_COOKIE_NAME in client.cookies
    assert GUEST_COOKIE_NAME not in client.cookies

    # 登録後もレポートは(アカウントへ移った状態で)そのまま読める
    migrated_report = client.get(f"/api/v1/assessments/{assessment_id}")
    assert migrated_report.status_code == 200
    assert migrated_report.json()["nickname"] == report["nickname"]

    # --- Step 5: ありたい姿の作成(S-31選択式 → S-32 AI対話3往復 → S-33 3案 → S-35確定) ---
    purpose_messages = _run_dialogue_turns(
        client,
        monkeypatch,
        module="app.ai.prompts.purpose_dialogue",
        url="/api/v1/ai/purpose-dialogue",
        total_turns=3,
        extra_body={"choices": _PURPOSE_CHOICES},
    )

    proposals_job = _create_job_and_advance(
        monkeypatch,
        client,
        send_module="app.api.v1.ai_purpose_proposals.send_job_message",
        result_texts=[_valid_purpose_proposals_json()],
        url="/api/v1/ai/purpose-proposals",
        json_body={"choices": _PURPOSE_CHOICES, "messages": purpose_messages},
    )
    assert proposals_job["status"] == "SUCCEEDED"
    proposals = proposals_job["result"]["proposals"]
    assert len(proposals) == 3
    selected_purpose = next(p for p in proposals if p["direction"] == "OTHERS")

    edited_statement = "まわりの人が安心して力を出せる、そんな存在でありたい。"
    create_purpose_response = client.post(
        "/api/v1/purposes",
        json={
            "choices": _PURPOSE_CHOICES,
            "messages": purpose_messages,
            "selected_direction": selected_purpose["direction"],
            "selected_label": selected_purpose["label"],
            "original_statement": selected_purpose["statement"],
            "statement": edited_statement,
        },
    )
    assert create_purpose_response.status_code == 201
    assert create_purpose_response.json()["statement"] == edited_statement

    current_purpose = client.get("/api/v1/purposes/current")
    assert current_purpose.status_code == 200
    assert current_purpose.json()["statement"] == edited_statement

    # --- Step 6/7: 最初の領域を選ぶ(CAREER) → 理想状態と目標を作成 ---
    # (S-51選択式 → S-52 AI対話2往復 → S-53 3案 → S-55編集 → S-56確定)
    area = "CAREER"
    area_choices = _area_choices(area)
    area_messages = _run_dialogue_turns(
        client,
        monkeypatch,
        module="app.ai.prompts.area_dialogue",
        url="/api/v1/ai/area-dialogue",
        total_turns=2,
        extra_body={"area": area, "choices": area_choices},
    )

    area_proposals_job = _create_job_and_advance(
        monkeypatch,
        client,
        send_module="app.api.v1.ai_area_proposals.send_job_message",
        result_texts=[_valid_area_proposals_json()],
        url="/api/v1/ai/area-proposals",
        json_body={"area": area, "choices": area_choices, "messages": area_messages},
    )
    assert area_proposals_job["status"] == "SUCCEEDED"
    area_proposals = area_proposals_job["result"]["proposals"]
    selected_area_proposal = next(p for p in area_proposals if p["direction"] == "DEEPEN")

    # S-56:「AIにヒントをもらう」(同期、任意操作)も一度通しておく
    goal_hints_json = json.dumps(
        {"hints": ["職務経歴書を書き上げる", "月1回1on1を設定する", "資格を1つ取る"]}
    )
    monkeypatch.setattr(
        "app.ai.runner.get_client", lambda: _FakeRunnerClient([goal_hints_json])
    )
    goal_hints_response = client.post(
        "/api/v1/ai/goal-hints",
        json={
            "area": area,
            "ideal_state": selected_area_proposal["ideal_state"],
            "existing_goals": [],
        },
    )
    assert goal_hints_response.status_code == 200
    assert len(goal_hints_response.json()["hints"]) == 3

    edited_ideal_state = "今の仕事の中で、自分の強みがはっきり言葉になっている。"
    create_area_plan_response = client.post(
        "/api/v1/area-plans",
        json={
            "area": area,
            "choices": area_choices,
            "messages": area_messages,
            "selected_direction": selected_area_proposal["direction"],
            "selected_label": selected_area_proposal["label"],
            "original_ideal_state": selected_area_proposal["ideal_state"],
            "ideal_state": edited_ideal_state,
            "goals": [
                {"body": "職務経歴書を書き上げる", "sort_order": 0},
                {"body": "月1回1on1を設定する", "sort_order": 1},
            ],
        },
    )
    assert create_area_plan_response.status_code == 201
    created_area_plan = create_area_plan_response.json()
    assert created_area_plan["ideal_state"] == edited_ideal_state
    assert len(created_area_plan["goals"]) == 2

    # --- Step 8: ホーム(S-41) ---
    home_response = client.get("/api/v1/home")
    assert home_response.status_code == 200
    home = home_response.json()
    assert home["purpose"]["statement"] == edited_statement
    career_home_entry = next(a for a in home["areas"] if a["area"] == "CAREER")
    assert career_home_entry["status"] == "CREATED"
    assert career_home_entry["goal_count"] == 2
    # 残り3領域は「あとで」でスキップしたままなので未作成
    assert all(
        a["status"] == "EMPTY" for a in home["areas"] if a["area"] != "CAREER"
    )
    # 目標が1つ以上あるのでWeekly Reflection導線が有効になる(P5-3)
    assert home["reflection_available"] is True

    # --- Step 10: Weekly Reflection(S-61現行の目標 → S-62回答 → S-63結果) ---
    context_response = client.get("/api/v1/reflections/context")
    assert context_response.status_code == 200
    goals = context_response.json()["goals"]
    assert len(goals) == 2

    reflection_job = _create_job_and_advance(
        monkeypatch,
        client,
        send_module="app.api.v1.reflections.send_job_message",
        result_texts=[_valid_reflection_summary_json()],
        url="/api/v1/reflections",
        json_body={
            "statuses": [
                {"goal_key": goals[0]["goal_key"], "status": "ON_TRACK"},
                {"goal_key": goals[1]["goal_key"], "status": "STALLED"},
            ],
            "note": "今週は残業が続いて、時間が取れなかった",
        },
    )
    assert reflection_job["status"] == "SUCCEEDED"
    reflection_id = reflection_job["result"]["reflection_id"]

    reflection_response = client.get(f"/api/v1/reflections/{reflection_id}")
    assert reflection_response.status_code == 200
    reflection = reflection_response.json()
    assert reflection["next_step"] == (
        "来週は、1日1回アプリを開くだけにしてみるのはどうでしょう。"
    )
    assert reflection["safety_flag"] is False


# ===========================================================================
# 離脱・再試行・失敗の分岐
# ===========================================================================


def _register_fresh_user(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> str:
    user_id = uuid.uuid4().hex
    monkeypatch.setattr(cognito, "sign_up_and_confirm", lambda *, email, password: user_id)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": f"{user_id}@example.com", "password": "correct-horse-battery-9"},
    )
    assert response.status_code == 201
    return user_id


def test_leaving_before_confirming_purpose_saves_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """離脱：3案まで生成しても`POST /purposes`で確定しなければ何も保存されない
    (`03_ユーザーフロー`2.1「確定した成果物だけを保存する」)。
    """
    client = TestClient(app, base_url="https://testserver")
    _register_fresh_user(client, monkeypatch)

    purpose_messages = _run_dialogue_turns(
        client,
        monkeypatch,
        module="app.ai.prompts.purpose_dialogue",
        url="/api/v1/ai/purpose-dialogue",
        total_turns=3,
        extra_body={"choices": _PURPOSE_CHOICES},
    )
    proposals_job = _create_job_and_advance(
        monkeypatch,
        client,
        send_module="app.api.v1.ai_purpose_proposals.send_job_message",
        result_texts=[_valid_purpose_proposals_json()],
        url="/api/v1/ai/purpose-proposals",
        json_body={"choices": _PURPOSE_CHOICES, "messages": purpose_messages},
    )
    assert proposals_job["status"] == "SUCCEEDED"

    # ここで離脱。次回アクセス時、確定済みのありたい姿は存在しない。
    response = client.get("/api/v1/purposes/current")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PURPOSE_NOT_FOUND"


def test_assessment_report_failure_can_be_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """失敗・再試行：AI出力がスキーマ違反のままだとジョブはFAILEDになり、何も保存されない
    (規則5「自動リトライしない」)。ユーザーが同じ入力で再試行すると、新しいジョブとして
    成功できる。
    """
    client = TestClient(app, base_url="https://testserver")
    client.post("/api/v1/guest-sessions")

    scale_answers = _full_scale_answers()
    questions_job = _create_job_and_advance(
        monkeypatch,
        client,
        send_module="app.api.v1.ai_assessment_questions.send_job_message",
        result_texts=[_valid_questions_json(list(questions.AREAS))],
        url="/api/v1/ai/assessment-questions",
        json_body={
            "scale_answers": scale_answers,
            "question_set_version": questions.CURRENT_QUESTION_SET_VERSION,
        },
    )
    free_text_answers = _free_text_answers_from_questions(
        scale_answers, questions_job["result"]["questions"]
    )
    body = {
        "scale_answers": scale_answers,
        "free_text_answers": free_text_answers,
        "question_set_version": questions.CURRENT_QUESTION_SET_VERSION,
    }

    invalid_text = json.dumps({"nickname": "x"})  # 必須フィールド欠落。再生成しても直らない
    failed_job = _create_job_and_advance(
        monkeypatch,
        client,
        send_module="app.api.v1.assessments.send_job_message",
        result_texts=[invalid_text, invalid_text],  # サーバ内の1回再生成分も含めて2回とも不正
        url="/api/v1/assessments",
        json_body=body,
    )
    assert failed_job["status"] == "FAILED"
    assert failed_job["error"]["code"] == "AI_OUTPUT_INVALID"

    # ユーザーの入力(scale_answers/free_text_answers)はクライアント側に残ったまま、
    # 「再試行」ボタンで同じ内容を送り直す。今度はAIの出力が正しく成功する。
    retried_job = _create_job_and_advance(
        monkeypatch,
        client,
        send_module="app.api.v1.assessments.send_job_message",
        result_texts=[_valid_report_json()],
        url="/api/v1/assessments",
        json_body=body,
    )
    assert retried_job["status"] == "SUCCEEDED"
    assessment_id = retried_job["result"]["assessment_id"]
    assert client.get(f"/api/v1/assessments/{assessment_id}").status_code == 200


def test_home_reachable_and_reflection_blocked_when_areas_are_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """スキップ経路：「あとで」で領域選択を飛ばしてもホームには到達できる(`03_ユーザーフロー`
    Step 6の分岐)。目標が1つも無いのでWeekly Reflectionには進めない
    (P5-3「目標0個で無効」を`POST /reflections`側でも確認)。
    """
    client = TestClient(app, base_url="https://testserver")
    _register_fresh_user(client, monkeypatch)

    purpose_messages = _run_dialogue_turns(
        client,
        monkeypatch,
        module="app.ai.prompts.purpose_dialogue",
        url="/api/v1/ai/purpose-dialogue",
        total_turns=3,
        extra_body={"choices": _PURPOSE_CHOICES},
    )
    proposals_job = _create_job_and_advance(
        monkeypatch,
        client,
        send_module="app.api.v1.ai_purpose_proposals.send_job_message",
        result_texts=[_valid_purpose_proposals_json()],
        url="/api/v1/ai/purpose-proposals",
        json_body={"choices": _PURPOSE_CHOICES, "messages": purpose_messages},
    )
    selected = proposals_job["result"]["proposals"][0]
    client.post(
        "/api/v1/purposes",
        json={
            "choices": _PURPOSE_CHOICES,
            "messages": purpose_messages,
            "selected_direction": selected["direction"],
            "selected_label": selected["label"],
            "original_statement": selected["statement"],
            "statement": selected["statement"],
        },
    )

    # 「あとで」を選び、領域を1つも作らずホームへ。
    home_response = client.get("/api/v1/home")
    assert home_response.status_code == 200
    home = home_response.json()
    assert all(a["status"] == "EMPTY" for a in home["areas"])
    assert home["reflection_available"] is False

    reflection_context = client.get("/api/v1/reflections/context")
    assert reflection_context.status_code == 200
    assert reflection_context.json()["goals"] == []

    reflection_attempt = client.post("/api/v1/reflections", json={"statuses": [], "note": None})
    assert reflection_attempt.status_code == 409
    assert reflection_attempt.json()["error"]["code"] == "NO_GOALS"


def test_area_dialogue_requires_a_confirmed_purpose(monkeypatch: pytest.MonkeyPatch) -> None:
    """失敗の分岐：ありたい姿が確定する前にS-52(領域のAI対話)へ直接到達しても進めない。"""
    client = TestClient(app, base_url="https://testserver")
    _register_fresh_user(client, monkeypatch)

    _install_fake_dialogue_client(monkeypatch, "app.ai.prompts.area_dialogue", ["問い1"])
    response = client.post(
        "/api/v1/ai/area-dialogue",
        json={"area": "CAREER", "choices": _area_choices("CAREER"), "messages": []},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PURPOSE_REQUIRED"
