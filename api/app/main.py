from fastapi import FastAPI

from app.api.v1 import (
    ai_area_dialogue,
    ai_area_proposals,
    ai_assessment_questions,
    ai_goal_hints,
    ai_purpose_dialogue,
    ai_purpose_proposals,
    area_plans,
    assessments,
    auth,
    guest_sessions,
    jobs,
    me,
    purposes,
)
from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers

settings = get_settings()

app = FastAPI(title="Flourish Studio API", debug=settings.environment == "local")
register_error_handlers(app)
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(guest_sessions.router, prefix="/api/v1")
app.include_router(ai_assessment_questions.router, prefix="/api/v1")
app.include_router(assessments.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(ai_purpose_dialogue.router, prefix="/api/v1")
app.include_router(ai_purpose_proposals.router, prefix="/api/v1")
app.include_router(purposes.router, prefix="/api/v1")
app.include_router(ai_area_dialogue.router, prefix="/api/v1")
app.include_router(ai_area_proposals.router, prefix="/api/v1")
app.include_router(ai_goal_hints.router, prefix="/api/v1")
app.include_router(area_plans.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
