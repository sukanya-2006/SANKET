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

Source = Literal["synthetic", "osha"]
Shift = Literal["day", "night"]


class ReportSummary(BaseModel):
    report_id: str
    report_text: str
    source: Source
    site: str | None = None
    activity: str | None = None
    shift: Shift | None = None
    report_date: date
    is_contractor: bool | None = None
    is_sif_precursor: bool | None = None
    severity: int | None = None
    lsr_rule: LSRRule | None = None
    control_status: ControlStatus | None = None
    confidence: float | None = None


class ReportDetail(ReportSummary):
    created_at: datetime
    classified_at: datetime | None = None
    model_version: str | None = None
    result: ClassificationResult | None = None


class ReportPage(BaseModel):
    items: list[ReportSummary]
    total: int
    limit: int
    offset: int


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
    top_rule: str


class ActivityAggregate(BaseModel):
    activity: str
    report_count: int
    precursor_count: int
    precursor_rate: float = Field(ge=0.0, le=1.0)
    top_rule: str


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
