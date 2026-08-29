"""Classification contract shared by the API, the frontend, and the ML pipeline.

PROVISIONAL — Member 2 owns the final strict schema. This version exists so Member 5 can
build against a stable shape from Day 3. Field names here match the gates in docs/rubric.md
v1.0 and the Supabase columns; changing one means changing all three.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Label(str, Enum):
    SIF_PRECURSOR = "SIF_PRECURSOR"
    NOT_SIF = "NOT_SIF"
    UNCLEAR = "UNCLEAR"


class EnergySource(str, Enum):
    GRAVITY = "gravity"
    MOTION = "motion"
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    PRESSURE = "pressure"
    TEMPERATURE = "temperature"
    CHEMICAL = "chemical"
    BIOLOGICAL = "biological"
    RADIATION = "radiation"
    NONE = "none"


class LifeSavingRule(str, Enum):
    """Eight of the nine IOGP Report 459 Life-Saving Rules, per rubric §2 Gate 2.

    "Bypassing Safety Controls" is deliberately excluded: barrier defeat is what Gate 2
    already measures, so carrying it as a hazard category would double-count.
    """

    CONFINED_SPACE = "confined_space"
    DRIVING = "driving"
    ENERGY_ISOLATION = "energy_isolation"
    HOT_WORK = "hot_work"
    LINE_OF_FIRE = "line_of_fire"
    SAFE_MECHANICAL_LIFTING = "safe_mechanical_lifting"
    WORK_AUTHORISATION = "work_authorisation"
    WORKING_AT_HEIGHT = "working_at_height"
    NONE = "none"


class ModelName(str, Enum):
    STUB = "stub"
    CLAUDE = "claude"
    TFIDF = "tfidf"


class Gate(BaseModel):
    """One gate decision. `passed` is null when the narrative cannot support a judgement."""

    passed: bool | None = None
    rationale: str = ""


class Gates(BaseModel):
    gate_1_high_energy: Gate
    gate_2_control_failed: Gate
    gate_3_serious_injury_plausible: Gate


class EvidenceSpan(BaseModel):
    """Character offsets into the narrative, so the UI can highlight in place."""

    text: str
    start: int
    end: int
    gate: Literal[1, 2, 3]


class ClassificationRequest(BaseModel):
    narrative: str = Field(min_length=1, max_length=20_000)
    report_id: str | None = None


class BatchClassificationRequest(BaseModel):
    items: list[ClassificationRequest] = Field(min_length=1, max_length=100)


class Classification(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    report_id: str | None = None
    label: Label
    confidence: float = Field(ge=0.0, le=1.0)
    gates: Gates
    energy_source: EnergySource
    lsr: LifeSavingRule
    rationale: str
    evidence_spans: list[EvidenceSpan] = []

    model_name: ModelName = Field(serialization_alias="model", validation_alias="model")
    model_version: str
    rubric_version: str
    offline_fallback: bool = False
    latency_ms: int
    created_at: datetime


class BatchClassificationResponse(BaseModel):
    results: list[Classification]
    count: int


# ---------------------------------------------------------------------------
# Reports + dashboard (frontend screens 2 and 3)
# ---------------------------------------------------------------------------


class ReportSummary(BaseModel):
    id: str
    source: Literal["osha", "synthetic"]
    narrative: str
    employer: str | None = None
    state: str | None = None
    incident_date: str | None = None
    gold_label: Label | None = None
    predicted_label: Label | None = None
    confidence: float | None = None
    energy_source: EnergySource | None = None
    lsr: LifeSavingRule | None = None


class ReportDetail(ReportSummary):
    naics_code: str | None = None
    city: str | None = None
    body_part: str | None = None
    event_type: str | None = None
    hospitalized: bool | None = None
    amputation: bool | None = None
    classification: Classification | None = None


class ReportPage(BaseModel):
    items: list[ReportSummary]
    total: int
    limit: int
    offset: int


class CountBucket(BaseModel):
    key: str
    count: int


class DashboardSummary(BaseModel):
    total_reports: int
    labeled_reports: int
    precursor_count: int
    precursor_rate: float
    by_label: list[CountBucket]
    by_energy_source: list[CountBucket]
    by_lsr: list[CountBucket]
    by_month: list[CountBucket]
    model_health: "ModelHealth"


class ModelHealth(BaseModel):
    active_model: ModelName
    offline_fallback_active: bool
    f1: float | None = None
    pr_auc: float | None = None
    last_eval_at: datetime | None = None


DashboardSummary.model_rebuild()
