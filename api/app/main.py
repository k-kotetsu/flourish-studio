from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Flourish Studio API", debug=settings.environment == "local")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
