"""Data access — one seam over "real database" and "seeded stub".

Every read in the API goes through here. When `SUPABASE_DB_URL` is set the queries in
`sql/aggregates.sql` run against Postgres; when it is not, the seeded stub answers with the same
shapes. Callers cannot tell, which is what let the frontend be built on day 3.

Both paths are now verified. The live path ran against Supabase on 9 Sep and all six
/aggregate/* endpoints returned real rows; the stub path is the one under automated test,
because the suite has no database. That gap is real and it is where seven bugs hid — see
docs/database-live.md before assuming a passing suite means the live path works.
"""

from __future__ import annotations

import logging

from . import db
from .schemas import ReportDetail, ReportSummary
from .stub import REPORTS as STUB_REPORTS

log = logging.getLogger(__name__)

_SUMMARY_FIELDS = set(ReportSummary.model_fields)

SELECT_REPORTS = """
SELECT r.report_id, r.report_text, r.source, r.site, r.activity, r.shift,
       r.report_date, r.is_contractor, r.created_at,
       l.is_sif_precursor, l.severity, l.lsr_rule, l.control_status, l.confidence,
       l.model_version, l.classified_at
FROM reports r
LEFT JOIN latest_predictions l ON l.report_id = r.report_id
"""


def live() -> bool:
    return db.is_live()


def _rows_from_db() -> list[ReportDetail]:
    return [ReportDetail(**row) for row in db.query(SELECT_REPORTS)]


def all_reports() -> list[ReportDetail]:
    """Every report, for the aggregation to scope down. Falls back to the stub on any DB error.

    A dashboard that shows stub data is recoverable; a dashboard that 500s during a demo is not.
    """
    if not live():
        return STUB_REPORTS
    try:
        return _rows_from_db()
    except Exception as exc:  # noqa: BLE001
        log.error("database read failed, serving seeded stub: %s: %s", type(exc).__name__, exc)
        return STUB_REPORTS


def list_reports(
    limit: int = 20,
    offset: int = 0,
    is_sif_precursor: bool | None = None,
    lsr_rule: str | None = None,
    site: str | None = None,
    source: str | None = None,
    q: str | None = None,
) -> tuple[list[ReportSummary], int]:
    """Screen 2's queue: precursors first, then severity, then most recent.

    Ordering lives here rather than in the frontend so the queue is the same in every client and
    in any export — the ranked order *is* the product.
    """
    items = all_reports()

    if is_sif_precursor is not None:
        items = [r for r in items if r.is_sif_precursor is is_sif_precursor]
    if lsr_rule:
        items = [r for r in items if r.lsr_rule == lsr_rule]
    if site:
        items = [r for r in items if r.site == site]
    if source:
        items = [r for r in items if r.source == source]
    if q:
        needle = q.lower()
        items = [r for r in items if needle in r.report_text.lower()]

    items = sorted(
        items,
        key=lambda r: (
            not bool(r.is_sif_precursor),
            -(r.severity or 0),
            r.report_date,
        ),
    )

    total = len(items)
    page = [
        ReportSummary(**r.model_dump(include=_SUMMARY_FIELDS))
        for r in items[offset : offset + limit]
    ]
    return page, total


def get_report(report_id: str) -> ReportDetail | None:
    return next((r for r in all_reports() if r.report_id == report_id), None)


def sites() -> list[str]:
    return sorted({r.site for r in all_reports() if r.site})


def activities() -> list[str]:
    return sorted({r.activity for r in all_reports() if r.activity})
