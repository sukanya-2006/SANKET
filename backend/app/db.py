"""Database access - plain parameterised SQL against Supabase Postgres.

Supabase is Postgres, so we connect with psycopg over the connection string rather than through
the REST client. That is deliberate: it lets the aggregation execute the exact statements in
sql/aggregates.sql, which is the artifact Member 4 has to be able to read aloud, instead of
reimplementing them in a query builder where nobody can check them.

The API runs fine with no database. is_live() is false, and every caller falls back to the
seeded stub. Member 5 is never blocked on an instance being awake, and the demo does not die
because a free-tier database went to sleep.

Never let the connection string reach the frontend. The browser talks to FastAPI; FastAPI talks
to Postgres.
"""

from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

from .config import get_settings

log = logging.getLogger(__name__)

SQL_DIR = Path(__file__).parent / "sql"
SCHEMA_SQL = SQL_DIR / "schema.sql"
AGGREGATES_SQL = SQL_DIR / "aggregates.sql"


@lru_cache
def named_statements() -> dict[str, str]:
    text = AGGREGATES_SQL.read_text(encoding="utf-8")
    blocks = re.split(r"^--\s*name:\s*(\w+)\s*$", text, flags=re.MULTILINE)

    statements: dict[str, str] = {}
    for name, body in zip(blocks[1::2], blocks[2::2]):
        sql = "\n".join(
            line for line in body.splitlines() if not line.strip().startswith("--")
        ).strip()
        if sql:
            statements[name] = sql
    return statements


def statement(name: str) -> str:
    try:
        return named_statements()[name]
    except KeyError:
        raise KeyError(f"no statement named {name!r} in {AGGREGATES_SQL.name}") from None


def is_live() -> bool:
    """True when a real database is behind the API rather than the seeded stub."""
    if not get_settings().db_configured:
        return False

    try:
        import psycopg  # noqa: F401
    except ImportError:
        log.warning("SUPABASE_DB_URL is set but psycopg is not installed; using the stub")
        return False

    return True


@contextmanager
def connection() -> Iterator[Any]:
    """A short-lived connection for individual database operations."""
    import psycopg

    conn = psycopg.connect(get_settings().supabase_db_url)

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Run a SELECT and return rows as dicts. Always parameterised - never f-strings."""
    from psycopg.rows import dict_row

    with connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params or {})
        return list(cur.fetchall())


def execute(sql: str, params: dict[str, Any] | None = None) -> int:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params or {})
        return cur.rowcount


def executemany(sql: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0

    with connection() as conn, conn.cursor() as cur:
        cur.executemany(sql, rows)
        return cur.rowcount


def apply_schema() -> None:
    """Create the tables and the latest_predictions view. Idempotent - safe to re-run."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        cur.execute(statement("latest_predictions"))

    log.info("schema applied")


INSERT_REPORT = """
INSERT INTO reports (
    report_id, report_text, source, site, activity, shift, report_date, is_contractor, created_at
) VALUES (
    %(report_id)s, %(report_text)s, %(source)s, %(site)s, %(activity)s, %(shift)s,
    %(report_date)s, %(is_contractor)s, %(created_at)s
)
"""


def insert_report(
    report_id: str,
    report_text: str,
    source: str,
    site: str | None,
    activity: str | None,
    shift: str | None,
    is_contractor: bool | None,
    created_at: Any,
) -> None:
    """Write one report row to reports.

    Errors propagate to the caller. This function is intentionally not a silent no-op.
    """
    execute(
        INSERT_REPORT,
        {
            "report_id": report_id,
            "report_text": report_text,
            "source": source,
            "site": site,
            "activity": activity,
            "shift": shift,
            "report_date": created_at.date(),
            "is_contractor": is_contractor,
            "created_at": created_at,
        },
    )


INSERT_PREDICTION = """
INSERT INTO predictions (
    report_id, hazard_assessment, lsr_rule, control_status, severity,
    is_sif_precursor, confidence, flagged_phrases, reasoning,
    model_version, prompt_version, is_fallback
) VALUES (
    %(report_id)s, %(hazard_assessment)s, %(lsr_rule)s, %(control_status)s, %(severity)s,
    %(is_sif_precursor)s, %(confidence)s, %(flagged_phrases)s, %(reasoning)s,
    %(model_version)s, %(prompt_version)s, %(is_fallback)s
)
"""


def prediction_row(
    report_id: str,
    result: Any,
    model_version: str,
    is_fallback: bool,
) -> dict:
    import json

    return {
        "report_id": report_id,
        "hazard_assessment": result.hazard_assessment.value,
        "lsr_rule": result.lsr_rule.value,
        "control_status": result.control_status.value if result.control_status else None,
        "severity": result.severity,
        "is_sif_precursor": result.is_sif_precursor,
        "confidence": result.confidence,
        "flagged_phrases": json.dumps(result.flagged_phrases),
        "reasoning": result.reasoning,
        "model_version": model_version,
        "prompt_version": get_settings().prompt_version,
        "is_fallback": is_fallback,
    }


def insert_prediction(
    report_id: str,
    result: Any,
    model_version: str,
    is_fallback: bool = False,
) -> None:
    """Append one prediction.

    Never an UPDATE. The table is append-only by design.
    """
    if not is_live():
        return

    execute(
        INSERT_PREDICTION,
        prediction_row(report_id, result, model_version, is_fallback),
    )


def set_report_status(report_id: str, status: str) -> None:
    """Upsert one report's workflow status.

    Status is current workflow state, so there is one current status per report.
    """
    if not is_live():
        return

    execute(
        """
        INSERT INTO report_status (report_id, status, updated_at)
        VALUES (%(report_id)s, %(status)s, now())
        ON CONFLICT (report_id)
        DO UPDATE SET
            status = EXCLUDED.status,
            updated_at = EXCLUDED.updated_at
        """,
        {
            "report_id": report_id,
            "status": status,
        },
    )


def save_report_bundle(
    *,
    report_id: str,
    report_text: str,
    source: str,
    site: str | None,
    activity: str | None,
    shift: str | None,
    is_contractor: bool | None,
    created_at: Any,
    result: Any,
    model_version: str,
    is_fallback: bool,
) -> None:
    """Atomically save a worker report, prediction, and active status.

    All three writes use the same database connection and transaction.
    If any write fails, the entire transaction is rolled back.
    """

    if not is_live():
        return

    params_report = {
        "report_id": report_id,
        "report_text": report_text,
        "source": source,
        "site": site,
        "activity": activity,
        "shift": shift,
        "report_date": created_at.date(),
        "is_contractor": is_contractor,
        "created_at": created_at,
    }

    prediction_params = prediction_row(
        report_id,
        result,
        model_version,
        is_fallback,
    )

    status_params = {
        "report_id": report_id,
        "status": "active",
    }

    import psycopg

    conn = psycopg.connect(get_settings().supabase_db_url)

    try:
        with conn.cursor() as cur:
            cur.execute(INSERT_REPORT, params_report)

            cur.execute(INSERT_PREDICTION, prediction_params)

            cur.execute(
                """
                INSERT INTO report_status (report_id, status, updated_at)
                VALUES (%(report_id)s, %(status)s, now())
                ON CONFLICT (report_id)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
                """,
                status_params,
            )

        conn.commit()

    except Exception:
        conn.rollback()
        log.exception(
            "atomic report write failed for report_id=%s; transaction rolled back",
            report_id,
        )
        raise

    finally:
        conn.close()