"""Data access - one seam over "real database" and "seeded stub".

Every read in the API goes through here. When SUPABASE_DB_URL is set the queries in
sql/aggregates.sql run against Postgres; when it is not, the seeded stub answers with the same
shapes. Callers cannot tell, which is what let the frontend be built on day 3.
"""

from __future__ import annotations

import logging

from . import db
from .schemas import ReportDetail, ReportSummary
from .stub import REPORTS as STUB_REPORTS

log = logging.getLogger(__name__)

_SUMMARY_FIELDS = set(ReportSummary.model_fields)

_stub_status_overrides: dict[str, str] = {}

_stub_extra_reports: list[ReportDetail] = []


SELECT_REPORTS = """
SELECT r.report_id, r.report_text, r.source, r.site, r.activity, r.shift,
       r.report_date, r.is_contractor, r.created_at,
       l.is_sif_precursor, l.severity, l.lsr_rule, l.control_status, l.confidence,
       l.model_version, l.classified_at,
       COALESCE(s.status, 'active') AS status
FROM reports r
LEFT JOIN latest_predictions l ON l.report_id = r.report_id
LEFT JOIN report_status s ON s.report_id = r.report_id
"""


def live() -> bool:
    return db.is_live()


def _rows_from_db() -> list[ReportDetail]:
    return [ReportDetail(**row) for row in db.query(SELECT_REPORTS)]


def all_reports() -> list[ReportDetail]:
    if not live():
        combined = STUB_REPORTS + _stub_extra_reports

        if not _stub_status_overrides:
            return combined

        return [
            r.model_copy(
                update={
                    "status": _stub_status_overrides.get(
                        r.report_id,
                        r.status,
                    )
                }
            )
            for r in combined
        ]

    try:
        return _rows_from_db()
    except Exception as exc:  # noqa: BLE001
        log.error(
            "database read failed, serving seeded stub: %s: %s",
            type(exc).__name__,
            exc,
        )
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
    items = all_reports()

    if is_sif_precursor is not None:
        items = [
            r for r in items
            if r.is_sif_precursor is is_sif_precursor
        ]

    if lsr_rule:
        items = [r for r in items if r.lsr_rule == lsr_rule]

    if site:
        items = [r for r in items if r.site == site]

    if source:
        items = [r for r in items if r.source == source]

    if q:
        needle = q.lower()
        items = [
            r for r in items
            if needle in r.report_text.lower()
        ]

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
        ReportSummary(
            **r.model_dump(include=_SUMMARY_FIELDS)
        )
        for r in items[offset : offset + limit]
    ]

    return page, total


def create_report(
    *,
    report_id: str,
    report_text: str,
    source: str,
    site: str | None,
    activity: str | None,
    shift: str | None,
    is_contractor: bool | None,
    created_at,
    result,
    model_version: str,
    is_fallback: bool,
) -> ReportDetail:
    """Persist one worker submission.

    Live database mode:
      reports + prediction + active status are saved in one transaction.

    Stub mode:
      the report is added to the in-memory stub so it appears in the admin queue.
    """

    if live():
        db.save_report_bundle(
            report_id=report_id,
            report_text=report_text,
            source=source,
            site=site,
            activity=activity,
            shift=shift,
            is_contractor=is_contractor,
            created_at=created_at,
            result=result,
            model_version=model_version,
            is_fallback=is_fallback,
        )

        found = get_report(report_id)

        if found is None:
            raise RuntimeError(
                f"report {report_id} was written but could not be re-read"
            )

        return found

    detail = ReportDetail(
        report_id=report_id,
        report_text=report_text,
        source=source,
        site=site,
        activity=activity,
        shift=shift,
        is_contractor=is_contractor,
        report_date=created_at.date(),
        created_at=created_at,
        classified_at=created_at,
        model_version=model_version,
        is_sif_precursor=result.is_sif_precursor,
        severity=result.severity,
        lsr_rule=result.lsr_rule,
        control_status=result.control_status,
        confidence=result.confidence,
        status="active",
        result=result,
    )

    _stub_extra_reports.append(detail)

    return detail


def get_report(report_id: str) -> ReportDetail | None:
    return next(
        (
            r
            for r in all_reports()
            if str(r.report_id) == str(report_id)
        ),
        None,
    )


def update_status(
    report_id: str,
    status: str,
) -> ReportDetail | None:
    found = get_report(report_id)

    if found is None:
        return None

    if live():
        db.set_report_status(report_id, status)
    else:
        _stub_status_overrides[str(report_id)] = status

    return get_report(report_id)


def sites() -> list[str]:
    return sorted(
        {r.site for r in all_reports() if r.site}
    )


def activities() -> list[str]:
    return sorted(
        {r.activity for r in all_reports() if r.activity}
    )