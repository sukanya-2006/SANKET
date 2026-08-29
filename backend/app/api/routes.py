"""Phase 1 stub API.

Every endpoint returns the real response shape backed by fake data, so Member 5 can build
all three screens on Day 3. In Phase 3 the bodies get swapped for Supabase + the ML
pipeline; the paths, request models, and response models stay put.
"""

import time

from fastapi import APIRouter, HTTPException, Query

from ..config import get_settings
from ..schemas import (
    BatchClassificationRequest,
    BatchClassificationResponse,
    Classification,
    ClassificationRequest,
    DashboardSummary,
    EnergySource,
    Label,
    LifeSavingRule,
    ReportDetail,
    ReportPage,
)
from ..stub import classify_stub, dashboard_summary, get_report, list_reports

router = APIRouter(prefix="/api/v1")


@router.get("/meta", tags=["meta"], summary="Enum values for frontend dropdowns")
def meta() -> dict:
    settings = get_settings()
    return {
        "labels": [e.value for e in Label],
        "energy_sources": [e.value for e in EnergySource],
        "life_saving_rules": [e.value for e in LifeSavingRule],
        "rubric_version": settings.rubric_version,
        "stub_mode": settings.stub_mode,
    }


@router.post("/classify", response_model=Classification, tags=["classify"])
def classify(payload: ClassificationRequest) -> Classification:
    """Screen 1 — live analyze. Deterministic: same narrative, same result."""
    started = time.perf_counter()
    result = classify_stub(payload.narrative, payload.report_id)
    result.latency_ms = max(1, int((time.perf_counter() - started) * 1000))
    return result


@router.post("/classify/batch", response_model=BatchClassificationResponse, tags=["classify"])
def classify_batch(payload: BatchClassificationRequest) -> BatchClassificationResponse:
    results = [classify_stub(item.narrative, item.report_id) for item in payload.items]
    return BatchClassificationResponse(results=results, count=len(results))


@router.get("/reports", response_model=ReportPage, tags=["reports"])
def reports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    label: Label | None = None,
    energy_source: EnergySource | None = None,
    q: str | None = None,
) -> ReportPage:
    """Screen 2 — report list with the filters the dashboard drills into."""
    items, total = list_reports(
        limit=limit,
        offset=offset,
        label=label.value if label else None,
        energy_source=energy_source.value if energy_source else None,
        q=q,
    )
    return ReportPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/reports/{report_id}", response_model=ReportDetail, tags=["reports"])
def report_detail(report_id: str) -> ReportDetail:
    found = get_report(report_id)
    if found is None:
        raise HTTPException(status_code=404, detail=f"report {report_id} not found")
    return found


@router.get("/dashboard/summary", response_model=DashboardSummary, tags=["dashboard"])
def dashboard() -> DashboardSummary:
    """Screen 3 — aggregate tiles and charts. Phase 3 replaces this with SQL aggregations."""
    return dashboard_summary()
