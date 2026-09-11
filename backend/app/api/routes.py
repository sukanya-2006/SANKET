"""API surface — SANKET.

Routes are intentionally thin:

- Classification goes through classifier.classify()
- Database reads go through repository
- Worker reports are classified and then saved to Postgres
- Predictions are stored separately from reports
"""

from __future__ import annotations

import logging
import traceback
import uuid
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .. import aggregate, classifier, db, repository
from ..api.recommendations import recommended_check_for
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


# ============================================================================
# WORKER REPORT SCHEMA
# ============================================================================

class WorkerReportRequest(BaseModel):
    report_text: str = Field(min_length=1, max_length=20_000)
    site: str = Field(min_length=1)
    activity: str = Field(min_length=1)
    shift: Literal["day", "night"] = "day"
    is_contractor: bool = False


# ============================================================================
# META
# ============================================================================

@router.get(
    "/meta",
    tags=["meta"],
    summary="Enums, versions and live model metrics",
)
def meta() -> dict:

    settings = get_settings()

    return {
        "hazard_assessment": [
            e.value for e in HazardAssessment
        ],
        "control_status": [
            e.value for e in ControlStatus
        ],
        "lsr_rule": [
            e.value for e in LSRRule
        ],
        "sites": repository.sites(),
        "activities": repository.activities(),
        "rubric_version": settings.rubric_version,
        "prompt_version": settings.prompt_version,
        "min_group_n": aggregate.MIN_GROUP_N,
        "database": (
            "connected"
            if db.is_live()
            else "not_configured"
        ),
        "metrics": classifier.metrics(),
    }


# ============================================================================
# SCREEN 1 — ANALYZE REPORT
# ============================================================================

@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    tags=["analyze"],
)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:

    try:
        outcome = classifier.classify(
            payload.report_text
        )

    except classifier.ClassificationUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=f"classification unavailable: {exc}",
        ) from exc

    result = outcome.result.model_copy(
        update={
            "recommended_check": recommended_check_for(
                outcome.result.lsr_rule,
                outcome.result.is_sif_precursor,
            )
        }
    )

    return AnalyzeResponse(
        result=result,
        model_version=outcome.model_version,
        is_fallback=outcome.is_fallback,
        latency_ms=outcome.latency_ms,
        created_at=datetime.now(timezone.utc),
    )


# ============================================================================
# WORKER REPORT
# ============================================================================

@router.post(
    "/reports/worker",
    response_model=AnalyzeResponse,
    tags=["reports"],
    summary="Submit Worker Report",
)
def submit_worker_report(
    payload: WorkerReportRequest,
) -> AnalyzeResponse:

    # ------------------------------------------------------------------------
    # STEP 1 — MAKE SURE DATABASE IS CONFIGURED
    # ------------------------------------------------------------------------

    if not db.is_live():
        raise HTTPException(
            status_code=503,
            detail=(
                "Database is not configured. "
                "Worker reports cannot be saved until "
                "SUPABASE_DB_URL is configured."
            ),
        )

    # ------------------------------------------------------------------------
    # STEP 2 — CLASSIFY
    # ------------------------------------------------------------------------

    try:
        outcome = classifier.classify(
            payload.report_text
        )

    except classifier.ClassificationUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=f"classification unavailable: {exc}",
        ) from exc

    # ------------------------------------------------------------------------
    # STEP 3 — STATIC RECOMMENDED CHECK
    # ------------------------------------------------------------------------

    result = outcome.result.model_copy(
        update={
            "recommended_check": recommended_check_for(
                outcome.result.lsr_rule,
                outcome.result.is_sif_precursor,
            )
        }
    )

    # ------------------------------------------------------------------------
    # STEP 4 — CREATE UNIQUE REPORT ID
    # ------------------------------------------------------------------------

    report_id = f"worker-{uuid.uuid4()}"

    # ------------------------------------------------------------------------
    # STEP 5 — SAVE REPORT + PREDICTION
    # ------------------------------------------------------------------------

    try:

        # --------------------------------------------------------------------
        # Ensure the submitted site exists before inserting the report.
        # --------------------------------------------------------------------

        db.execute(
            """
            INSERT INTO sites (site)
            VALUES (%(site)s)
            ON CONFLICT (site) DO NOTHING
            """,
            {
                "site": payload.site
            },
        )

        # --------------------------------------------------------------------
        # SAVE THE ORIGINAL WORKER REPORT
        # --------------------------------------------------------------------

        insert_report_sql = """
        INSERT INTO reports (
            report_id,
            report_text,
            source,
            site,
            activity,
            shift,
            report_date,
            is_contractor
        )
        VALUES (
            %(report_id)s,
            %(report_text)s,
            %(source)s,
            %(site)s,
            %(activity)s,
            %(shift)s,
            %(report_date)s,
            %(is_contractor)s
        )
        """

        db.execute(
            insert_report_sql,
            {
                "report_id": report_id,
                "report_text": payload.report_text,
                "source": "worker",
                "site": payload.site,
                "activity": payload.activity,
                "shift": payload.shift,
                "report_date": date.today(),
                "is_contractor": payload.is_contractor,
            },
        )

        # --------------------------------------------------------------------
        # SAVE CLASSIFICATION
        # --------------------------------------------------------------------

        db.insert_prediction(
            report_id=report_id,
            result=result,
            model_version=outcome.model_version,
            is_fallback=outcome.is_fallback,
        )

        # --------------------------------------------------------------------
        # CREATE INITIAL STATUS
        # --------------------------------------------------------------------

        db.execute(
            """
            INSERT INTO report_status (
                report_id,
                status
            )
            VALUES (
                %(report_id)s,
                'active'
            )
            ON CONFLICT (report_id)
            DO NOTHING
            """,
            {
                "report_id": report_id
            },
        )

        log.info(
            "Worker report saved successfully: %s",
            report_id,
        )

    except Exception as exc:

        traceback.print_exc()

        log.exception(
            "FAILED TO SAVE WORKER REPORT %s",
            report_id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to save worker report: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    # ------------------------------------------------------------------------
    # STEP 6 — RETURN RESULT TO FRONTEND
    # ------------------------------------------------------------------------

    return AnalyzeResponse(
        result=result,
        model_version=outcome.model_version,
        is_fallback=outcome.is_fallback,
        latency_ms=outcome.latency_ms,
        created_at=datetime.now(timezone.utc),
    )


# ============================================================================
# ADMIN TRIAGE — GET REPORTS
# ============================================================================

@router.get(
    "/reports",
    response_model=ReportPage,
    tags=["reports"],
)
def reports(

    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),

    offset: int = Query(
        0,
        ge=0,
    ),

    is_sif_precursor: bool | None = None,
    lsr_rule: LSRRule | None = None,
    site: str | None = None,
    source: str | None = None,
    q: str | None = None,

) -> ReportPage:

    items, total = repository.list_reports(
        limit=limit,
        offset=offset,
        is_sif_precursor=is_sif_precursor,
        lsr_rule=(
            lsr_rule.value
            if lsr_rule
            else None
        ),
        site=site,
        source=source,
        q=q,
    )

    return ReportPage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ============================================================================
# GET ONE REPORT
# ============================================================================

@router.get(
    "/reports/{report_id}",
    response_model=ReportDetail,
    tags=["reports"],
)
def report_detail(
    report_id: str,
) -> ReportDetail:

    found = repository.get_report(
        report_id
    )

    if found is None:
        raise HTTPException(
            status_code=404,
            detail=f"report {report_id} not found",
        )

    return found


# ============================================================================
# UPDATE REPORT STATUS
#
# active → dispatched → archived
# ============================================================================

@router.patch(
    "/reports/{report_id}/status",
    tags=["reports"],
)
def update_report_status(

    report_id: str,
    payload: StatusUpdateRequest,

) -> dict:

    if not db.is_live():
        raise HTTPException(
            status_code=503,
            detail="Database is not configured.",
        )

    try:

        # First check whether the report exists.

        rows = db.query(
            """
            SELECT report_id
            FROM reports
            WHERE report_id = %(report_id)s
            """,
            {
                "report_id": report_id
            },
        )

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"report {report_id} not found",
            )

        # Insert status if it doesn't exist.
        # Otherwise update it.

        db.execute(
            """
            INSERT INTO report_status (
                report_id,
                status,
                updated_at
            )
            VALUES (
                %(report_id)s,
                %(status)s,
                NOW()
            )
            ON CONFLICT (report_id)
            DO UPDATE SET
                status = EXCLUDED.status,
                updated_at = NOW()
            """,
            {
                "report_id": report_id,
                "status": payload.status,
            },
        )

        return {
            "report_id": report_id,
            "status": payload.status,
            "message": "Report status updated successfully.",
        }

    except HTTPException:
        raise

    except Exception as exc:

        traceback.print_exc()

        log.exception(
            "FAILED TO UPDATE REPORT STATUS %s",
            report_id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to update report status: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc


# ============================================================================
# DASHBOARD — SUMMARY
# ============================================================================

@router.get(
    "/aggregate/summary",
    response_model=AggregateSummary,
    tags=["aggregate"],
)
def aggregate_summary() -> AggregateSummary:

    return aggregate.summary()


# ============================================================================
# DASHBOARD — SITES
# ============================================================================

@router.get(
    "/aggregate/sites",
    response_model=SiteAggregateResponse,
    tags=["aggregate"],
)
def aggregate_sites() -> SiteAggregateResponse:

    return aggregate.sites()


# ============================================================================
# DASHBOARD — ACTIVITIES
# ============================================================================

@router.get(
    "/aggregate/activities",
    response_model=ActivityAggregateResponse,
    tags=["aggregate"],
)
def aggregate_activities() -> ActivityAggregateResponse:

    return aggregate.activities()


# ============================================================================
# DASHBOARD — RULES
# ============================================================================

@router.get(
    "/aggregate/rules",
    response_model=list[RuleControlBucket],
    tags=["aggregate"],
)
def aggregate_rules() -> list[RuleControlBucket]:

    return aggregate.rules()


# ============================================================================
# DASHBOARD — SHIFTS
# ============================================================================

@router.get(
    "/aggregate/shifts",
    response_model=list[ShiftAggregate],
    tags=["aggregate"],
)
def aggregate_shifts() -> list[ShiftAggregate]:

    return aggregate.shifts()


# ============================================================================
# DASHBOARD — TREND
# ============================================================================

@router.get(
    "/aggregate/trend",
    response_model=list[TrendPoint],
    tags=["aggregate"],
)
def aggregate_trend() -> list[TrendPoint]:

    return aggregate.trend()