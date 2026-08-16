"""評価セット実行環境(10_AIプロンプト設計6.1、P2-13)。

固定入力(`fixtures.EVAL_SETS`)ごとに、実運用と同じ経路(P-01→P-02)で生成を通し、
結果を`eval_output/`にJSONで書き出す。人がそれを読んでレビューする(6.2)。

対象は現時点で実装済みの2種(ASSESSMENT_QUESTIONS・ASSESSMENT_REPORT)のみ。
残り(PURPOSE_DIALOGUE等)はP3以降でプロンプトが実装され次第、`_run_one`に追加する
拡張前提の構成にした(P2-13完了メモ参照)。

`make eval`から実行する。実際にBedrockを呼ぶため、AWS認証(`aws sso login`)が要る。
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from app.ai.prompts.assessment_questions import build_targets, generate_assessment_questions
from app.ai.prompts.assessment_report import generate_assessment_report
from app.ai.runner import GenerationResult
from app.domain.assessment_precompute import FreeTextAnswer
from app.domain.questions import CURRENT_QUESTION_SET_VERSION, QuestionSet, get_question_set
from app.eval.fixtures import EVAL_SETS, EvalSet, FreeTextBodies

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "eval_output"


@dataclasses.dataclass(frozen=True)
class EvalSetResult:
    id: int
    name: str
    assessment_questions: GenerationResult
    assessment_report: GenerationResult | None


def _build_free_text_answers(
    questions: list[dict[str, Any]], bodies: FreeTextBodies
) -> list[FreeTextAnswer]:
    """P-01の出力(`generated_question`)と、評価セットの固定回答本文を組み合わせる。

    実運用でもS-13(AIが問いを生成)→S-14(ユーザーが回答)の順で`FreeTextAnswer`が
    組み立てられるため、同じ順序をここでも踏襲する。
    """
    return [
        FreeTextAnswer(
            area=question["area"],
            slot=question["slot"],
            target_item_code=question["target_item_code"],
            generated_question=question["text"],
            body=bodies[(question["area"], question["slot"])],
        )
        for question in questions
    ]


def _run_one(eval_set: EvalSet, question_set: QuestionSet) -> EvalSetResult:
    scale_answers = eval_set.build_scale_answers(question_set)
    identifiers = {"eval_set": str(eval_set.id)}

    targets = build_targets(scale_answers, question_set)
    questions_result = generate_assessment_questions(
        targets, question_set, identifiers=identifiers
    )

    if questions_result.status != "SUCCEEDED" or questions_result.output is None:
        return EvalSetResult(
            id=eval_set.id,
            name=eval_set.name,
            assessment_questions=questions_result,
            assessment_report=None,
        )

    free_text_answers = _build_free_text_answers(
        questions_result.output["questions"], eval_set.free_text_bodies
    )
    report_result = generate_assessment_report(
        scale_answers, free_text_answers, question_set, identifiers=identifiers
    )
    return EvalSetResult(
        id=eval_set.id,
        name=eval_set.name,
        assessment_questions=questions_result,
        assessment_report=report_result,
    )


def _write_result(output_dir: Path, result: EvalSetResult) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"set_{result.id:02d}.json"
    path.write_text(
        json.dumps(dataclasses.asdict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def run_all(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[EvalSetResult]:
    question_set = get_question_set(CURRENT_QUESTION_SET_VERSION)
    results = []
    for eval_set in EVAL_SETS:
        result = _run_one(eval_set, question_set)
        _write_result(output_dir, result)
        results.append(result)
    return results


def main() -> None:
    results = run_all()
    for result in results:
        report_status = result.assessment_report.status if result.assessment_report else "SKIPPED"
        print(
            f"[{result.id}] {result.name}: "
            f"ASSESSMENT_QUESTIONS={result.assessment_questions.status} "
            f"ASSESSMENT_REPORT={report_status}"
        )
    print(f"\n出力先: {DEFAULT_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
