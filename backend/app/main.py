from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import get_settings

settings = get_settings()

app = FastAPI(
    title="SIF Precursor Detection API",
    description="AI/NLP engine to detect SIF precursors — SIH 2026 (PS SIH26165). Phase 1: stub responses.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "stub_mode": settings.stub_mode,
        "database": "connected" if settings.db_configured else "not_configured",
        "rubric_version": settings.rubric_version,
    }
