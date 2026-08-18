"""ワーカーLambdaのエントリポイント。SQSからジョブを受け取り処理する(11_技術構成5.5)。

kindごとに実際の生成処理(Bedrock呼び出し)へ分岐する。未実装のkindは雛形段階(P1-13)の
ままダミーの結果ですぐSUCCEEDEDにする。

SQSはmaxReceiveCount=1で自動リトライしない(破ってはいけない規則5)。失敗はFAILEDとして
記録するだけで、ここから再送はしない。
"""

import json
from typing import Any

from app.ai.prompts import (
    area_proposals,
    assessment_questions,
    assessment_report,
    purpose_proposals,
    reflection_summary,
)
from app.ai.prompts.purpose_dialogue import DialogueMessage
from app.domain import job as job_domain
from app.domain.area_choices import ChoiceAnswer as AreaChoiceAnswer
from app.domain.assessment import build_assessment_item, now_iso
from app.domain.assessment_precompute import FreeTextAnswer, ScaleAnswer, compute_commitment
from app.domain.purpose_choices import ChoiceAnswer
from app.domain.questions import get_question_set
from app.domain.reflection import ResolvedStatus, build_reflection_item
from app.domain.reflection import now_iso as reflection_now_iso


def handler(event: dict[str, Any], context: object) -> dict[str, str]:
    records = event.get("Records", [])
    for record in records:
        _process_record(record)
    return {"status": "ok"}


def _process_record(record: dict[str, Any]) -> None:
    body = json.loads(record["body"])
    job_id = body["job_id"]
    kind = body["kind"]

    job_domain.mark_running(job_id)
    current = job_domain.get_job(job_id)
    if current is None:
        return

    if kind == "ASSESSMENT_QUESTIONS":
        _process_assessment_questions(job_id, body.get("payload", {}))
        return
    if kind == "ASSESSMENT_REPORT":
        _process_assessment_report(job_id, current["owner"], body.get("payload", {}))
        return
    if kind == "PURPOSE_PROPOSALS":
        _process_purpose_proposals(job_id, body.get("payload", {}))
        return
    if kind == "AREA_PROPOSALS":
        _process_area_proposals(job_id, body.get("payload", {}))
        return
    if kind == "REFLECTION_SUMMARY":
        _process_reflection_summary(job_id, current["owner"], body.get("payload", {}))
        return

    job_domain.mark_succeeded(job_id, result={"echo": current["kind"]})


def _process_assessment_questions(job_id: str, payload: dict[str, Any]) -> None:
    question_set = get_question_set(payload["question_set_version"])
    targets = [assessment_questions.QuestionTarget(**target) for target in payload["targets"]]

    result = assessment_questions.generate_assessment_questions(
        targets, question_set, identifiers={"job_id": job_id}
    )
    if result.status == "SUCCEEDED":
        assert result.output is not None
        job_domain.mark_succeeded(job_id, result=result.output)
    else:
        assert result.error is not None
        job_domain.mark_failed(job_id, code=result.error.code, retryable=result.error.retryable)


def _process_assessment_report(job_id: str, owner: str, payload: dict[str, Any]) -> None:
    question_set = get_question_set(payload["question_set_version"])
    scale_answers = [ScaleAnswer(**answer) for answer in payload["scale_answers"]]
    free_text_answers = [FreeTextAnswer(**answer) for answer in payload["free_text_answers"]]

    result = assessment_report.generate_assessment_report(
        scale_answers, free_text_answers, question_set, identifiers={"job_id": job_id}
    )
    if result.status != "SUCCEEDED":
        assert result.error is not None
        job_domain.mark_failed(job_id, code=result.error.code, retryable=result.error.retryable)
        return

    assert result.output is not None
    assessment_id = payload["assessment_id"]
    item = build_assessment_item(
        owner=owner,
        assessment_id=assessment_id,
        question_set_version=payload["question_set_version"],
        scale_answers=scale_answers,
        free_text_answers=free_text_answers,
        ai_output=result.output,
        commitment=compute_commitment(scale_answers),
        started_at=payload["started_at"],
        completed_at=now_iso(),
    )
    # 成功した時点ではじめて保存する(09_API設計5.3)。JOB完了と成果物保存を1トランザクションに
    # まとめ、片方だけが書かれる状態を作らない(スキルflourish-api)。
    job_domain.mark_succeeded_with_item(job_id, result={"assessment_id": assessment_id}, item=item)


def _process_purpose_proposals(job_id: str, payload: dict[str, Any]) -> None:
    choices = [ChoiceAnswer(**choice) for choice in payload["choices"]]
    messages = [DialogueMessage(**message) for message in payload["messages"]]

    # 09_API設計5.7「保存しない」。POST /purposes(P3-8)で確定時にはじめて保存する。
    result = purpose_proposals.generate_purpose_proposals(
        choices, messages, identifiers={"job_id": job_id}
    )
    if result.status == "SUCCEEDED":
        assert result.output is not None
        job_domain.mark_succeeded(job_id, result=result.output)
    else:
        assert result.error is not None
        job_domain.mark_failed(job_id, code=result.error.code, retryable=result.error.retryable)


def _process_reflection_summary(job_id: str, owner: str, payload: dict[str, Any]) -> None:
    user_id = owner.removeprefix("USER#")
    statuses = [ResolvedStatus(**status) for status in payload["statuses"]]

    result = reflection_summary.generate_reflection_summary(
        payload["purpose_statement"],
        statuses,
        payload["area_ideal_states"],
        payload["note"],
        identifiers={"job_id": job_id},
    )
    if result.status != "SUCCEEDED":
        assert result.error is not None
        job_domain.mark_failed(job_id, code=result.error.code, retryable=result.error.retryable)
        return

    assert result.output is not None
    reflection_id = payload["reflection_id"]
    # 09_API設計5.14「成功時に回答とAI出力をまとめて保存する」。JOB完了とREFLECTION保存を
    # 1トランザクションにまとめる(assessment_reportと同じ設計)。
    item = build_reflection_item(
        user_id=user_id,
        reflection_id=reflection_id,
        statuses=statuses,
        note=payload["note"],
        ai_output=result.output,
        answered_at=payload["answered_at"],
        generated_at=reflection_now_iso(),
    )
    job_domain.mark_succeeded_with_item(job_id, result={"reflection_id": reflection_id}, item=item)


def _process_area_proposals(job_id: str, payload: dict[str, Any]) -> None:
    choices = [AreaChoiceAnswer(**choice) for choice in payload["choices"]]
    messages = [DialogueMessage(**message) for message in payload["messages"]]

    # 09_API設計6章「S-53生成中」相当。保存しない。
    # POST /area-plans(P4-6)で確定時にはじめて保存する。
    result = area_proposals.generate_area_proposals(
        payload["purpose_statement"],
        payload["area"],
        choices,
        messages,
        identifiers={"job_id": job_id},
    )
    if result.status == "SUCCEEDED":
        assert result.output is not None
        job_domain.mark_succeeded(job_id, result=result.output)
    else:
        assert result.error is not None
        job_domain.mark_failed(job_id, code=result.error.code, retryable=result.error.retryable)
