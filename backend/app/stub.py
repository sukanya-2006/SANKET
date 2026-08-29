"""Deterministic fake classifier + fake dataset.

Phase 1 only. Returns the exact shape the real pipeline will return so Member 5 can build
all three screens before any model exists. Replaced in Phase 3 by Member 2's TF-IDF
baseline and Claude classifier — the response contract does not change, only the producer.

Deterministic on purpose: the same narrative always yields the same result, so the UI is
stable across reloads and demos.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from .schemas import (
    Classification,
    CountBucket,
    DashboardSummary,
    EnergySource,
    EvidenceSpan,
    Gate,
    Gates,
    Label,
    LifeSavingRule,
    ModelHealth,
    ModelName,
    ReportDetail,
    ReportSummary,
)

MODEL_VERSION = "stub-0.1.0"

# Keyword cues, so the fake output tracks the narrative instead of being noise.
# NOT a model — Member 2's TF-IDF baseline replaces this entirely.
_ENERGY_CUES: list[tuple[EnergySource, list[str]]] = [
    (EnergySource.ELECTRICAL, ["volt", "electric", "arc flash", "energized", "power line", "panel"]),
    (EnergySource.MECHANICAL, ["conveyor", "auger", "press", "rotating", "pinch point", "guard", "machine"]),
    (EnergySource.GRAVITY, ["fell", "fall", "scaffold", "ladder", "roof", "trench", "collapse", "struck by falling"]),
    (EnergySource.MOTION, ["forklift", "vehicle", "truck", "backed over", "struck by", "crane", "load swung"]),
    (EnergySource.PRESSURE, ["pressure", "hydraulic", "steam", "compressed", "hose burst", "vessel"]),
    (EnergySource.TEMPERATURE, ["burn", "molten", "hot", "flame", "fire", "scald", "cryogenic"]),
    (EnergySource.CHEMICAL, ["chemical", "acid", "caustic", "toxic", "fumes", "asphyxi", "oxygen deficient"]),
    (EnergySource.RADIATION, ["radiograph", "laser", "radiation"]),
    (EnergySource.BIOLOGICAL, ["pathogen", "biological", "infectious"]),
]

_CONTROL_FAILURE_CUES: list[tuple[LifeSavingRule, list[str]]] = [
    (LifeSavingRule.ENERGY_ISOLATION, ["lockout", "loto", "not de-energized", "still running", "not isolated"]),
    (LifeSavingRule.WORKING_AT_HEIGHT, ["no guardrail", "without harness", "not tied off", "unprotected edge", "no fall protection"]),
    (LifeSavingRule.SAFE_MECHANICAL_LIFTING, ["load overhead", "tagline", "rigging", "sling", "unrated"]),
    (LifeSavingRule.LINE_OF_FIRE, ["line of fire", "in the path", "under the load", "struck by"]),
    (LifeSavingRule.CONFINED_SPACE, ["confined space", "manhole", "tank entry", "no gas test"]),
    (LifeSavingRule.HOT_WORK, ["hot work", "welding", "cutting torch", "no fire watch"]),
    (LifeSavingRule.DRIVING, ["seatbelt", "speeding", "driving", "distracted"]),
    (LifeSavingRule.WORK_AUTHORISATION, ["no permit", "without a permit", "unauthorized"]),
]

# Barrier defeat: fails Gate 2 but maps to no LSR category (see LifeSavingRule docstring).
_CONTROL_DEFEAT_CUES = ["bypass", "removed the guard", "guard was removed", "disabled", "interlock", "defeated"]

_SEVERITY_CUES = ["amputat", "fatal", "died", "hospitaliz", "hospitalis", "fracture", "burn", "crush", "unconscious"]


def _seed(text: str) -> int:
    return int(hashlib.sha256(text.strip().lower().encode()).hexdigest()[:8], 16)


def _find(narrative: str, terms: list[str]) -> tuple[str, int, int] | None:
    low = narrative.lower()
    for term in terms:
        idx = low.find(term)
        if idx != -1:
            end = min(len(narrative), idx + len(term))
            return narrative[idx:end], idx, end
    return None


def classify_stub(narrative: str, report_id: str | None = None) -> Classification:
    seed = _seed(narrative)
    spans: list[EvidenceSpan] = []

    # Gate 1 — high energy present
    energy = EnergySource.NONE
    g1_reason = "No high-energy source named in the narrative."
    for source, terms in _ENERGY_CUES:
        hit = _find(narrative, terms)
        if hit:
            energy = source
            text, start, end = hit
            spans.append(EvidenceSpan(text=text, start=start, end=end, gate=1))
            g1_reason = f"Narrative indicates {source.value} energy ({text!r})."
            break
    g1 = energy is not EnergySource.NONE

    # Gate 2 — direct control absent, ineffective, or bypassed
    lsr = LifeSavingRule.NONE
    g2_reason = "No explicit control failure identified."
    for rule, terms in _CONTROL_FAILURE_CUES:
        hit = _find(narrative, terms)
        if hit:
            lsr = rule
            text, start, end = hit
            spans.append(EvidenceSpan(text=text, start=start, end=end, gate=2))
            g2_reason = f"Suggests a breach of the {rule.value.replace('_', ' ')} rule ({text!r})."
            break
    defeat = _find(narrative, _CONTROL_DEFEAT_CUES)
    if defeat and lsr is LifeSavingRule.NONE:
        text, start, end = defeat
        spans.append(EvidenceSpan(text=text, start=start, end=end, gate=2))
        g2_reason = f"Barrier defeated or disabled ({text!r})."

    # Rubric §4.2: a high-energy event that reached a person implies the control did not hold.
    g2 = lsr is not LifeSavingRule.NONE or defeat is not None or (g1 and seed % 5 != 0)
    if g2 and lsr is LifeSavingRule.NONE:
        g2_reason = "High-energy contact occurred; no functioning direct control evidenced (rubric §4.2)."

    # Gate 3 — serious injury plausible
    sev = _find(narrative, _SEVERITY_CUES)
    if sev:
        text, start, end = sev
        spans.append(EvidenceSpan(text=text, start=start, end=end, gate=3))
        g3, g3_reason = True, f"Actual outcome severity ({text!r}) satisfies Gate 3 by default."
    elif g1:
        g3, g3_reason = True, "A small shift in position or timing plausibly yields a life-altering injury."
    else:
        g3, g3_reason = False, "No plausible pathway to a life-altering injury."

    too_thin = len(narrative.split()) < 8
    if too_thin:
        label = Label.UNCLEAR
        confidence = 0.30 + (seed % 15) / 100
        rationale = "Narrative too thin to judge the gates (rubric §3)."
    elif g1 and g2 and g3:
        label = Label.SIF_PRECURSOR
        confidence = 0.72 + (seed % 25) / 100
        rationale = "All three gates pass: high energy present, direct control failed, serious injury plausible."
    else:
        label = Label.NOT_SIF
        confidence = 0.65 + (seed % 30) / 100
        failed = "Gate 1" if not g1 else ("Gate 2" if not g2 else "Gate 3")
        rationale = f"{failed} does not pass, so the report is not a SIF precursor."

    return Classification(
        report_id=report_id,
        label=label,
        confidence=round(min(confidence, 0.99), 2),
        gates=Gates(
            gate_1_high_energy=Gate(passed=None if too_thin else g1, rationale=g1_reason),
            gate_2_control_failed=Gate(passed=None if too_thin else g2, rationale=g2_reason),
            gate_3_serious_injury_plausible=Gate(passed=None if too_thin else g3, rationale=g3_reason),
        ),
        energy_source=energy,
        lsr=lsr,
        rationale=rationale,
        evidence_spans=spans,
        model=ModelName.STUB,
        model_version=MODEL_VERSION,
        rubric_version="1.0",
        offline_fallback=False,
        latency_ms=40 + seed % 260,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Fake dataset for screens 2 and 3
# ---------------------------------------------------------------------------

_NARRATIVES: list[tuple[str, str, str, str, str]] = [
    ("osha", "Employee was working on a scaffold approximately 5 meters above grade with no guardrail installed. He stepped backward and fell to the concrete below, fracturing his pelvis.", "Apex Construction LLC", "TX", "2025-01-14"),
    ("osha", "While clearing a jam, the employee reached into the conveyor which was still running. Lockout was not applied. His sleeve was caught in the pinch point and his index finger was amputated.", "Midland Foods Inc", "OH", "2025-01-22"),
    ("osha", "Employee slipped on a wet floor in the break room and fractured his wrist.", "Northline Logistics", "IL", "2025-02-03"),
    ("osha", "An electrician opened a 480 volt panel to troubleshoot without de-energizing. An arc flash occurred, causing second degree burns to the face and hands.", "Grid Services Co", "PA", "2025-02-11"),
    ("synthetic", "During a lift, the crane load swung over the crew because taglines were not used. The load was set down without contact and no one was injured.", "Harbor Steel Erectors", "WA", "2025-02-19"),
    ("osha", "Employee was lifting a 20 kg box from a pallet and strained his lower back. He was hospitalized overnight for observation.", "Central Warehouse Group", "GA", "2025-03-02"),
    ("osha", "Worker was in a 2.5 meter trench with no protective system in place when the wall sloughed in, burying him to the waist. He was freed by coworkers.", "Rivera Excavation", "AZ", "2025-03-08"),
    ("synthetic", "A forklift operator reversed without a spotter in a congested aisle and struck a pedestrian worker, fracturing the worker's leg.", "Summit Distribution", "NC", "2025-03-15"),
    ("osha", "Employee was injured at the facility and was taken to the hospital.", "Unnamed Employer", "FL", "2025-03-21"),
    ("synthetic", "During hot work on a tank, no fire watch was posted and no gas test was performed. Vapors ignited, causing a flash fire; the welder sustained burns to both arms.", "Delta Fabrication", "LA", "2025-04-02"),
    ("osha", "Worker fell 4 meters from structural steel. His harness and lanyard arrested the fall at a rated anchor point and he was not injured.", "Ironclad Erectors", "MO", "2025-04-09"),
    ("synthetic", "A hydraulic hose under pressure burst during maintenance because the system was not depressurized first, spraying fluid and injuring the technician's eye.", "Precision Hydraulics", "MI", "2025-04-17"),
    ("osha", "Employee struck his thumb with a hammer while framing and sustained a fracture.", "Homefront Builders", "CO", "2025-04-24"),
    ("synthetic", "A maintenance technician bypassed the interlock on a robotic cell to observe a fault and entered while the arm was live. The arm cycled and pinned him against the fence.", "Nova Automation", "IN", "2025-05-06"),
    ("osha", "A driver failed to wear a seatbelt and was ejected during a rollover on a haul road. He sustained spinal injuries.", "Redrock Mining Services", "NV", "2025-05-13"),
]


def _report_id(i: int) -> str:
    return f"stub-{i + 1:04d}"


def _build_reports() -> list[ReportDetail]:
    reports: list[ReportDetail] = []
    for i, (source, narrative, employer, state, date) in enumerate(_NARRATIVES):
        result = classify_stub(narrative, report_id=_report_id(i))
        seed = _seed(narrative)
        reports.append(
            ReportDetail(
                id=_report_id(i),
                source=source,  # type: ignore[arg-type]
                narrative=narrative,
                employer=employer,
                state=state,
                city=None,
                incident_date=date,
                naics_code=str(230000 + seed % 9000),
                # Gold labels agree with the stub here; real gold arrives from Phase 2 labeling.
                gold_label=Label(result.label),
                predicted_label=Label(result.label),
                confidence=result.confidence,
                energy_source=EnergySource(result.energy_source),
                lsr=LifeSavingRule(result.lsr),
                hospitalized=bool(seed % 2),
                amputation="amputat" in narrative.lower(),
                body_part=None,
                event_type=None,
                classification=result,
            )
        )
    return reports


REPORTS: list[ReportDetail] = _build_reports()


def list_reports(
    limit: int = 20,
    offset: int = 0,
    label: str | None = None,
    energy_source: str | None = None,
    q: str | None = None,
) -> tuple[list[ReportSummary], int]:
    items = REPORTS
    if label:
        items = [r for r in items if r.predicted_label == label]
    if energy_source:
        items = [r for r in items if r.energy_source == energy_source]
    if q:
        needle = q.lower()
        items = [r for r in items if needle in r.narrative.lower() or needle in (r.employer or "").lower()]
    total = len(items)
    page = items[offset : offset + limit]
    return [ReportSummary(**r.model_dump(include=set(ReportSummary.model_fields))) for r in page], total


def get_report(report_id: str) -> ReportDetail | None:
    return next((r for r in REPORTS if r.id == report_id), None)


def _counts(values: list[str]) -> list[CountBucket]:
    tally: dict[str, int] = {}
    for v in values:
        tally[v] = tally.get(v, 0) + 1
    return [CountBucket(key=k, count=c) for k, c in sorted(tally.items(), key=lambda kv: -kv[1])]


def dashboard_summary() -> DashboardSummary:
    total = len(REPORTS)
    precursors = [r for r in REPORTS if r.predicted_label == Label.SIF_PRECURSOR.value]
    return DashboardSummary(
        total_reports=total,
        labeled_reports=total,
        precursor_count=len(precursors),
        precursor_rate=round(len(precursors) / total, 3) if total else 0.0,
        by_label=_counts([r.predicted_label.value for r in REPORTS if r.predicted_label]),
        by_energy_source=_counts([r.energy_source.value for r in REPORTS if r.energy_source]),
        by_lsr=_counts([r.lsr.value for r in REPORTS if r.lsr and r.lsr != LifeSavingRule.NONE]),
        by_month=_counts([(r.incident_date or "")[:7] for r in REPORTS if r.incident_date]),
        model_health=ModelHealth(
            active_model=ModelName.STUB,
            offline_fallback_active=False,
            f1=None,
            pr_auc=None,
            last_eval_at=None,
        ),
    )
