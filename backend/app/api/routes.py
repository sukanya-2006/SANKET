# """API surface — TECH_STACK v2. Paths and field names per NAMES.md.

# Routes are thin on purpose. Classification goes through `classifier.classify`, which owns the
# cache, the timeout, the retry and the fallback; reads go through `repository`, which owns the
# choice between Postgres and the seeded stub. Swapping either out does not touch this file.
# """

# import logging
# from datetime import datetime, timezone

# from fastapi import APIRouter, HTTPException, Query

# from .. import aggregate, classifier, db, repository
# from ..config import get_settings
# from ..schemas import (
#     ActivityAggregateResponse,
#     AggregateSummary,
#     AnalyzeRequest,
#     AnalyzeResponse,
#     ControlStatus,
#     HazardAssessment,
#     LSRRule,
#     ReportDetail,
#     ReportPage,
#     RuleControlBucket,
#     ShiftAggregate,
#     SiteAggregateResponse,
#     TrendPoint,
# )

# log = logging.getLogger(__name__)
# router = APIRouter()


# @router.get("/meta", tags=["meta"], summary="Enums, versions and live model metrics")
# def meta() -> dict:
#     settings = get_settings()
#     return {
#         "hazard_assessment": [e.value for e in HazardAssessment],
#         "control_status": [e.value for e in ControlStatus],
#         "lsr_rule": [e.value for e in LSRRule],
#         "sites": repository.sites(),
#         "activities": repository.activities(),
#         "rubric_version": settings.rubric_version,
#         "prompt_version": settings.prompt_version,
#         "min_group_n": aggregate.MIN_GROUP_N,
#         "database": "connected" if db.is_live() else "not_configured",
#         # Schema-failure and fallback rates as measured numbers, not hopes.
#         "metrics": classifier.metrics(),
#     }


# # ---------------------------------------------------------------------------
# # Screen 1 — live analyse box
# # ---------------------------------------------------------------------------


# @router.post("/analyze", response_model=AnalyzeResponse, tags=["analyze"])
# def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
#     """Classify one free-text report.

#     `is_fallback` is true when the primary classifier failed, timed out, or returned output the
#     schema rejected twice, and the local baseline answered instead. The UI must show that plainly
#     as "degraded mode — keyword baseline" rather than quietly serving a weaker answer.
#     """
#     try:
#         outcome = classifier.classify(payload.report_text)
#     except classifier.ClassificationUnavailable as exc:
#         # Both classifiers are down. Say so; never invent a label.
#         raise HTTPException(status_code=503, detail=f"classification unavailable: {exc}") from exc

#     return AnalyzeResponse(
#         result=outcome.result,
#         model_version=outcome.model_version,
#         is_fallback=outcome.is_fallback,
#         latency_ms=outcome.latency_ms,
#         created_at=datetime.now(timezone.utc),
#     )


# # ---------------------------------------------------------------------------
# # Screen 2 — ranked report queue
# # ---------------------------------------------------------------------------


# @router.get("/reports", response_model=ReportPage, tags=["reports"])
# def reports(
#     limit: int = Query(20, ge=1, le=100),
#     offset: int = Query(0, ge=0),
#     is_sif_precursor: bool | None = None,
#     lsr_rule: LSRRule | None = None,
#     site: str | None = None,
#     source: str | None = None,
#     q: str | None = None,
# ) -> ReportPage:
#     """Precursors first, then severity descending. The ranked order is the product."""
#     items, total = repository.list_reports(
#         limit=limit,
#         offset=offset,
#         is_sif_precursor=is_sif_precursor,
#         lsr_rule=lsr_rule.value if lsr_rule else None,
#         site=site,
#         source=source,
#         q=q,
#     )
#     return ReportPage(items=items, total=total, limit=limit, offset=offset)


# @router.get("/reports/{report_id}", response_model=ReportDetail, tags=["reports"])
# def report_detail(report_id: str) -> ReportDetail:
#     found = repository.get_report(report_id)
#     if found is None:
#         raise HTTPException(status_code=404, detail=f"report {report_id} not found")
#     return found


# # ---------------------------------------------------------------------------
# # Screen 3 — density dashboard
# # ---------------------------------------------------------------------------


# @router.get("/aggregate/summary", response_model=AggregateSummary, tags=["aggregate"])
# def aggregate_summary() -> AggregateSummary:
#     return aggregate.summary()


# @router.get("/aggregate/sites", response_model=SiteAggregateResponse, tags=["aggregate"])
# def aggregate_sites() -> SiteAggregateResponse:
#     """Ranked by precursor_rate DESC then precursor_count DESC.

#     Sites under MIN_GROUP_N reports are in `insufficient_volume` — grey them out, do not hide
#     them. Rate, not raw count, so a site is not punished for reporting diligently.
#     """
#     return aggregate.sites()


# @router.get("/aggregate/activities", response_model=ActivityAggregateResponse, tags=["aggregate"])
# def aggregate_activities() -> ActivityAggregateResponse:
#     return aggregate.activities()


# @router.get("/aggregate/rules", response_model=list[RuleControlBucket], tags=["aggregate"])
# def aggregate_rules() -> list[RuleControlBucket]:
#     return aggregate.rules()


# @router.get("/aggregate/shifts", response_model=list[ShiftAggregate], tags=["aggregate"])
# def aggregate_shifts() -> list[ShiftAggregate]:
#     return aggregate.shifts()


# @router.get("/aggregate/trend", response_model=list[TrendPoint], tags=["aggregate"])
# def aggregate_trend() -> list[TrendPoint]:
#     return aggregate.trend()




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
    RuleControlBucket,
    ShiftAggregate,
    SiteAggregateResponse,
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
        q=q,
    )
    return ReportPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/reports/{report_id}", response_model=ReportDetail, tags=["reports"])
def report_detail(report_id: str) -> ReportDetail:
    found = repository.get_report(report_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"report {report_id} not found")
    return found


@router.patch("/reports/{report_id}/status", response_model=ReportDetail, tags=["reports"])
def update_report_status(report_id: str, payload: StatusUpdateRequest) -> ReportDetail:
    """Screen 2's "Acknowledge & Dispatch" / "Mark as Reviewed & Archive" actions.

    Idempotent — setting the same status twice is a no-op, not an error, so a flaky click or a
    retried request never breaks the queue.
    """
    updated = repository.update_status(report_id, payload.status)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"report {report_id} not found")
    return updated


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