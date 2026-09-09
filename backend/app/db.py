"""Database access — plain parameterised SQL against Supabase Postgres.

Supabase is Postgres, so we connect with psycopg over the connection string rather than through
the REST client. That is deliberate: it lets the aggregation execute the exact statements in
`sql/aggregates.sql`, which is the artifact Member 4 has to be able to read aloud, instead of
reimplementing them in a query builder where nobody can check them.

The API runs fine with no database. `is_live()` is false, and every caller falls back to the
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


# ---------------------------------------------------------------------------
# Named statements
# ---------------------------------------------------------------------------
# aggregates.sql marks each statement with `-- name: <id>`. Keeping the SQL in a .sql file
# rather than in Python string literals is what makes it reviewable by the whole team.


@lru_cache
def named_statements() -> dict[str, str]:
    text = AGGREGATES_SQL.read_text(encoding="utf-8")
    blocks = re.split(r"^--\s*name:\s*(\w+)\s*$", text, flags=re.MULTILINE)

    statements: dict[str, str] = {}
    # re.split returns [preamble, name1, body1, name2, body2, ...]
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
    except KeyError:  # pragma: no cover - a typo in a call site, caught the first time it runs
        raise KeyError(f"no statement named {name!r} in {AGGREGATES_SQL.name}") from None


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


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
    """A short-lived connection. No pool: a 22-day prototype at demo traffic does not need one."""
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
    """Run a SELECT and return rows as dicts. Always parameterised — never f-strings."""
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
    """Create the tables and both prediction views. Idempotent — safe to re-run."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        cur.execute(statement("latest_predictions"))
        cur.execute(statement("latest_predictions_by_version"))
    log.info("schema applied")


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

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


def prediction_row(report_id: str, result: Any, model_version: str, is_fallback: bool) -> dict:
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


def insert_prediction(report_id: str, result: Any, model_version: str, is_fallback: bool = False) -> None:
    """Append one prediction.

    Never an UPDATE. The table is append-only by design, so an earlier judgement stays on the
    record and "every judgement is logged and reviewable" is structural, not a promise.
    """
    if not is_live():
        return
    execute(INSERT_PREDICTION, prediction_row(report_id, result, model_version, is_fallback))
