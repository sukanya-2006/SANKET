import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

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

# Plug the real classifier into the primary slot. Without this, classifier.py keeps using
# the stub no matter how many times classifier_llm is imported.
#
# Defensive on purpose. If the groq package is missing or GROQ_API_KEY is unset, the API must
# still start on the baseline rather than refusing to boot: the frontend needs a running API to
# develop against, the test suite needs to import this module, and a deployment that cannot
# start has no degraded mode at all. /health reports which classifier actually got registered,
# so a stub answering in production is visible rather than silent.
log = logging.getLogger(__name__)

try:
    from . import classifier_llm

    classifier.register_primary(classifier_llm.classify)
except Exception as exc:  # noqa: BLE001
    log.warning(
        "real classifier unavailable (%s: %s) — running on the baseline. "
        "Check GROQ_API_KEY and `pip install -r requirements.txt`.",
        type(exc).__name__,
        exc,
    )

# The baseline is what answers when the primary fails, times out, or returns output the schema
# rejects twice. It needs baseline_model.joblib, which only exists after train_baseline.py runs
# against a completed gold_labels.csv — so before labelling finishes this legitimately cannot
# load, and the stub holds the slot instead.
#
# Registered defensively for the same reason as the primary, and so it wires itself in the
# moment the model file appears rather than needing a code change nobody remembers to make on
# demo day. Until then the degraded path answers with the keyword stub, which is weaker than the
# TF-IDF baseline the pitch describes — /health names the slot honestly so that gap stays
# visible rather than being discovered on stage.
try:
    from . import classifier_base

    classifier.register_baseline(classifier_base.classify)
except Exception as exc:  # noqa: BLE001
    log.warning(
        "TF-IDF baseline unavailable (%s: %s) — the fallback path will answer with the "
        "keyword stub. Run train_baseline.py once data/gold_labels.csv exists.",
        type(exc).__name__,
        exc,
    )


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
