"""生成系エンドポイントのレート制限。09_API設計2.4、スキルflourish-api「レート制限」。

登録済みユーザーは時間枠のカウンタ(RATE、08_データモデル8.3)、ゲストはGUESTアイテムの
`report_generation_count`(08_データモデル6.2)で数える。いずれも読んでから書かず、
上限判定と加算を1回のUpdateItemで行う。WAFではなくアプリ層の実装(ユーザー単位の業務ルールのため)。
"""

import time
from datetime import UTC, datetime
from typing import Any

from app.core.errors import RateLimitedError
from app.db import repository
from app.db.keys import GUEST_SK, RATE_SK, guest_pk, rate_pk

Item = dict[str, Any]

# 登録済み: 1時間30回(09_API設計2.4)
USER_HOURLY_LIMIT = 30

# ゲスト: 1セッション3回、初回+再試行2回(09_API設計2.4)
GUEST_SESSION_LIMIT = 3

# 枠終了+1時間(08_データモデル8.3)
_RATE_TTL_BUFFER_SECONDS = 60 * 60


def _current_hour_window(now: int) -> tuple[str, int]:
    hour_start = datetime.fromtimestamp(now, tz=UTC).replace(minute=0, second=0, microsecond=0)
    window = hour_start.strftime("%Y-%m-%dT%H")
    window_end = int(hour_start.timestamp()) + 60 * 60
    return window, window_end


def check_and_increment_user(owner: str, limit: int = USER_HOURLY_LIMIT) -> None:
    """登録済みユーザーの生成系呼び出しを数える。上限超過は`RateLimitedError`(429)。"""
    now = int(time.time())
    window, window_end = _current_hour_window(now)
    try:
        repository.update_item(
            rate_pk(owner, window),
            RATE_SK,
            update_expression="ADD #c :one SET expires_at = :exp",
            expression_attribute_names={"#c": "count"},
            expression_attribute_values={
                ":one": 1,
                ":exp": window_end + _RATE_TTL_BUFFER_SECONDS,
                ":limit": limit,
            },
            condition_expression="attribute_not_exists(#c) OR #c < :limit",
        )
    except repository.ConditionalCheckFailed as error:
        raise RateLimitedError(
            "RATE_LIMITED",
            "hourly generation limit exceeded",
            retry_after=window_end - now,
        ) from error


def check_and_increment_guest(guest_token: str, limit: int = GUEST_SESSION_LIMIT) -> None:
    """ゲストのレポート生成回数を数える。専用カウンタを作らずGUESTアイテムの属性で数える(08_データモデル6.2)。"""
    now = int(time.time())
    try:
        repository.update_item(
            guest_pk(guest_token),
            GUEST_SK,
            update_expression="ADD report_generation_count :one",
            expression_attribute_values={":one": 1, ":limit": limit},
            condition_expression="report_generation_count < :limit",
        )
    except repository.ConditionalCheckFailed as error:
        guest_item = repository.get_item(guest_pk(guest_token), GUEST_SK)
        retry_after = max(int(guest_item["expires_at"]) - now, 0) if guest_item else 0
        raise RateLimitedError(
            "RATE_LIMITED",
            "guest report generation limit exceeded",
            retry_after=retry_after,
        ) from error
