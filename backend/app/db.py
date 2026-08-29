"""Supabase access.

Phase 1 runs with no database: `get_client()` returns None when credentials are absent, and
the routes fall back to the seeded stub. That is deliberate — Member 5 must never be blocked on
a database being up, and the demo must not die because a free-tier instance went to sleep.

Phase 3 wires the readers below into the routes. The response models do not change.

Never import the service key into anything the frontend can reach. The frontend talks to
FastAPI; FastAPI talks to Supabase.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import get_settings

log = logging.getLogger(__name__)

SQL_DIR = Path(__file__).parent / "sql"
SCHEMA_SQL = SQL_DIR / "schema.sql"
AGGREGATES_SQL = SQL_DIR / "aggregates.sql"


@lru_cache
def get_client() -> Any | None:
    """The Supabase client, or None when the API is running database-free.

    Cached: one client per process. Import of `supabase` is deferred so Phase 1 does not
    require the package to be installed.
    """
    settings = get_settings()
    if not settings.db_configured:
        return None

    try:
        from supabase import create_client
    except ImportError:
        log.warning("SUPABASE_URL is set but the supabase package is not installed")
        return None

    return create_client(settings.supabase_url, settings.supabase_service_key)


def is_live() -> bool:
    """True when a real database is behind the API rather than the seeded stub."""
    return get_client() is not None


def insert_prediction(report_id: str, result: Any, model_version: str, is_fallback: bool = False) -> None:
    """Append one prediction. Never updates — the table is append-only by design, so an
    earlier judgement stays on the record and 'every judgement is logged' is structural.
    """
    client = get_client()
    if client is None:
        return

    client.table("predictions").insert(
        {
            "report_id": report_id,
            "hazard_assessment": result.hazard_assessment.value,
            "lsr_rule": result.lsr_rule.value,
            "control_status": result.control_status.value if result.control_status else None,
            "severity": result.severity,
            "is_sif_precursor": result.is_sif_precursor,
            "confidence": result.confidence,
            "flagged_phrases": result.flagged_phrases,
            "reasoning": result.reasoning,
            "model_version": model_version,
            "is_fallback": is_fallback,
        }
    ).execute()
