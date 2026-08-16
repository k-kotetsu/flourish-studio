"""Cognitoをユーザーディレクトリとして使う(11_技術構成7.2)。

トークンをブラウザに渡さないBFF方式。バックエンドが`SignUp`で仮登録し、`AdminConfirmSignUp`で
即座に確認済みにする(Cognito標準の確認コードメールは送らせない。7.2)。パスワードの複雑性要件
(8文字以上、英字と数字を各1文字以上)はCognito側のパスワードポリシーで守られ、`SignUp`が
`InvalidPasswordException`を返す。「よく使われるパスワードを拒否」はCognitoにない機能のため
`app.domain.weak_password`で別途照合する(7.4)。
"""

from functools import lru_cache

import boto3
from mypy_boto3_cognito_idp.client import CognitoIdentityProviderClient

from app.core.config import get_settings


class EmailTakenError(Exception):
    """メールアドレスが既に使われている(`UsernameExistsException`)。"""


class InvalidPasswordError(Exception):
    """Cognitoのパスワードポリシーを満たさない(`InvalidPasswordException`)。"""


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
