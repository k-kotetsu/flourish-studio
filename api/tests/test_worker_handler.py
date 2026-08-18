import dataclasses
import json
import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.ai.prompts import assessment_questions
from app.db import repository
from app.db.keys import assessment_sk, reflection_sk, user_pk
from app.domain import job as job_domain
from app.domain import questions
from app.domain.area_choices import ChoiceAnswer as AreaChoiceAnswer
from app.domain.assessment_precompute import FreeTextAnswer, ScaleAnswer, pick_free_text_targets
from app.domain.purpose_choices import ChoiceAnswer
from app.worker.handler import handler

_QUESTION_SET = questions.get_question_set(questions.CURRENT_QUESTION_SET_VERSION)


def _uid() -> str:
    return uuid.uuid4().hex


def test_handler_returns_ok_for_empty_event() -> None:
    assert handler({}, object()) == {"status": "ok"}


def test_handler_processes_a_dummy_job_to_succeeded() -> None:
    # ASSESSMENT_QUESTIONS・ASSESSMENT_REPORT・PURPOSE_PROPOSALS・AREA_PROPOSALS・
    # REFLECTION_SUMMARYはP2-5/P2-8/P3-7/P4-4/P5-2で実処理に分岐したため、ここでは
    # 未実装のままダミー処理(雛形段階)が働くkindを使う。GOAL_HINTSは同期呼び出し
    # (P4-6、09_API設計5.10)でありワーカーには来ないが、その分このテストのダミー役に使える。
    owner = f"USER#{_uid()}"
    job_id, item = job_domain.create_job(owner, "GOAL_HINTS")
    assert item["status"] == "QUEUED"

    event = {"Records": [{"body": json.dumps({"job_id": job_id, "kind": "GOAL_HINTS"})}]}
    result = handler(event, object())

    assert result == {"status": "ok"}
    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "SUCCEEDED"
    assert updated["result"] == {"echo": "GOAL_HINTS"}


def test_handler_processes_multiple_records() -> None:
    # ASSESSMENT_QUESTIONS・ASSESSMENT_REPORT・PURPOSE_PROPOSALS・AREA_PROPOSALS・
    # REFLECTION_SUMMARYはP2-5/P2-8/P3-7/P4-4/P5-2で実処理に分岐したため、ここでは
    # 未実装のままダミー処理(雛形段階)が働くkindを使う。
    owner = f"USER#{_uid()}"
    job_id_a, _ = job_domain.create_job(owner, "GOAL_HINTS")
    job_id_b, _ = job_domain.create_job(owner, "SOME_OTHER_UNIMPLEMENTED_KIND")
    event = {
        "Records": [
            {"body": json.dumps({"job_id": job_id_a, "kind": "GOAL_HINTS"})},
            {"body": json.dumps({"job_id": job_id_b, "kind": "SOME_OTHER_UNIMPLEMENTED_KIND"})},
        ],
    }

    handler(event, object())

    updated_a = job_domain.get_job(job_id_a)
    updated_b = job_domain.get_job(job_id_b)
    assert updated_a is not None
    assert updated_b is not None
    assert updated_a["status"] == "SUCCEEDED"
    assert updated_b["status"] == "SUCCEEDED"


QuestionTargets = list[assessment_questions.QuestionTarget]


def _assessment_questions_payload() -> tuple[dict[str, Any], QuestionTargets]:
    scale_answers = []
    for area in questions.AREAS:
        item_codes = [item.code for item in _QUESTION_SET.items if item.area == area]
        for code, score in zip(item_codes, [4, 3, 2, 1, 0], strict=True):
            scale_answers.append(
                ScaleAnswer(
                    area=area, question_kind=questions.SATISFACTION, item_code=code, score=score
                )
            )
        scale_answers.append(ScaleAnswer(area=area, question_kind=questions.COMMITMENT, score=2))
    targets = assessment_questions.build_targets(scale_answers, _QUESTION_SET)
    payload = {
        "question_set_version": _QUESTION_SET.version,
        "targets": [dataclasses.asdict(target) for target in targets],
    }
    return payload, targets


def _fake_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=500, output_tokens=200, cache_read_input_tokens=0),
    )


def _valid_questions_json(targets: list[assessment_questions.QuestionTarget]) -> str:
    # AIの出力は`area`/`slot`/`text`のみ(`target_item_code`は含まない。P2-13参照)。
    questions_out = []
    for target in targets:
        questions_out.append(
            {
                "area": target.area,
                "slot": "SATISFIED",
                "text": "いまどんな状況ですか。",
            }
        )
        questions_out.append(
            {
                "area": target.area,
                "slot": "CONCERN",
                "text": "これからどうしていきたいですか。",
            }
        )
    return json.dumps({"questions": questions_out})


class _FakeMessages:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)

    def create(self, **kwargs: Any) -> Any:
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses: list[Any]) -> None:
        self.messages = _FakeMessages(responses)


def _assessment_questions_event(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {"job_id": job_id, "kind": "ASSESSMENT_QUESTIONS", "payload": payload}
    return {"Records": [{"body": json.dumps(body)}]}


def test_handler_generates_assessment_questions_to_succeeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """完了条件「8件の問いが生成され、検証を通る」(P2-5)。"""
    payload, targets = _assessment_questions_payload()
    fake_client = _FakeClient([_fake_response(_valid_questions_json(targets))])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"GUEST#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "ASSESSMENT_QUESTIONS")

    handler(_assessment_questions_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "SUCCEEDED"
    assert len(updated["result"]["questions"]) == 8
    # target_item_codeはAIの出力に含まれず、コード側が(area, slot)から付与する(P2-13)。
    expected_codes = {(t.area, "SATISFIED"): t.satisfied_item_code for t in targets} | {
        (t.area, "CONCERN"): t.concern_item_code for t in targets
    }
    for question in updated["result"]["questions"]:
        key = (question["area"], question["slot"])
        assert question["target_item_code"] == expected_codes[key]


def test_handler_fails_assessment_questions_job_after_schema_violation_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload, _targets = _assessment_questions_payload()
    invalid_text = json.dumps({"questions": []})  # 件数不足。再生成しても直らない
    fake_client = _FakeClient([_fake_response(invalid_text), _fake_response(invalid_text)])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"GUEST#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "ASSESSMENT_QUESTIONS")

    handler(_assessment_questions_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "FAILED"
    assert updated["error"]["code"] == "AI_OUTPUT_INVALID"
    assert updated["error"]["retryable"] is True


def _assessment_report_payload() -> dict[str, Any]:
    scale_answers = []
    for area in questions.AREAS:
        item_codes = [item.code for item in _QUESTION_SET.items if item.area == area]
        for code, score in zip(item_codes, [4, 3, 2, 1, 0], strict=True):
            scale_answers.append(
                ScaleAnswer(
                    area=area, question_kind=questions.SATISFACTION, item_code=code, score=score
                )
            )
        scale_answers.append(ScaleAnswer(area=area, question_kind=questions.COMMITMENT, score=2))

    free_text_answers: list[FreeTextAnswer] = []
    for target in pick_free_text_targets(scale_answers, _QUESTION_SET):
        free_text_answers.append(
            FreeTextAnswer(
                area=target.area,
                slot="SATISFIED",
                target_item_code=target.satisfied_item_code,
                generated_question="いまどんな状況で、なぜそう感じているのか教えてください。",
                body="今の会社で任される範囲が広がってきた",
            )
        )
        free_text_answers.append(
            FreeTextAnswer(
                area=target.area,
                slot="CONCERN",
                target_item_code=target.concern_item_code,
                generated_question="これからどうしていきたいですか。",
                body=None,
            )
        )

    return {
        "assessment_id": _uid(),
        "question_set_version": _QUESTION_SET.version,
        "scale_answers": [dataclasses.asdict(answer) for answer in scale_answers],
        "free_text_answers": [dataclasses.asdict(answer) for answer in free_text_answers],
        "started_at": "2026-08-15T00:00:00Z",
    }


def _valid_report_json() -> str:
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
            "safety_flag": False,
        }
    )


def _assessment_report_event(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {"job_id": job_id, "kind": "ASSESSMENT_REPORT", "payload": payload}
    return {"Records": [{"body": json.dumps(body)}]}


def test_handler_generates_assessment_report_to_succeeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """完了条件「検証をすべて通る。成功時のみ1アイテム保存」(P2-8)。"""
    payload = _assessment_report_payload()
    fake_client = _FakeClient([_fake_response(_valid_report_json())])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"GUEST#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "ASSESSMENT_REPORT")

    handler(_assessment_report_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "SUCCEEDED"
    assessment_id = payload["assessment_id"]
    assert updated["result"] == {"assessment_id": assessment_id}

    item = repository.get_item(owner, assessment_sk(assessment_id))
    assert item is not None
    assert item["result"]["nickname"] == "全速前進、燃料計は未確認"
    assert item["result"]["commitment_score"] == 8  # COMMITMENT各領域2点 x 4領域
    assert item["result"]["commitment_stage"] == "SEEDLING"  # 8〜11(4.1の閾値表)
    assert item["result"]["articulation_stage"] == "SPROUT"
    assert len(item["result"]["areas"]) == 4
    assert "articulation_reason" not in item["result"]  # ユーザーに見せない(4.2)
    assert item["guest_session_id"] == owner.removeprefix("GUEST#")
    assert "expires_at" in item  # ゲストの現在地レポートは30日TTL(08_データモデル2.2)


def test_handler_does_not_save_an_item_when_ai_output_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _assessment_report_payload()
    invalid_text = json.dumps({"nickname": "x"})  # 必須フィールド欠落。再生成しても直らない
    fake_client = _FakeClient([_fake_response(invalid_text), _fake_response(invalid_text)])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"USER#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "ASSESSMENT_REPORT")

    handler(_assessment_report_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "FAILED"
    assert updated["error"]["code"] == "AI_OUTPUT_INVALID"

    item = repository.get_item(owner, assessment_sk(payload["assessment_id"]))
    assert item is None  # 失敗時は何も残らない(09_API設計5.3)


def _purpose_proposals_payload() -> dict[str, Any]:
    choices = [
        ChoiceAnswer(question_code="Q1", option_codes=["GROWTH", "FREEDOM"]),
        ChoiceAnswer(question_code="Q2", option_codes=["SELF_DETERMINED"]),
        ChoiceAnswer(question_code="Q3", option_codes=["HAVING_OPTIONS"]),
    ]
    messages = [
        {"role": "AI", "body": "「成長」を選ばれていました。何か思い当たることがありましたか。"},
        {"role": "USER", "body": "前の職場で任される範囲が広がったときに実感しました。"},
        {"role": "AI", "body": "それはどんな場面でしたか。"},
        {"role": "USER", "body": "新しいプロジェクトを任されたときです。"},
        {"role": "AI", "body": "その感覚が3〜5年後にどうなっていてほしいですか。"},
        {"role": "USER", "body": "自分で選んだ仕事だと言える状態でいたいです。"},
    ]
    return {
        "choices": [dataclasses.asdict(choice) for choice in choices],
        "messages": messages,
    }


def _valid_proposals_json() -> str:
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


def _purpose_proposals_event(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {"job_id": job_id, "kind": "PURPOSE_PROPOSALS", "payload": payload}
    return {"Records": [{"body": json.dumps(body)}]}


def test_handler_generates_purpose_proposals_to_succeeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """完了条件「必ず3件、direction重複なし」(P3-7)。"""
    payload = _purpose_proposals_payload()
    fake_client = _FakeClient([_fake_response(_valid_proposals_json())])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"USER#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "PURPOSE_PROPOSALS")

    handler(_purpose_proposals_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "SUCCEEDED"
    proposals = updated["result"]["proposals"]
    assert len(proposals) == 3
    assert {proposal["direction"] for proposal in proposals} == {"SELF", "OTHERS", "SOCIETY"}


def test_handler_fails_purpose_proposals_job_when_fewer_than_three_persist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """完了条件「3件未満はFAILED」(P3-7)。2案だけ見せない(09_API設計5.7)。"""
    payload = _purpose_proposals_payload()
    invalid_text = json.dumps({"proposals": [], "safety_flag": False})  # 再生成しても直らない
    fake_client = _FakeClient([_fake_response(invalid_text), _fake_response(invalid_text)])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"USER#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "PURPOSE_PROPOSALS")

    handler(_purpose_proposals_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "FAILED"
    assert updated["error"]["code"] == "AI_OUTPUT_INVALID"
    assert updated["error"]["retryable"] is True


def _area_proposals_payload() -> dict[str, Any]:
    choices = [
        AreaChoiceAnswer(question_code="Q1", option_codes=["CAREER_FULFILLMENT"]),
        AreaChoiceAnswer(question_code="Q2", option_codes=["CAREER_VALUE_GROWTH"]),
        AreaChoiceAnswer(question_code="Q3", option_codes=["CAREER_POSITION_GROWTH"]),
    ]
    messages = [
        {"role": "AI", "body": "「成長」を選ばれていました。何か思い当たることがありましたか。"},
        {"role": "USER", "body": "前の職場で任される範囲が広がったときに実感しました。"},
        {"role": "AI", "body": "それが実現したとき、ありたい姿にどう近づきますか。"},
        {"role": "USER", "body": "自分から言葉にできる状態に近づきます。"},
    ]
    return {
        "purpose_statement": "まわりの人が安心して力を出せる存在でありたい。",
        "area": "CAREER",
        "choices": [dataclasses.asdict(choice) for choice in choices],
        "messages": messages,
    }


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


def _area_proposals_event(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {"job_id": job_id, "kind": "AREA_PROPOSALS", "payload": payload}
    return {"Records": [{"body": json.dumps(body)}]}


def test_handler_generates_area_proposals_to_succeeded(monkeypatch: pytest.MonkeyPatch) -> None:
    """完了条件「順序固定。回答で並べ替えない」(P4-4)。"""
    payload = _area_proposals_payload()
    fake_client = _FakeClient([_fake_response(_valid_area_proposals_json())])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"USER#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "AREA_PROPOSALS")

    handler(_area_proposals_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "SUCCEEDED"
    proposals = updated["result"]["proposals"]
    assert len(proposals) == 3
    assert [proposal["direction"] for proposal in proposals] == ["DEEPEN", "CHANGE", "EXPAND"]


def test_handler_fails_area_proposals_job_when_order_is_wrong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AIが並べ替えて出力しても、サーバー側の検証がFAILEDにする(再生成しても直らない)。"""
    payload = _area_proposals_payload()
    wrong_order = json.loads(_valid_area_proposals_json())
    wrong_order["proposals"] = list(reversed(wrong_order["proposals"]))
    invalid_text = json.dumps(wrong_order)
    fake_client = _FakeClient([_fake_response(invalid_text), _fake_response(invalid_text)])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"USER#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "AREA_PROPOSALS")

    handler(_area_proposals_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "FAILED"
    assert updated["error"]["code"] == "AI_OUTPUT_INVALID"


def test_handler_fails_area_proposals_job_when_fewer_than_three_persist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """完了条件「3件未満はFAILED」(P-04と同じ検証をP4-4にも適用)。"""
    payload = _area_proposals_payload()
    invalid_text = json.dumps({"proposals": [], "safety_flag": False})  # 再生成しても直らない
    fake_client = _FakeClient([_fake_response(invalid_text), _fake_response(invalid_text)])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    owner = f"USER#{_uid()}"
    job_id, _ = job_domain.create_job(owner, "AREA_PROPOSALS")

    handler(_area_proposals_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "FAILED"
    assert updated["error"]["code"] == "AI_OUTPUT_INVALID"


def _reflection_summary_payload() -> dict[str, Any]:
    return {
        "reflection_id": _uid(),
        "purpose_statement": "まわりの人が安心して力を出せる存在でありたい。",
        "statuses": [
            {
                "goal_key": "g-career-1",
                "area": "CAREER",
                "goal_body": "職務経歴書を書き上げる",
                "status": "ON_TRACK",
            },
            {
                "goal_key": "g-financial-1",
                "area": "FINANCIAL",
                "goal_body": "毎月の支出を把握する",
                "status": "STALLED",
            },
        ],
        "area_ideal_states": {
            "CAREER": "今の仕事の中で自分の強みが言葉になっている状態。",
            "FINANCIAL": "毎月の収支を自分で把握できている状態。",
        },
        "note": "今週は残業が続いて、時間が取れなかった",
        "answered_at": "2026-08-15T00:00:00Z",
    }


def _valid_reflection_summary_json() -> str:
    return json.dumps(
        {
            "looking_back": "Careerは前に進み、Financialは今週は手がつかなかったようです。",
            "insight": "動けた目標には、その日のうちに終わる大きさがありました。",
            "next_step": "来週は、1日1回アプリを開くだけにしてみるのはどうでしょう。",
            "safety_flag": False,
        }
    )


def _reflection_summary_event(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {"job_id": job_id, "kind": "REFLECTION_SUMMARY", "payload": payload}
    return {"Records": [{"body": json.dumps(body)}]}


def test_handler_generates_reflection_summary_to_succeeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """完了条件「全体に1つ返す。次の一歩は1つだけ」(P5-2)。"""
    payload = _reflection_summary_payload()
    fake_client = _FakeClient([_fake_response(_valid_reflection_summary_json())])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    user_id = _uid()
    owner = f"USER#{user_id}"
    job_id, _ = job_domain.create_job(owner, "REFLECTION_SUMMARY")

    handler(_reflection_summary_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "SUCCEEDED"
    reflection_id = payload["reflection_id"]
    assert updated["result"] == {"reflection_id": reflection_id}

    item = repository.get_item(
        user_pk(user_id), reflection_sk(payload["answered_at"], reflection_id)
    )
    assert item is not None
    assert item["result"]["next_step"] == (
        "来週は、1日1回アプリを開くだけにしてみるのはどうでしょう。"
    )
    assert item["statuses"] == payload["statuses"]
    assert item["note"] == payload["note"]
    assert item["answered_at"] == payload["answered_at"]


def test_handler_does_not_save_a_reflection_when_ai_output_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _reflection_summary_payload()
    invalid_text = json.dumps({"looking_back": ""})  # 必須フィールド欠落。再生成しても直らない
    fake_client = _FakeClient([_fake_response(invalid_text), _fake_response(invalid_text)])
    monkeypatch.setattr("app.ai.runner.get_client", lambda: fake_client)

    user_id = _uid()
    owner = f"USER#{user_id}"
    job_id, _ = job_domain.create_job(owner, "REFLECTION_SUMMARY")

    handler(_reflection_summary_event(job_id, payload), object())

    updated = job_domain.get_job(job_id)
    assert updated is not None
    assert updated["status"] == "FAILED"
    assert updated["error"]["code"] == "AI_OUTPUT_INVALID"
    assert updated["error"]["retryable"] is True
