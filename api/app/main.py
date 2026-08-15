from fastapi import FastAPI

from app.api.v1 import guest_sessions, jobs
from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers

settings = get_settings()

app = FastAPI(title="Flourish Studio API", debug=settings.environment == "local")
register_error_handlers(app)
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(guest_sessions.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
