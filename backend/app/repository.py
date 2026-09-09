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
from datetime import datetime, timezone

from . import db
from .schemas import (
    ReportDetail,
    ReportStatus,
    ReportSummary,
    StatusEvent,
    StatusResponse,
)
from .stub import REPORTS as STUB_REPORTS

log = logging.getLogger(__name__)

_SUMMARY_FIELDS = set(ReportSummary.model_fields)

SELECT_REPORTS = """
SELECT r.report_id, r.report_text, r.source, r.site, r.activity, r.shift,
       r.report_date, r.is_contractor, r.created_at,
       l.is_sif_precursor, l.severity, l.lsr_rule, l.control_status, l.confidence,
       l.model_version, l.classified_at,
       -- A report nobody has triaged has no status row. Absence of a decision is not a
       -- decision, so it defaults here rather than being written into the table up front.
       coalesce(s.status, 'active') AS status,
       s.status_changed_at
FROM reports r
LEFT JOIN latest_predictions l ON l.report_id = r.report_id
LEFT JOIN latest_report_status s ON s.report_id = r.report_id
"""


# Append-only, exactly like predictions. A triage decision is never updated in place: the
# question "who archived this, when, and why" has to survive, and an UPDATE erases it.
INSERT_STATUS_EVENT = """
INSERT INTO report_status_events (report_id, status, note, actor)
VALUES (%(report_id)s, %(status)s, %(note)s, %(actor)s)
RETURNING report_id, status, note, actor, created_at
"""

SELECT_STATUS_HISTORY = """
SELECT report_id, status, note, actor, created_at
FROM report_status_events
WHERE report_id = %(report_id)s
ORDER BY created_at DESC
"""


# In-memory triage state, used only when there is no database behind the API.
#
# Member 5 develops against the seeded stub, and a dashboard whose dispatch buttons do
# nothing is not testable. So the stub path keeps decisions in the process - correct within a
# session, gone on restart. That is a real limitation, not a hidden one: every response
# carries `persisted`, which is false here, so the UI can say so rather than implying a
# durability the stub cannot provide.
_stub_status: dict[str, StatusEvent] = {}


def live() -> bool:
    return db.is_live()


def _rows_from_db() -> list[ReportDetail]:
    return [ReportDetail(**row) for row in db.query(SELECT_REPORTS)]


def _with_stub_status(reports: list[ReportDetail]) -> list[ReportDetail]:
    """Overlay in-memory triage decisions onto the seeded stub.

    Without this the stub path accepts a status change and then keeps reporting `active`,
    which looks exactly like a broken write.
    """
    if not _stub_status:
        return reports
    out = []
    for r in reports:
        event = _stub_status.get(r.report_id)
        if event is None:
            out.append(r)
            continue
        out.append(r.model_copy(update={
            "status": event.status,
            "status_changed_at": event.created_at,
        }))
    return out


def all_reports() -> list[ReportDetail]:
    """Every report, for the aggregation to scope down. Falls back to the stub on any DB error.

    A dashboard that shows stub data is recoverable; a dashboard that 500s during a demo is not.
    """
    if not live():
        return _with_stub_status(STUB_REPORTS)
    try:
        return _rows_from_db()
    except Exception as exc:  # noqa: BLE001
        log.error("database read failed, serving seeded stub: %s: %s", type(exc).__name__, exc)
        return _with_stub_status(STUB_REPORTS)


def list_reports(
    limit: int = 20,
    offset: int = 0,
    is_sif_precursor: bool | None = None,
    lsr_rule: str | None = None,
    site: str | None = None,
    source: str | None = None,
    status: str | None = None,
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
    if status:
        items = [r for r in items if r.status == status]
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


def set_status(
    report_id: str,
    status: ReportStatus,
    note: str | None = None,
    actor: str | None = None,
) -> StatusResponse:
    """Record one triage decision. Appends; never updates.

    Returns `persisted=False` when there is no database, so the caller can tell the operator
    the truth rather than letting a decision quietly evaporate on the next restart.
    """
    if not live():
        event = StatusEvent(
            report_id=report_id,
            status=status,
            note=note,
            actor=actor,
            created_at=datetime.now(timezone.utc),
        )
        _stub_status[report_id] = event
        log.warning(
            "status change for report %s held in memory only - no database configured",
            report_id,
        )
        return StatusResponse(
            report_id=report_id,
            status=status,
            status_changed_at=event.created_at,
            persisted=False,
        )

    row = db.query(INSERT_STATUS_EVENT, {
        "report_id": report_id,
        "status": status.value,
        "note": note,
        "actor": actor,
    })[0]
    return StatusResponse(
        report_id=row["report_id"],
        status=ReportStatus(row["status"]),
        status_changed_at=row["created_at"],
        persisted=True,
    )


def status_history(report_id: str) -> list[StatusEvent]:
    """Every triage decision made on a report, newest first.

    This is the point of the append-only table. "It was dispatched on Tuesday, archived on
    Thursday by someone who left a note saying the crew found nothing" is a question the
    dashboard should be able to answer, and a mutable status column never could.
    """
    if not live():
        event = _stub_status.get(report_id)
        return [event] if event else []
    return [StatusEvent(**row) for row in db.query(SELECT_STATUS_HISTORY,
                                                   {"report_id": report_id})]


def sites() -> list[str]:
    return sorted({r.site for r in all_reports() if r.site})


def activities() -> list[str]:
    return sorted({r.activity for r in all_reports() if r.activity})
