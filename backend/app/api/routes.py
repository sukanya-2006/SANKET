"""API surface — TECH_STACK v2. Paths and field names per NAMES.md.

Routes are thin on purpose. Classification goes through `classifier.classify`, which owns the
cache, the timeout, the retry and the fallback; reads go through `repository`, which owns the
choice between Postgres and the seeded stub. Swapping either out does not touch this file.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from .. import aggregate, classifier, db, repository
from ..config import get_settings
from ..schemas import (
    ActivityAggregateResponse,
    AggregateSummary,
    AnalyzeRequest,
    AnalyzeResponse,
    ControlStatus,
    HazardAssessment,
    LSRRule,
    ReportDetail,
    ReportPage,
    ReportStatus,
    RuleControlBucket,
    ShiftAggregate,
    SiteAggregateResponse,
    StatusEvent,
    StatusResponse,
    StatusUpdateRequest,
    TrendPoint,
)

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/meta", tags=["meta"], summary="Enums, versions and live model metrics")
def meta() -> dict:
    settings = get_settings()
    return {
        "hazard_assessment": [e.value for e in HazardAssessment],
        "control_status": [e.value for e in ControlStatus],
        "lsr_rule": [e.value for e in LSRRule],
        "sites": repository.sites(),
        "activities": repository.activities(),
        "rubric_version": settings.rubric_version,
        "prompt_version": settings.prompt_version,
        "min_group_n": aggregate.MIN_GROUP_N,
        "database": "connected" if db.is_live() else "not_configured",
        # Schema-failure and fallback rates as measured numbers, not hopes.
        "metrics": classifier.metrics(),
    }


# ---------------------------------------------------------------------------
# Screen 1 — live analyse box
# ---------------------------------------------------------------------------


@router.post("/analyze", response_model=AnalyzeResponse, tags=["analyze"])
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    """Classify one free-text report.

    `is_fallback` is true when the primary classifier failed, timed out, or returned output the
    schema rejected twice, and the local baseline answered instead. The UI must show that plainly
    as "degraded mode — keyword baseline" rather than quietly serving a weaker answer.
    """
    try:
        outcome = classifier.classify(payload.report_text)
    except classifier.ClassificationUnavailable as exc:
        # Both classifiers are down. Say so; never invent a label.
        raise HTTPException(status_code=503, detail=f"classification unavailable: {exc}") from exc

    return AnalyzeResponse(
        result=outcome.result,
        model_version=outcome.model_version,
        is_fallback=outcome.is_fallback,
        latency_ms=outcome.latency_ms,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Screen 2 — ranked report queue
# ---------------------------------------------------------------------------


@router.get("/reports", response_model=ReportPage, tags=["reports"])
def reports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_sif_precursor: bool | None = None,
    lsr_rule: LSRRule | None = None,
    site: str | None = None,
    source: str | None = None,
    status: ReportStatus | None = None,
    q: str | None = None,
) -> ReportPage:
    """Precursors first, then severity descending. The ranked order is the product."""
    items, total = repository.list_reports(
        limit=limit,
        offset=offset,
        is_sif_precursor=is_sif_precursor,
        lsr_rule=lsr_rule.value if lsr_rule else None,
        site=site,
        source=source,
        status=status.value if status else None,
        q=q,
    )
    return ReportPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/reports/{report_id}", response_model=ReportDetail, tags=["reports"])
def report_detail(report_id: str) -> ReportDetail:
    found = repository.get_report(report_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"report {report_id} not found")
    return found


@router.post("/reports/{report_id}/status", response_model=StatusResponse,
             tags=["reports"])
def set_report_status(report_id: str, payload: StatusUpdateRequest) -> StatusResponse:
    """Record a triage decision: dispatched, archived, or back to active.

    This is the only endpoint in the API where a human changes something. Everything else
    reads, or asks the model a question. That asymmetry is deliberate - the system ranks a
    reading queue and never closes a report itself.

    The write is an append, not an update. `GET /reports/{report_id}/status` returns the whole
    history, so "who archived this and why" survives, which a mutable status column could not
    answer.

    Check `persisted` in the response. It is false when the API is running without a database,
    in which case the decision is held in memory and dies with the process. Surface that in the
    UI rather than showing a success state - a triage decision that silently reverts overnight
    is the failure this endpoint exists to remove.
    """
    if repository.get_report(report_id) is None:
        raise HTTPException(status_code=404, detail=f"report {report_id} not found")

    result = repository.set_status(
        report_id=report_id,
        status=payload.status,
        note=payload.note,
        actor=payload.actor,
    )
    if not result.persisted:
        log.warning("report %s marked %s in memory only - no database configured",
                    report_id, payload.status.value)
    return result


@router.get("/reports/{report_id}/status", response_model=list[StatusEvent],
            tags=["reports"])
def get_report_status_history(report_id: str) -> list[StatusEvent]:
    """Every triage decision made on this report, newest first.

    Empty means nobody has acted on it yet, which is what `status: active` means everywhere
    else. Absence of a decision is not a decision.
    """
    if repository.get_report(report_id) is None:
        raise HTTPException(status_code=404, detail=f"report {report_id} not found")
    return repository.status_history(report_id)


# ---------------------------------------------------------------------------
# Screen 3 — density dashboard
# ---------------------------------------------------------------------------


@router.get("/aggregate/summary", response_model=AggregateSummary, tags=["aggregate"])
def aggregate_summary() -> AggregateSummary:
    return aggregate.summary()


@router.get("/aggregate/sites", response_model=SiteAggregateResponse, tags=["aggregate"])
def aggregate_sites() -> SiteAggregateResponse:
    """Ranked by precursor_rate DESC then precursor_count DESC.

    Sites under MIN_GROUP_N reports are in `insufficient_volume` — grey them out, do not hide
    them. Rate, not raw count, so a site is not punished for reporting diligently.
    """
    return aggregate.sites()


@router.get("/aggregate/activities", response_model=ActivityAggregateResponse, tags=["aggregate"])
def aggregate_activities() -> ActivityAggregateResponse:
    return aggregate.activities()


@router.get("/aggregate/rules", response_model=list[RuleControlBucket], tags=["aggregate"])
def aggregate_rules() -> list[RuleControlBucket]:
    return aggregate.rules()


@router.get("/aggregate/shifts", response_model=list[ShiftAggregate], tags=["aggregate"])
def aggregate_shifts() -> list[ShiftAggregate]:
    return aggregate.shifts()


@router.get("/aggregate/trend", response_model=list[TrendPoint], tags=["aggregate"])
def aggregate_trend() -> list[TrendPoint]:
    return aggregate.trend()
