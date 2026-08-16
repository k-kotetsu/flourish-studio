"""流出パスワードの照合。11_技術構成7.4「よく使われるパスワードを拒否」。

Cognitoのパスワードポリシーにはこの機能がないため、バックエンドで実装する。上位1万件程度の
リストを`api/app/data/common_passwords.txt`としてLambdaに同梱し、Cognitoに渡す前に照合する。
"""

from functools import lru_cache
from pathlib import Path

_LIST_PATH = Path(__file__).resolve().parent.parent / "data" / "common_passwords.txt"


@lru_cache
def _common_passwords() -> frozenset[str]:
    lines = _LIST_PATH.read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip().lower() for line in lines if line.strip())


def is_common_password(password: str) -> bool:
    return password.lower() in _common_passwords()
