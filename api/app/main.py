from fastapi import FastAPI

from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers

settings = get_settings()

app = FastAPI(title="Flourish Studio API", debug=settings.environment == "local")
register_error_handlers(app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
