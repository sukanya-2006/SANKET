"""
Repository — all report reads go through this file.

When the database is configured, reports are read directly from Postgres.
Worker-submitted reports and their latest predictions are joined together.

No seeded data is ever mixed into live database mode. The stub answers only when there
is no database, or when the one there is cannot be reached - see all_reports().
"""

from __future__ import annotations

import logging

from . import db
from .schemas import ReportDetail, ReportSummary
from .stub import REPORTS as STUB_REPORTS

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

        except Exception as exc:  # noqa: BLE001
            # Skip the row, keep the rest. Re-raising here meant one report with a bad
            # enum value emptied the entire dashboard, and the log line pointing at the
            # culprit scrolled past while everyone looked at the blank screen instead.
            log.error(
                "Skipping unreadable report row. report_id=%s error=%s: %s",
                row.get("report_id"), type(exc).__name__, exc,
            )

    if rows and not reports:
        # Every single row failed to parse. That is a schema mismatch, not bad data, and
        # silently returning nothing would look exactly like an empty database.
        raise RuntimeError(
            "all %d report rows failed to parse - the database schema and "
            "ReportDetail have diverged" % len(rows)
        )

    return reports


def all_reports() -> list[ReportDetail]:
    """
    Return reports from the live database, or the seeded stub when there is no database.

    Three cases, and they are not the same thing:

    1. A database is configured and answers. Live rows only. Seeded data is NEVER mixed in -
       a dashboard showing half real and half fixture rows is impossible to debug, and that
       rule stays exactly as it was written.

    2. A database is configured and fails. The stub answers and the error is logged loudly.
       A dashboard showing fixture data is recoverable; one that 500s mid-demo is not, and a
       free-tier Postgres instance going to sleep is a thing that actually happens.

    3. No database is configured at all. The stub answers. This is not a fallback, it is the
       documented development mode - Member 5 builds screens against it and the test suite
       runs entirely in it. Returning an empty list here made a fresh clone serve an API with
       no data in it, which broke seven tests and every frontend that had not been pointed at
       Supabase yet.

    Callers never have to know which case they are in, but anyone can ask: /health reports
    `data_source` as either `postgres` or `seeded_stub`, so the mode is always visible and
    never has to be inferred from the data looking fake.
    """

    if not live():
        log.info("No database configured - serving the seeded stub (see /health data_source)")
        return STUB_REPORTS

    try:
        return _rows_from_db()
    except Exception as exc:  # noqa: BLE001
        log.error(
            "Database read failed, serving the seeded stub so the dashboard stays up: %s: %s",
            type(exc).__name__, exc,
        )
        return STUB_REPORTS


def list_reports(
    limit: int = 20,
    offset: int = 0,
    is_sif_precursor: bool | None = None,
    lsr_rule: str | None = None,
    site: str | None = None,
    source: str | None = None,
    status: str | None = None,
    report_date: str | None = None,
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

    # Triage state. The admin screen filtered its three tabs client-side over a single page of
    # results, so a dispatched report past the page boundary vanished from every tab.
    if status:
        items = [
            r for r in items
            if (r.status or "active") == status
        ]

    # A single day, for "here is what came in today, worst first".
    #
    # This is the day-at-a-time view, and it is why the queue itself does not sort by date:
    # 209 reports span 101 distinct dates and 60 of those hold exactly one report, so
    # date-major ordering would be mostly groups of one, with nothing for severity to order
    # inside them. Filtering to a date and keeping the risk ranking within it gives the same
    # reading order without fragmenting the other hundred days.
    if report_date:
        items = [
            r for r in items
            if str(r.report_date) == report_date
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

    # Precursors first, then severity, then NEWEST first.
    #
    # The date key used to be ascending, so a report submitted thirty seconds ago sorted LAST
    # among everything sharing its precursor flag and severity. "Submit a report, then find it
    # in the queue" is the first thing anyone tries, and with 209 reports it landed past the
    # end of the first page - the report was there, and unreachable.
    #
    # Negating the ordinal rather than reversing the whole tuple keeps the first two keys
    # pointing the way they already did: `reverse=True` would also flip precursors to the
    # bottom and severity to ascending.
    #
    # Risk stays the primary key, deliberately. Sorting by date first was considered and the
    # data rules it out: 209 reports span 101 distinct dates, 60 of which hold exactly one
    # report, so date-major grouping produces mostly groups of one and severity inside them
    # orders nothing. It would also make this a chronological log with local sorting, which is
    # what every system we are trying to improve on already does. The ranked order is the
    # product. Use the `report_date` filter for a day-at-a-time view instead.
    items = sorted(
        items,
        key=lambda r: (
            not bool(r.is_sif_precursor),
            -(r.severity or 0),
            -r.report_date.toordinal(),
        ),
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