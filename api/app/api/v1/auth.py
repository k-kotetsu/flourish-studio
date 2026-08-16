"""`POST /auth/register`。09_API設計5.5、11_技術構成7.2・7.4、08_データモデル3.4、
スキルflourish-api。

S-21。`fs_guest`があれば、そのゲストセッションと現在地レポートを新しいアカウントへ紐付ける。
PROFILE作成・ASSESSMENT引き継ぎ・SESSION発行・GUESTの変換記録を1つのTransactWriteItemsで行う
(08_データモデル3.4)。クライアントからゲストIDやassessment_idを送る必要はない
(09_API設計2.1)ため、`fs_guest`配下のASSESSMENT#を`Query`して引き継ぎ対象を見つける。
"""

import time
from typing import Any

from fastapi import APIRouter, Cookie, Response
from pydantic import BaseModel, EmailStr

from app.core.errors import ConflictError, UnprocessableEntityError
from app.core.security import (
    GUEST_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    clear_auth_cookie,
    set_auth_cookie,
)
from app.db import repository
from app.db.keys import guest_pk, user_pk
from app.domain import cognito, weak_password
from app.domain.guest_session import build_conversion_transact_item
from app.domain.session import build_session_item
from app.domain.user import build_profile_item

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/auth/register", status_code=201)
def register(
    body: RegisterRequest,
    response: Response,
    fs_guest: str | None = Cookie(default=None),
) -> dict[str, Any]:
    # 「よく使われるパスワードを拒否」はCognitoにない機能のため先に照合する(11_技術構成7.4)。
    if weak_password.is_common_password(body.password):
        raise UnprocessableEntityError(
            "WEAK_PASSWORD", "password is on the common/breached password list",
        )

    try:
        user_id = cognito.sign_up_and_confirm(email=body.email, password=body.password)
    except cognito.EmailTakenError as exc:
        raise ConflictError("EMAIL_TAKEN", "email is already registered") from exc
    except cognito.InvalidPasswordError as exc:
        raise UnprocessableEntityError(
            "WEAK_PASSWORD", "password does not satisfy the password policy",
        ) from exc

    guest_reports = (
        repository.query_by_sk_prefix(guest_pk(fs_guest), "ASSESSMENT#") if fs_guest else []
    )

    now = int(time.time())
    token, session_item = build_session_item(user_id)
    transact_items: list[dict[str, Any]] = [
        {"Put": {"Item": build_profile_item(user_id, fs_guest)}},
    ]
    for report in guest_reports:
        # 3.4: PK = USER#<sub>, SK = 元のASSESSMENT#<id>のまま。expires_atは外す(ゲスト専用のTTL)。
        migrated_report = {**report, "PK": user_pk(user_id)}
        migrated_report.pop("expires_at", None)
        transact_items.append({"Put": {"Item": migrated_report}})
    transact_items.append({"Put": {"Item": session_item}})
    if fs_guest is not None:
        transact_items.append(build_conversion_transact_item(fs_guest, user_id, now))

    repository.transact_write_items(transact_items)

    set_auth_cookie(response, SESSION_COOKIE_NAME, token)
    if fs_guest is not None:
        clear_auth_cookie(response, GUEST_COOKIE_NAME)

    return {}
