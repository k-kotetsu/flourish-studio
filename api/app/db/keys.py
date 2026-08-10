"""flourishテーブルのPK/SK生成。キーの一覧はスキルflourish-data、08_データモデル2.2を参照。"""

PROFILE_SK = "PROFILE"
GUEST_SK = "GUEST"
SESSION_SK = "SESSION"
JOB_SK = "JOB"
IDEM_SK = "IDEM"
RATE_SK = "RATE"


def user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def guest_pk(guest_id: str) -> str:
    return f"GUEST#{guest_id}"


def session_pk(token_hash: str) -> str:
    return f"SESSION#{token_hash}"


def job_pk(job_id: str) -> str:
    return f"JOB#{job_id}"


def idem_pk(owner: str, key: str) -> str:
    return f"IDEM#{owner}#{key}"


def rate_pk(owner: str, window: str) -> str:
    return f"RATE#{owner}#{window}"


def assessment_sk(assessment_id: str) -> str:
    return f"ASSESSMENT#{assessment_id}"


def purpose_current_sk() -> str:
    return "PURPOSE#CURRENT"


def area_current_sk(area: str) -> str:
    return f"AREA#{area}#CURRENT"


def reflection_sk(answered_at: str, reflection_id: str) -> str:
    return f"REFLECTION#{answered_at}#{reflection_id}"


def history_sk(prefix: str, version: int) -> str:
    return f"HIST#{prefix}#{version:06d}"
