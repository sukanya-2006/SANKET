
"""Locked schema — master plan §5, names per NAMES.md.

Member 2 owns ClassificationResult. Member 4 owns the report, aggregate, and response
wrappers. Nothing here gets renamed without Members 2, 4, and 5 agreeing in one conversation.

Why enums and not `bool | Literal[...]`: Pydantic's lax bool coercion turns that union into a
2am debugging session.
"""

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class HazardAssessment(str, Enum):
    YES = "yes"
    NO = "no"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class ControlStatus(str, Enum):
    ABSENT = "absent"
    FAILED = "failed"
    PRESENT = "present"
    UNCLEAR = "unclear"


class LSRRule(str, Enum):
    """The eight IOGP Life-Saving Rules we tag against, plus `none`.

    "Bypassing Safety Controls" is deliberately excluded: barrier defeat is what
    `control_status` measures, so carrying it here too would double-count.
    """

    ENERGY_ISOLATION = "energy_isolation"
    HOT_WORK = "hot_work"
    CONFINED_SPACE = "confined_space"
    LINE_OF_FIRE = "line_of_fire"
    WORK_AT_HEIGHT = "work_at_height"
    LIFTING = "lifting"
    DRIVING = "driving"
    PERMIT_TO_WORK = "permit_to_work"
    NONE = "none"


class ClassificationResult(BaseModel):
    """Master plan §5. `recommended_check` added by backend patch v1.1 Amendment B."""

    hazard_assessment: HazardAssessment
    lsr_rule: LSRRule
    control_status: ControlStatus | None = None
    severity: int = Field(ge=1, le=5)
    is_sif_precursor: bool
    confidence: float = Field(ge=0.0, le=1.0)
    flagged_phrases: list[str] = []
    reasoning: str

    # Static lookup keyed on lsr_rule — never model output. See api/recommendations.py.
    recommended_check: str | None = None


def derive_precursor(
    hazard_assessment: HazardAssessment | str | None,
    control_status: ControlStatus | str | None,
    severity: float | None,
) -> bool:
    """The rubric v2.2 §6 decision table — the single definition every classifier derives from.

    No classifier sets `is_sif_precursor` itself. schema.sql's `precursor_requires_all_three_gates`
    CHECK recomputes exactly this expression, so a flag reached any other way makes the row
    unstorable — and only the flagged rows, the ones that matter. The baseline used to return a
    true flag beside `control_status = unclear`, which the CHECK reads as false, so every precursor
    it found was rejected on insert.

    Takes enum members or their raw string values: the LLM classifier calls this on parsed JSON,
    before Pydantic has coerced anything.
    """
    hazard = getattr(hazard_assessment, "value", hazard_assessment)
    control = getattr(control_status, "value", control_status)
    return (
        hazard == HazardAssessment.YES.value
        and control in (ControlStatus.ABSENT.value, ControlStatus.FAILED.value)
        and isinstance(severity, (int, float))
        and severity >= 4
    )


class AnalyzeRequest(BaseModel):
    report_text: str = Field(min_length=1, max_length=20_000)


class AnalyzeResponse(BaseModel):
    """What the live-analyse box on screen 1 renders."""

    result: ClassificationResult
    model_version: str
    is_fallback: bool = False
    latency_ms: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Reports — master plan §6 metadata
# ---------------------------------------------------------------------------

Source = Literal["synthetic", "osha", "worker"]
Shift = Literal["day", "night"]
ReportStatus = Literal["active", "dispatched", "archived"]

class WorkerReportRequest(BaseModel):
    report_text: str = Field(min_length=1, max_length=20_000)

    site: str | None = None
    activity: str | None = None
    shift: Shift | None = None
    is_contractor: bool | None = None


class ReportSummary(BaseModel):
    report_id: str
    report_text: str
    source: Source
    site: str | None = None
    activity: str | None = None
    shift: Shift | None = None
    report_date: date
    created_at: datetime | None = None
    is_contractor: bool | None = None
    is_sif_precursor: bool | None = None
    severity: int | None = None
    lsr_rule: LSRRule | None = None
    control_status: ControlStatus | None = None
    confidence: float | None = None
    # Workflow state for screen 2's triage queue. Not part of the classification —
    # this is human action taken on a report, tracked separately in report_status.
    status: ReportStatus = "active"


class ReportDetail(ReportSummary):
    classified_at: datetime | None = None
    model_version: str | None = None
    result: ClassificationResult | None = None


class ReportPage(BaseModel):
    items: list[ReportSummary]
    total: int
    limit: int
    offset: int


class StatusUpdateRequest(BaseModel):
    """Body for PATCH /reports/{report_id}/status. Screen 2's dispatch/archive actions."""

    status: ReportStatus


# ---------------------------------------------------------------------------
# Aggregates — backend patch v1.1 Amendment A
# ---------------------------------------------------------------------------


class AggregateSummary(BaseModel):
    total_reports: int
    precursor_count: int
    precursor_rate: float = Field(ge=0.0, le=1.0)
    insufficient_information_count: int
    avg_confidence: float
    median_triage_seconds: float
    model_version: str
    last_updated: datetime


class SiteAggregate(BaseModel):
    site: str
    report_count: int
    precursor_count: int
    precursor_rate: float = Field(ge=0.0, le=1.0)
    # Null when the group has no precursors at all - there is no most-common-rule among
    # a site's precursors if it has none. The SQL says so directly: mode() over an empty
    # FILTER returns NULL, and a required str made /aggregate/sites 500 on real data.
    top_rule: str | None = None


class ActivityAggregate(BaseModel):
    activity: str
    report_count: int
    precursor_count: int
    precursor_rate: float = Field(ge=0.0, le=1.0)
    top_rule: str | None = None  # see SiteAggregate.top_rule


class SiteAggregateResponse(BaseModel):
    """`ranked` is ordered by precursor_rate DESC, then precursor_count DESC.

    Groups below MIN_GROUP_N are in `insufficient_volume` instead — shown greyed out by the
    frontend, not hidden.
    """

    ranked: list[SiteAggregate]
    insufficient_volume: list[SiteAggregate]
    min_group_n: int


class ActivityAggregateResponse(BaseModel):
    ranked: list[ActivityAggregate]
    insufficient_volume: list[ActivityAggregate]
    min_group_n: int


class RuleControlBucket(BaseModel):
    lsr_rule: LSRRule
    control_status: ControlStatus | None
    count: int


class ShiftAggregate(BaseModel):
    site: str
    shift: Shift
    report_count: int
    precursor_count: int
    precursor_rate: float = Field(ge=0.0, le=1.0)


class TrendPoint(BaseModel):
    month: str  # YYYY-MM
    report_count: int
    precursor_count: int
    precursor_rate: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Worker report submission
# ---------------------------------------------------------------------------

class WorkerReportRequest(BaseModel):
    """A safety report submitted directly by a worker."""

    report_text: str = Field(min_length=1, max_length=20_000)

    site: str
    activity: str
    shift: Shift
    is_contractor: bool | None = None


class WorkerReportResponse(BaseModel):
    """Returned after a worker report has been saved and classified."""

    report_id: str
    result: ClassificationResult
    model_version: str
    is_fallback: bool = False
    latency_ms: int
    created_at: datetime