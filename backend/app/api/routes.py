"""API surface — TECH_STACK v2. Paths and field names per NAMES.md.

Phase 1 serves the locked schema from the seeded stub. Phase 3 swaps the producers behind
`classify()` and `aggregate.*` for Supabase and the real classifiers; these signatures and
response models do not change.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from .. import aggregate
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
    TrendPoint,
)
from ..stub import MODEL_VERSION, classify_stub, get_report, list_reports

router = APIRouter()


@router.get("/meta", tags=["meta"], summary="Enum values for frontend dropdowns")
def meta() -> dict:
    settings = get_settings()
    return {
        "hazard_assessment": [e.value for e in HazardAssessment],
        "control_status": [e.value for e in ControlStatus],
        "lsr_rule": [e.value for e in LSRRule],
        "model_version": MODEL_VERSION,
        "rubric_version": settings.rubric_version,
        "stub_mode": settings.stub_mode,
        "min_group_n": aggregate.MIN_GROUP_N,
    }


# ---------------------------------------------------------------------------
# Screen 1 — live analyse box
# ---------------------------------------------------------------------------


@router.post("/analyze", response_model=AnalyzeResponse, tags=["analyze"])
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    """Classify one free-text report.

    Phase 4 wires the offline fallback here: on Claude API failure or a 10s timeout the local
    TF-IDF baseline answers and `is_fallback` flips to true, which the UI shows plainly as
    "degraded mode — keyword baseline". The field is in the contract now so the frontend can
    build that banner before the fallback exists.
    """
    started = time.perf_counter()
    result = classify_stub(payload.report_text)
    return AnalyzeResponse(
        result=result,
        model_version=MODEL_VERSION,
        is_fallback=False,
        latency_ms=max(1, int((time.perf_counter() - started) * 1000)),
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
    items, total = list_reports(
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
    found = get_report(report_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"report {report_id} not found")
    return found


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
