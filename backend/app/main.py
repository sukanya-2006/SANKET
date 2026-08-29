from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import classifier, db
from .api.routes import router
from .config import get_settings

settings = get_settings()

app = FastAPI(
    title="SIF Precursor Detection API",
    description=(
        "AI/NLP engine to detect SIF precursors — SIH 2026 (PS SIH26165, Oil India Limited). "
        "Classifies free-text safety reports through a three-gate rubric, tags them to IOGP "
        "Life-Saving Rules, and ranks sites by precursor density. It never closes a report; "
        "it reorders the reading queue."
    ),
    version="0.2.0",
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
    """Liveness plus what is actually wired behind it.

    Deliberately honest: it names the classifiers in use, so nobody demos the keyword stub
    believing it is the Claude classifier.
    """
    versions = classifier.active_versions()
    return {
        "status": "ok",
        "database": "connected" if db.is_live() else "not_configured",
        "data_source": "postgres" if db.is_live() else "seeded_stub",
        "primary_classifier": versions["primary"],
        "baseline_classifier": versions["baseline"],
        "rubric_version": settings.rubric_version,
        "prompt_version": settings.prompt_version,
    }
