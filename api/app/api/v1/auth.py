"""`POST /auth/register`・`POST /auth/login`・Google連携。09_API設計5.5・5.5.1・8章、
11_技術構成7.2・7.4・7.5、08_データモデル3.4、スキルflourish-api。

register(S-21)：`fs_guest`があれば、そのゲストセッションと現在地レポートを新しいアカウントへ
紐付ける。PROFILE作成・ASSESSMENT引き継ぎ・SESSION発行・GUESTの変換記録を1つの
TransactWriteItemsで行う(08_データモデル3.4)。クライアントからゲストIDやassessment_idを
送る必要はない(09_API設計2.1)ため、`fs_guest`配下のASSESSMENT#を`Query`して引き継ぎ対象を
見つける。

login(S-02)：メールアドレス未登録かパスワード不一致かを区別せず、同じ`401 INVALID_CREDENTIALS`
にまとめる(09_API設計5.5.1)。

Google連携(`GET /auth/google` → `GET /auth/google/callback`)：ゲストの紐付けはregisterと
「同じ仕組み」(09_API設計8章)のため、PROFILE作成・ゲスト紐付けの組み立てを`register`と共有する
(`_build_new_account_transact_items`)。Googleは初回サインインでCognito側にsubが新規発行される
ため、そのsubに対応するPROFILEが無ければ新規アカウント、あれば既存アカウントへのログインとして
扱う。
"""

import time
from typing import Any

from fastapi import APIRouter, Cookie, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from app.core.config import get_settings
from app.core.errors import ConflictError, UnauthorizedError, UnprocessableEntityError
from app.core.security import (
    GUEST_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    clear_auth_cookie,
    clear_oauth_state_cookie,
    generate_token,
    set_auth_cookie,
    set_oauth_state_cookie,
)
from app.db import repository
from app.db.keys import PROFILE_SK, guest_pk, user_pk
from app.domain import cognito, weak_password
from app.domain.guest_session import build_conversion_transact_item
from app.domain.session import build_session_item, create_session
from app.domain.user import build_profile_item

router = APIRouter()


def _build_new_account_transact_items(
    user_id: str, fs_guest: str | None, now: int,
) -> list[dict[str, Any]]:
    """PROFILE作成・ASSESSMENT引き継ぎ・GUESTの変換記録をまとめて返す(08_データモデル3.4)。

    register・Google連携(初回サインイン時)の両方から使う共通部分。
    """
    guest_reports = (
        repository.query_by_sk_prefix(guest_pk(fs_guest), "ASSESSMENT#") if fs_guest else []
    )
    items: list[dict[str, Any]] = [{"Put": {"Item": build_profile_item(user_id, fs_guest)}}]
    for report in guest_reports:
        # 3.4: PK = USER#<sub>, SK = 元のASSESSMENT#<id>のまま。expires_atは外す(ゲスト専用のTTL)。
        migrated_report = {**report, "PK": user_pk(user_id)}
        migrated_report.pop("expires_at", None)
        items.append({"Put": {"Item": migrated_report}})
    if fs_guest is not None:
        items.append(build_conversion_transact_item(fs_guest, user_id, now))
    return items


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

    now = int(time.time())
    token, session_item = build_session_item(user_id)
    transact_items = _build_new_account_transact_items(user_id, fs_guest, now)
    transact_items.append({"Put": {"Item": session_item}})

    repository.transact_write_items(transact_items)

    set_auth_cookie(response, SESSION_COOKIE_NAME, token)
    if fs_guest is not None:
        clear_auth_cookie(response, GUEST_COOKIE_NAME)

    return {}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/auth/login", status_code=200)
def login(body: LoginRequest, response: Response) -> dict[str, Any]:
    try:
        user_id = cognito.authenticate(email=body.email, password=body.password)
    except cognito.InvalidCredentialsError as exc:
        raise UnauthorizedError(
            "INVALID_CREDENTIALS", "email or password is incorrect",
        ) from exc

    token, _ = create_session(user_id)
    set_auth_cookie(response, SESSION_COOKIE_NAME, token)
    return {}


def _google_redirect_uri() -> str:
    settings = get_settings()
    if settings.public_domain_name is None:
        # AppStackが必ず環境変数で渡す(技術構成7.5)。未設定はデプロイ構成の誤り。
        raise RuntimeError("PUBLIC_DOMAIN_NAME is not configured")
    return f"https://{settings.public_domain_name}/api/v1/auth/google/callback"


def _app_url(path: str) -> str:
    settings = get_settings()
    if settings.public_domain_name is None:
        raise RuntimeError("PUBLIC_DOMAIN_NAME is not configured")
    return f"https://{settings.public_domain_name}/app{path}"


@router.get("/auth/google")
def google_authorize() -> RedirectResponse:
    """Cognito Hosted UIの認可エンドポイントへ302で送る(11_技術構成7.5)。

    `state`をHttpOnly Cookieに一時保存し、コールバックで一致を確認する(CSRF対策)。
    """
    state = generate_token()
    redirect = RedirectResponse(
        cognito.google_authorize_url(_google_redirect_uri(), state), status_code=302,
    )
    set_oauth_state_cookie(redirect, state)
    return redirect


@router.get("/auth/google/callback")
def google_callback(
    code: str | None = None,
    state: str | None = None,
    fs_guest: str | None = Cookie(default=None),
    fs_oauth_state: str | None = Cookie(default=None),
) -> RedirectResponse:
    """コールバックはバックエンドが受け、トークンを交換して`SESSION`を発行する(7.5)。

    トークンをブラウザに返さない点はメール認証と同じ。`state`が一致しない・認可コードが
    無い・トークン交換に失敗した場合は、いずれもログイン画面(S-02)へ戻す(自動リトライは
    せず、ユーザーの操作でやり直せる状態にする)。
    """
    if code is None or state is None or fs_oauth_state is None or state != fs_oauth_state:
        redirect = RedirectResponse(_app_url("/s-02"), status_code=302)
        clear_oauth_state_cookie(redirect)
        return redirect

    try:
        user_id = cognito.exchange_google_code(code, _google_redirect_uri())
    except cognito.GoogleAuthFailedError:
        redirect = RedirectResponse(_app_url("/s-02"), status_code=302)
        clear_oauth_state_cookie(redirect)
        return redirect

    # このsubに対応するPROFILEがまだ無ければ、Googleでの初回サインイン(=新規アカウント)。
    # ゲストの紐付けはregisterと同じ仕組みを使う(09_API設計8章)。
    existing_profile = repository.get_item(user_pk(user_id), PROFILE_SK)
    now = int(time.time())
    token, session_item = build_session_item(user_id)
    transact_items = (
        _build_new_account_transact_items(user_id, fs_guest, now)
        if existing_profile is None
        else []
    )
    transact_items.append({"Put": {"Item": session_item}})
    repository.transact_write_items(transact_items)

    redirect = RedirectResponse(_app_url("/s-41"), status_code=302)
    set_auth_cookie(redirect, SESSION_COOKIE_NAME, token)
    clear_oauth_state_cookie(redirect)
    if fs_guest is not None and existing_profile is None:
        clear_auth_cookie(redirect, GUEST_COOKIE_NAME)
    return redirect
