"""Cognitoをユーザーディレクトリとして使う(11_技術構成7.2)。

トークンをブラウザに渡さないBFF方式。バックエンドが`SignUp`で仮登録し、`AdminConfirmSignUp`で
即座に確認済みにする(Cognito標準の確認コードメールは送らせない。7.2)。パスワードの複雑性要件
(8文字以上、英字と数字を各1文字以上)はCognito側のパスワードポリシーで守られ、`SignUp`が
`InvalidPasswordException`を返す。「よく使われるパスワードを拒否」はCognitoにない機能のため
`app.domain.weak_password`で別途照合する(7.4)。

Google連携(7.5)は`GET /auth/google` → Cognito Hosted UIの認可エンドポイント →
`GET /auth/google/callback`の流れ。認可コードのトークン交換はOAuth2標準のHTTPエンドポイントで
あり、boto3のAPI面には無いため、標準ライブラリの`urllib`で直接呼ぶ(新規の依存を増やさない
判断。P3-2の`authenticate`が「デコード用の依存を増やさない」とした判断を踏襲)。
"""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Any

import boto3
from mypy_boto3_cognito_idp.client import CognitoIdentityProviderClient

from app.core.config import get_settings


class EmailTakenError(Exception):
    """メールアドレスが既に使われている(`UsernameExistsException`)。"""


class InvalidPasswordError(Exception):
    """Cognitoのパスワードポリシーを満たさない(`InvalidPasswordException`)。"""


class InvalidCredentialsError(Exception):
    """メールアドレスまたはパスワードが正しくない。

    未登録のメールアドレス(`UserNotFoundException`)とパスワード不一致
    (`NotAuthorizedException`)を区別せず、この1種類にまとめる
    (09_API設計5.5.1「総当たりでの登録有無の特定を防ぐ」)。
    """


class GoogleAuthFailedError(Exception):
    """Googleとの連携(認可コードのトークン交換)に失敗した。

    ユーザーがGoogle側で同意しなかった場合・コードが失効している場合などを区別せず、
    この1種類にまとめる(login時のInvalidCredentialsErrorと同じ考え方)。
    """


@lru_cache
def get_client() -> CognitoIdentityProviderClient:
    settings = get_settings()
    return boto3.client("cognito-idp", region_name=settings.aws_region)


def sign_up_and_confirm(email: str, password: str) -> str:
    """新しいCognitoユーザーを作り、確認済みにした上で`sub`を返す。"""
    settings = get_settings()
    if settings.cognito_user_pool_id is None or settings.cognito_user_pool_client_id is None:
        # AppStackが必ず環境変数で渡す(技術構成7.2)。未設定はデプロイ構成の誤り。
        raise RuntimeError("COGNITO_USER_POOL_ID / COGNITO_USER_POOL_CLIENT_ID is not configured")

    client = get_client()
    try:
        response = client.sign_up(
            ClientId=settings.cognito_user_pool_client_id,
            Username=email,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
        )
    except client.exceptions.UsernameExistsException as exc:
        raise EmailTakenError from exc
    except client.exceptions.InvalidPasswordException as exc:
        raise InvalidPasswordError from exc

    client.admin_confirm_sign_up(
        UserPoolId=settings.cognito_user_pool_id,
        Username=email,
    )
    return str(response["UserSub"])


def authenticate(email: str, password: str) -> str:
    """メールアドレス・パスワードで認証し、成功すれば`sub`を返す。

    `AdminInitiateAuth`(`ADMIN_USER_PASSWORD_AUTH`フロー)を使う。`sign_up_and_confirm`が
    `AdminConfirmSignUp`という管理者権限のAPIを既に使っている流儀に揃えた。認証結果の
    `AuthenticationResult`にはIDトークンが含まれるが、デコード用の依存を増やさないため
    `AdminGetUser`で`sub`属性を取り直す。
    """
    settings = get_settings()
    if settings.cognito_user_pool_id is None or settings.cognito_user_pool_client_id is None:
        raise RuntimeError("COGNITO_USER_POOL_ID / COGNITO_USER_POOL_CLIENT_ID is not configured")

    client = get_client()
    try:
        client.admin_initiate_auth(
            UserPoolId=settings.cognito_user_pool_id,
            ClientId=settings.cognito_user_pool_client_id,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )
    except (
        client.exceptions.NotAuthorizedException,
        client.exceptions.UserNotFoundException,
    ) as exc:
        raise InvalidCredentialsError from exc

    user = client.admin_get_user(UserPoolId=settings.cognito_user_pool_id, Username=email)
    for attribute in user["UserAttributes"]:
        if attribute["Name"] == "sub":
            return str(attribute["Value"])
    raise RuntimeError("Cognito user has no sub attribute")


def _cognito_domain_url() -> str:
    settings = get_settings()
    if settings.cognito_domain_prefix is None:
        # AppStackが必ず環境変数で渡す(技術構成7.5)。未設定はデプロイ構成の誤り。
        raise RuntimeError("COGNITO_DOMAIN_PREFIX is not configured")
    return f"https://{settings.cognito_domain_prefix}.auth.{settings.aws_region}.amazoncognito.com"


@lru_cache
def _get_app_client_secret() -> str:
    """UserPoolClientのシークレット(トークン交換のクライアント認証に必要)を取り直す。

    CDK側でSecrets Manager等に複製せず、実行時に`DescribeUserPoolClient`で都度取得する
    (IAM権限だけで完結し、シークレットをCloudFormationテンプレートやLambda環境変数に
    平文で持たせずに済む)。
    """
    settings = get_settings()
    if settings.cognito_user_pool_id is None or settings.cognito_user_pool_client_id is None:
        raise RuntimeError("COGNITO_USER_POOL_ID / COGNITO_USER_POOL_CLIENT_ID is not configured")
    client = get_client()
    response = client.describe_user_pool_client(
        UserPoolId=settings.cognito_user_pool_id,
        ClientId=settings.cognito_user_pool_client_id,
    )
    secret = response["UserPoolClient"].get("ClientSecret")
    if secret is None:
        raise RuntimeError("UserPoolClient has no ClientSecret (generateSecret must be true)")
    return str(secret)


def google_authorize_url(redirect_uri: str, state: str) -> str:
    """Cognito Hosted UIの認可エンドポイントURLを組み立てる(`GET /auth/google`)。"""
    settings = get_settings()
    if settings.cognito_user_pool_client_id is None:
        raise RuntimeError("COGNITO_USER_POOL_CLIENT_ID is not configured")
    query = urllib.parse.urlencode(
        {
            "client_id": settings.cognito_user_pool_client_id,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": redirect_uri,
            "identity_provider": "Google",
            "state": state,
        },
    )
    return f"{_cognito_domain_url()}/oauth2/authorize?{query}"


def exchange_google_code(code: str, redirect_uri: str) -> str:
    """認可コードをCognitoのトークンに交換し、`sub`を返す(`GET /auth/google/callback`)。

    IDトークンのデコード用ライブラリを新規に増やさず(`authenticate`と同じ判断)、
    アクセストークンで`GetUser`を呼んで`sub`属性を取り直す。
    """
    settings = get_settings()
    if settings.cognito_user_pool_client_id is None:
        raise RuntimeError("COGNITO_USER_POOL_CLIENT_ID is not configured")

    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "client_id": settings.cognito_user_pool_client_id,
            "code": code,
            "redirect_uri": redirect_uri,
        },
    ).encode("utf-8")
    basic = base64.b64encode(
        f"{settings.cognito_user_pool_client_id}:{_get_app_client_secret()}".encode(),
    ).decode("ascii")
    request = urllib.request.Request(
        f"{_cognito_domain_url()}/oauth2/token",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            tokens: dict[str, Any] = json.loads(response.read())
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise GoogleAuthFailedError from exc

    access_token = tokens.get("access_token")
    if access_token is None:
        raise GoogleAuthFailedError("token endpoint response has no access_token")

    client = get_client()
    user = client.get_user(AccessToken=access_token)
    for attribute in user["UserAttributes"]:
        if attribute["Name"] == "sub":
            return str(attribute["Value"])
    raise RuntimeError("Cognito user has no sub attribute")
