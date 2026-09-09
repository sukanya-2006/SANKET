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


class ReportStatus(str, Enum):
    """Where a report sits in the human triage queue. Not a model output.

    The classifier never sets this and never reads it. It ranks a reading queue; a person
    decides what to do about an entry. Keeping the two apart is the difference between
    "the system flagged this" and "the system closed this", and only one of those is a
    claim we are willing to make.

    `active` is the absence of a decision, which is why it is the default and why a report
    nobody has touched has no row in report_status_events at all.
    """

    ACTIVE = "active"
    DISPATCHED = "dispatched"
    ARCHIVED = "archived"


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

    # Human triage state. Defaults to active because a report nobody has acted on has no
    # status row, and the queue must render identically whether or not anyone has started.
    status: ReportStatus = ReportStatus.ACTIVE
    status_changed_at: datetime | None = None


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


class StatusUpdateRequest(BaseModel):
    """Body of POST /reports/{report_id}/status."""

    status: ReportStatus

    # Why, in the operator's words. Optional, but it is the field that makes the audit
    # trail worth having - "archived" alone tells a reviewer nothing six weeks later.
    note: str | None = Field(default=None, max_length=2000)

    # Who did it. Free text, because there is no auth in a prototype and recording a name
    # someone typed beats recording nothing. It is NOT an identity claim and nothing
    # downstream should treat it as one.
    actor: str | None = Field(default=None, max_length=120)


class StatusEvent(BaseModel):
    """One triage decision, as stored. The table is append-only, so these accumulate."""

    report_id: str
    status: ReportStatus
    note: str | None = None
    actor: str | None = None
    created_at: datetime


class StatusResponse(BaseModel):
    """What POST /reports/{report_id}/status returns.

    `persisted` is false when the API is running without a database, in which case the
    change is held in memory and dies with the process. The frontend needs to be able to
    tell, because a triage decision that silently evaporates on restart is exactly the
    failure this endpoint exists to remove.
    """

    report_id: str
    status: ReportStatus
    status_changed_at: datetime
    persisted: bool


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

    # Null when the group has no precursors at all - there is no "most common rule among
    # this site's precursors" if it has none. The SQL says so directly: mode() over an empty
    # FILTER returns NULL. The stub used to answer "none" here instead, which is a real
    # LSRRule value meaning "no Life-Saving Rule applies", so a frontend could not tell an
    # empty group from a genuine finding. Both paths now return null and the UI shows a dash.
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
