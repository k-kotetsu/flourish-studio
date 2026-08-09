"""ワーカーLambdaのエントリポイント。ジョブ処理の実装はP1-13で行う。"""

from typing import Any


def handler(event: dict[str, Any], context: object) -> dict[str, str]:
    records = event.get("Records", [])
    print(f"received {len(records)} record(s)")
    return {"status": "ok"}
