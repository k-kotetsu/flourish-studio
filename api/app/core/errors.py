"""アプリケーション層の例外。09_API設計2.2〜2.3、スキルflourish-apiのステータスコード対応。"""

from typing import Any


class AppError(Exception):
    """`code`はクライアントが分岐に使う。追加はしても意味は変えない(flourish-api)。"""

    status_code: int = 400

    def __init__(
        self,
        code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class BadRequestError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class UnprocessableEntityError(AppError):
    status_code = 422


class RateLimitedError(AppError):
    """超過時は`Retry-After`を返す(09_API設計2.4)。"""

    status_code = 429

    def __init__(
        self,
        code: str,
        message: str,
        retry_after: int,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(code, message, details)
        self.retry_after = retry_after


class ServiceUnavailableError(AppError):
    status_code = 503
