"""
Repository — all report reads go through this file.

When the database is configured, reports are read directly from Postgres.
Worker-submitted reports and their latest predictions are joined together.

No seeded data is mixed into the live database mode.
"""

from __future__ import annotations

import logging

from . import db
from .schemas import ReportDetail, ReportSummary

log = logging.getLogger(__name__)

_SUMMARY_FIELDS = set(ReportSummary.model_fields)


# ---------------------------------------------------------------------------
# READ REPORTS + THEIR LATEST PREDICTION
# ---------------------------------------------------------------------------

SELECT_REPORTS = """
SELECT
    r.report_id,
    r.report_text,
    r.source,
    r.site,
    r.activity,
    r.shift,
    r.report_date,
    r.is_contractor,
    r.created_at,

    l.is_sif_precursor,
    l.severity,
    l.lsr_rule,
    l.control_status,
    l.confidence,
    l.model_version,
    r.created_at AS classified_at,

    COALESCE(s.status, 'active') AS status

FROM reports r

LEFT JOIN latest_predictions l
    ON l.report_id = r.report_id

LEFT JOIN report_status s
    ON s.report_id = r.report_id

ORDER BY r.created_at DESC
"""


def live() -> bool:
    """Return True when a database connection is configured."""
    return db.is_live()


def _rows_from_db() -> list[ReportDetail]:
    """
    Read all reports from the live database.

    Any database error is logged instead of silently returning fake data.
    """

    rows = db.query(SELECT_REPORTS)

    log.info(
        "Loaded %s reports from database",
        len(rows)
    )

    reports: list[ReportDetail] = []

    for row in rows:
        try:
            reports.append(
                ReportDetail(**row)
            )

        except Exception as exc:
            log.exception(
                "Failed to convert database row to ReportDetail. "
                "report_id=%s error=%s",
                row.get("report_id"),
                exc,
            )
            raise

    return reports


def all_reports() -> list[ReportDetail]:
    """
    Return reports from the live database.

    We deliberately do NOT fall back to seeded reports when a database
    is configured. Mixing live and fake data makes dashboard debugging
    extremely confusing.
    """

    if not live():
        log.warning(
            "Database is not configured. Returning no reports."
        )
        return []

    return _rows_from_db()


def list_reports(
    limit: int = 20,
    offset: int = 0,
    is_sif_precursor: bool | None = None,
    lsr_rule: str | None = None,
    site: str | None = None,
    source: str | None = None,
    q: str | None = None,
) -> tuple[list[ReportSummary], int]:

    items = all_reports()

    # -----------------------------------------------------------------------
    # FILTERS
    # -----------------------------------------------------------------------

    if is_sif_precursor is not None:
        items = [
            r for r in items
            if r.is_sif_precursor is is_sif_precursor
        ]

    if lsr_rule:
        items = [
            r for r in items
            if r.lsr_rule is not None
            and r.lsr_rule.value == lsr_rule
        ]

    if site:
        items = [
            r for r in items
            if r.site == site
        ]

    if source:
        items = [
            r for r in items
            if r.source == source
        ]

    if q:
        needle = q.lower()

        items = [
            r for r in items
            if needle in r.report_text.lower()
        ]

    # -----------------------------------------------------------------------
    # SORT
    #
    # SIF precursors first
    # Then highest severity
    # Then newest report
    # -----------------------------------------------------------------------

    items = sorted(
        items,
        key=lambda r: (
            not bool(r.is_sif_precursor),
            -(r.severity or 0),
            r.report_date,
        ),
        reverse=False,
    )

    total = len(items)

    page_items = items[
        offset: offset + limit
    ]

    page = [
        ReportSummary(
            **report.model_dump(
                include=_SUMMARY_FIELDS
            )
        )
        for report in page_items
    ]

    log.info(
        "Returning %s of %s reports",
        len(page),
        total,
    )

    return page, total


def get_report(
    report_id: str,
) -> ReportDetail | None:

    reports = all_reports()

    for report in reports:

        if str(report.report_id) == str(report_id):

            return report

    return None


def update_status(
    report_id: str,
    status: str,
) -> ReportDetail | None:

    report = get_report(report_id)

    if report is None:
        return None

    if not live():

        log.warning(
            "Cannot update report status because "
            "the database is not configured."
        )

        return None

    db.set_report_status(
        report_id,
        status,
    )

    return get_report(report_id)


def sites() -> list[str]:

    return sorted(
        {
            report.site
            for report in all_reports()
            if report.site
        }
    )


def activities() -> list[str]:

    return sorted(
        {
            report.activity
            for report in all_reports()
            if report.activity
        }
    )