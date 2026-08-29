"""Phase 1 stub: deterministic fake classifier + seeded dataset.

Returns the locked schema (master plan §5 / NAMES.md) backed by fake data, so Member 5 can
build all three screens before any model exists. Phase 3 replaces the producer — Member 2's
TF-IDF baseline and Claude classifier — and the response contract does not change.

Deterministic on purpose: the same text always yields the same result, so the UI is stable
across reloads and the demo.

TWO HONESTY WARNINGS, both of which must survive into the pitch:

1. The 30 `osha` rows here are NOT real OSHA Severe Injury Reports. They are placeholders in
   the right shape, with ids prefixed `osha-placeholder-`. Member 3 replaces them with the real
   pull. Never show these on stage as real OSHA text.
2. `median_triage_seconds` in the aggregate summary is computed from synthetic timestamps
   generated here. It is not a measured number and must not be quoted as the before/after
   headline until real timings are recorded.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone

from .api.recommendations import recommended_check_for
from .schemas import (
    ClassificationResult,
    ControlStatus,
    HazardAssessment,
    LSRRule,
    ReportDetail,
    ReportSummary,
)

MODEL_VERSION = "stub-0.1.0"

# --- keyword cues -----------------------------------------------------------------------
# NOT a model. Member 2's TF-IDF baseline replaces this entirely; it exists so the fake
# output tracks the text instead of being noise. Order matters: most specific rule first.

_RULE_CUES: list[tuple[LSRRule, list[str]]] = [
    (LSRRule.CONFINED_SPACE, ["confined space", "vessel entry", "tank entry", "manhole", "gas test"]),
    (LSRRule.HOT_WORK, ["hot work", "welding", "cutting torch", "fire watch", "grinding sparks"]),
    (LSRRule.ENERGY_ISOLATION, ["isolat", "lockout", "de-energ", "energised", "energized", "live circuit", "breaker"]),
    (LSRRule.WORK_AT_HEIGHT, ["scaffold", "at height", "ladder", "derrick", "monkey board", "harness", "guardrail", "fall arrest"]),
    (LSRRule.LIFTING, ["crane", "sling", "rigging", "hoist", "tagline", "lifted"]),
    (LSRRule.LINE_OF_FIRE, ["line of fire", "under the load", "in the path", "pressurised line", "pressurized line"]),
    (LSRRule.DRIVING, ["seatbelt", "light vehicle", "haul road", "approach road", "driven at speed"]),
    (LSRRule.PERMIT_TO_WORK, ["permit"]),
]

# Checked absent -> failed -> present. Absent cues are explicit negations, so they cannot
# appear in barrier-held text; checking them first stops "no attendant was posted" from
# matching the present cue "attendant was posted" as a substring.
_CONTROL_PRESENT_CUES = [
    "functioned as designed", "was clipped to a rated anchor", "arrested the fall",
    "isolation was verified", "permit was valid", "guard was fitted", "was in place and followed",
    "attendant was posted", "fire watch was posted", "held the load",
]
_CONTROL_FAILED_CUES = [
    "failed", "gave way", "did not hold", "parted", "burst", "collapsed", "slipped out of",
]
_CONTROL_ABSENT_CUES = [
    "no lockout", "not isolated", "no guardrail", "not clipped", "no permit", "no gas test",
    "no attendant", "no fire watch", "no taglines", "no exclusion zone", "not wearing a seatbelt",
    "was not removed", "bypass", "removed the guard", "without a permit", "not informed",
]

# Gate 3: potential severity of the hazard if a small realistic thing went differently.
# Independent of whether the control held — a barrier that holds does not shrink the hazard.
_RULE_SEVERITY: dict[LSRRule, int] = {
    LSRRule.CONFINED_SPACE: 5,
    LSRRule.ENERGY_ISOLATION: 4,
    LSRRule.WORK_AT_HEIGHT: 4,
    LSRRule.LIFTING: 4,
    LSRRule.LINE_OF_FIRE: 4,
    LSRRule.HOT_WORK: 4,
    LSRRule.DRIVING: 4,
    LSRRule.PERMIT_TO_WORK: 4,
    LSRRule.NONE: 1,
}

_MIN_WORDS = 8


def _seed(text: str) -> int:
    return int(hashlib.sha256(text.strip().lower().encode()).hexdigest()[:8], 16)


def _first_hit(text: str, terms: list[str]) -> str | None:
    """Return the matched text expanded to whole words.

    Cues like "isolat" are stems so they catch isolated/isolation, but a flagged phrase is
    highlighted verbatim in the UI — "isolat" reads as a bug. Expand to word boundaries.
    """
    low = text.lower()
    for term in terms:
        idx = low.find(term)
        if idx == -1:
            continue
        start, end = idx, idx + len(term)
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "-"):
            start -= 1
        while end < len(text) and (text[end].isalnum() or text[end] in "-"):
            end += 1
        return text[start:end]
    return None


def classify_stub(report_text: str) -> ClassificationResult:
    """Three gates over keyword cues. Returns the locked ClassificationResult."""
    seed = _seed(report_text)
    flagged: list[str] = []

    # Gate 1 — hazard, categorised by Life-Saving Rule
    rule = LSRRule.NONE
    for candidate, terms in _RULE_CUES:
        hit = _first_hit(report_text, terms)
        if hit:
            rule, _ = candidate, flagged.append(hit)
            break

    if len(report_text.split()) < _MIN_WORDS:
        hazard = HazardAssessment.INSUFFICIENT_INFORMATION
    elif rule is not LSRRule.NONE:
        hazard = HazardAssessment.YES
    else:
        hazard = HazardAssessment.NO

    # Gate 2 — control status
    control: ControlStatus | None = None
    if hazard is HazardAssessment.YES:
        if hit := _first_hit(report_text, _CONTROL_ABSENT_CUES):
            control, _ = ControlStatus.ABSENT, flagged.append(hit)
        elif hit := _first_hit(report_text, _CONTROL_FAILED_CUES):
            control, _ = ControlStatus.FAILED, flagged.append(hit)
        elif hit := _first_hit(report_text, _CONTROL_PRESENT_CUES):
            control, _ = ControlStatus.PRESENT, flagged.append(hit)
        else:
            control = ControlStatus.UNCLEAR
    elif hazard is HazardAssessment.INSUFFICIENT_INFORMATION:
        control = ControlStatus.UNCLEAR

    # Gate 3 — plausible variation, expressed as potential severity
    if hazard is HazardAssessment.YES:
        severity = _RULE_SEVERITY[rule]
    elif hazard is HazardAssessment.INSUFFICIENT_INFORMATION:
        severity = 2
    else:
        severity = 1

    is_precursor = (
        hazard is HazardAssessment.YES
        and control in (ControlStatus.ABSENT, ControlStatus.FAILED)
        and severity >= 4
    )

    if hazard is HazardAssessment.INSUFFICIENT_INFORMATION:
        reasoning = "Report text is too short to judge the hazard; routed for human review rather than scored."
        confidence = 0.30 + (seed % 15) / 100
    elif hazard is HazardAssessment.NO:
        reasoning = "No Life-Saving Rule hazard identified in the text, so Gate 1 stops the assessment."
        confidence = 0.62 + (seed % 28) / 100
    elif control is ControlStatus.PRESENT:
        reasoning = (
            f"Hazard present ({rule.value}), but the text states the barrier was in place and functioned. "
            "Gate 2 stops the assessment: a control that held is not a precursor."
        )
        confidence = 0.70 + (seed % 24) / 100
    elif is_precursor:
        reasoning = (
            f"Hazard present ({rule.value}) with the direct control {control.value}; a small realistic "
            f"change in timing or position plausibly yields a severity-{severity} outcome. All three gates pass."
        )
        confidence = 0.71 + (seed % 26) / 100
    else:
        reasoning = (
            f"Hazard present ({rule.value}) with control status {control.value if control else 'unknown'}, "
            f"but potential severity {severity} does not reach the life-altering threshold at Gate 3."
        )
        confidence = 0.64 + (seed % 26) / 100

    return ClassificationResult(
        hazard_assessment=hazard,
        lsr_rule=rule,
        control_status=control,
        severity=severity,
        is_sif_precursor=is_precursor,
        confidence=round(min(confidence, 0.99), 2),
        flagged_phrases=flagged,
        reasoning=reasoning,
        recommended_check=recommended_check_for(rule, is_precursor),
    )


# ---------------------------------------------------------------------------
# Seeded dataset — master plan §6
# ---------------------------------------------------------------------------
# Ten fixed sites, deliberately uneven, so "Rig 4 had eleven this quarter" exists.
# Rig 4 is seeded with 11 energy_isolation precursors, 9 of them on night shift.
# Positive class across the 150 synthetic rows is 33/150 = 22%, inside the plan's 20-25% band.
# Two sites sit under MIN_GROUP_N so the small-denominator guard has something to catch.

_EQUIPMENT = [
    "pump starter panel", "compressor control panel", "conveyor drive housing",
    "wellhead actuator", "gas booster starter", "MCC cubicle", "separator pump breaker",
    "mud pump starter", "crane hoist panel", "heater control panel", "injection pump starter",
    "dosing skid panel", "flare igniter panel", "transfer pump starter",
]
_LOCATIONS = ["north", "east", "west", "south", "upper deck", "lower deck", "cellar"]
_LOADS = ["casing bundle", "pipe rack", "valve skid", "drill collar", "tank section"]
_VESSELS = ["separator vessel", "storage tank", "process drum", "surge vessel"]
_LINES = ["flare line", "produced-water line", "gas header", "condensate line"]
_ROADS = ["Duliajan", "Moran", "Kumchai", "Jorhat"]
_TASKS = ["hydrojetting", "insulation stripping", "valve replacement", "coating repair"]


def _precursor_text(rule: LSRRule, n: int) -> str:
    if rule is LSRRule.ENERGY_ISOLATION:
        return (
            f"Technician opened the {_EQUIPMENT[n % len(_EQUIPMENT)]} to clear a fault. "
            "The circuit was not isolated and no lockout was applied before the cover came off."
        )
    if rule is LSRRule.WORK_AT_HEIGHT:
        return (
            f"Fitter worked from the {_LOCATIONS[n % len(_LOCATIONS)]} scaffold where no guardrail "
            "was fitted, and his harness was not clipped to any anchor."
        )
    if rule is LSRRule.LIFTING:
        return (
            f"The crane lifted a {_LOADS[n % len(_LOADS)]} with no taglines and the load travelled "
            "over the crew; no exclusion zone was set."
        )
    if rule is LSRRule.CONFINED_SPACE:
        return (
            f"Two workers entered the {_VESSELS[n % len(_VESSELS)]} for cleaning. "
            "No gas test was recorded and no attendant was posted at the manhole."
        )
    if rule is LSRRule.HOT_WORK:
        return (
            f"Welding proceeded on the {_LINES[n % len(_LINES)]} with no fire watch posted, "
            "and flammable residue in the area was not removed beforehand."
        )
    if rule is LSRRule.LINE_OF_FIRE:
        return (
            f"Operator stood in the line of fire of a pressurised line while the "
            f"{_LOCATIONS[n % len(_LOCATIONS)]} flange was broken; no exclusion zone was set."
        )
    if rule is LSRRule.DRIVING:
        return (
            f"A light vehicle was driven at speed on the {_ROADS[n % len(_ROADS)]} approach road "
            "and the driver was not wearing a seatbelt."
        )
    return (
        f"Contractor crew began {_TASKS[n % len(_TASKS)]} with no permit raised for the scope, "
        "and the area owner was not informed."
    )


def _barrier_held_text(n: int) -> str:
    """The ambiguous demo case (plan §12.2): hazard real, barrier held, NOT a precursor."""
    return (
        f"Fitter slipped while moving along the {_LOCATIONS[n % len(_LOCATIONS)]} scaffold. "
        "His harness was clipped to a rated anchor and the fall arrest system functioned as designed; "
        "he was recovered to the deck unhurt."
    )


def _low_hazard_text(n: int) -> str:
    return (
        f"During routine inspection a worker reported damaged paint coating on the "
        f"{_LOCATIONS[n % len(_LOCATIONS)]} walkway handrail and requested a touch-up."
    )


def _thin_text(n: int) -> str:
    return f"Issue reported at {_LOCATIONS[n % len(_LOCATIONS)]} area."


# site -> (report_count, precursor_count, rules used for its precursors)
_SITE_PLAN: list[tuple[str, int, int, list[LSRRule]]] = [
    ("Rig 4", 20, 11, [LSRRule.ENERGY_ISOLATION]),
    ("Moran Gas Plant", 18, 6, [LSRRule.HOT_WORK, LSRRule.CONFINED_SPACE]),
    ("Duliajan Field", 24, 6, [LSRRule.WORK_AT_HEIGHT, LSRRule.LIFTING]),
    ("Pipeline Sector 3", 16, 3, [LSRRule.LINE_OF_FIRE, LSRRule.PERMIT_TO_WORK]),
    ("Rig 7", 22, 3, [LSRRule.WORK_AT_HEIGHT, LSRRule.ENERGY_ISOLATION]),
    ("Jorhat Workover", 17, 2, [LSRRule.LIFTING]),
    ("Baghjan Wellpad", 15, 1, [LSRRule.DRIVING]),
    ("Kumchai Drilling", 11, 0, []),
    ("Naharkatiya Depot", 4, 1, [LSRRule.WORK_AT_HEIGHT]),  # under MIN_GROUP_N
    ("Makum Terminal", 3, 0, []),  # under MIN_GROUP_N
]

_ACTIVITY_FOR_RULE: dict[LSRRule, str] = {
    LSRRule.ENERGY_ISOLATION: "maintenance",
    LSRRule.WORK_AT_HEIGHT: "workover",
    LSRRule.LIFTING: "lifting",
    LSRRule.CONFINED_SPACE: "confined_space_entry",
    LSRRule.HOT_WORK: "hot_work",
    LSRRule.LINE_OF_FIRE: "maintenance",
    LSRRule.DRIVING: "transport",
    LSRRule.PERMIT_TO_WORK: "inspection",
    LSRRule.NONE: "inspection",
}

_BASE_DATE = date(2026, 1, 1)


def _build() -> list[ReportDetail]:
    reports: list[ReportDetail] = []
    counter = 0

    for site, n_reports, n_precursors, rules in _SITE_PLAN:
        for i in range(n_reports):
            counter += 1
            report_id = f"syn-{counter:04d}"

            if i < n_precursors:
                rule = rules[i % len(rules)]
                text = _precursor_text(rule, counter)
                activity = _ACTIVITY_FOR_RULE[rule]
                # Rig 4's story: exactly 9 of its 11 precursors fall on night shift.
                if site == "Rig 4":
                    shift = "night" if i < 9 else "day"
                else:
                    shift = "night" if i % 3 == 0 else "day"
            else:
                kind = (i - n_precursors) % 3
                text = (_barrier_held_text, _low_hazard_text, _thin_text)[kind](counter)
                activity = "inspection" if kind else "workover"
                shift = "night" if i % 4 == 0 else "day"

            result = classify_stub(text)
            seed = _seed(text)
            report_date = _BASE_DATE + timedelta(days=(counter * 5) % 180)
            created = datetime(
                report_date.year, report_date.month, report_date.day, 6 + seed % 12,
                seed % 60, tzinfo=timezone.utc,
            )

            reports.append(
                ReportDetail(
                    report_id=report_id,
                    report_text=text,
                    source="synthetic",
                    site=site,
                    activity=activity,
                    shift=shift,  # type: ignore[arg-type]
                    report_date=report_date,
                    is_contractor=bool(seed % 3),
                    is_sif_precursor=result.is_sif_precursor,
                    severity=result.severity,
                    lsr_rule=result.lsr_rule,
                    control_status=result.control_status,
                    confidence=result.confidence,
                    created_at=created,
                    # Triage latency: seconds between report arriving and being classified.
                    classified_at=created + timedelta(seconds=2 + seed % 11),
                    model_version=MODEL_VERSION,
                    result=result,
                )
            )

    # 30 OSHA-shaped placeholders. No site taxonomy, so excluded from every aggregate.
    for i in range(30):
        text = _precursor_text(list(_RULE_SEVERITY)[i % 8], 1000 + i) if i % 3 == 0 else _low_hazard_text(1000 + i)
        result = classify_stub(text)
        seed = _seed(text + str(i))
        report_date = _BASE_DATE + timedelta(days=(i * 7) % 180)
        created = datetime(report_date.year, report_date.month, report_date.day, 9, seed % 60, tzinfo=timezone.utc)
        reports.append(
            ReportDetail(
                report_id=f"osha-placeholder-{i + 1:02d}",
                report_text=text,
                source="osha",
                site=None,
                activity=None,
                shift=None,
                report_date=report_date,
                is_contractor=None,
                is_sif_precursor=result.is_sif_precursor,
                severity=result.severity,
                lsr_rule=result.lsr_rule,
                control_status=result.control_status,
                confidence=result.confidence,
                created_at=created,
                classified_at=created + timedelta(seconds=3 + seed % 9),
                model_version=MODEL_VERSION,
                result=result,
            )
        )

    return reports


REPORTS: list[ReportDetail] = _build()

# Guard the seeded story: if a template edit breaks the demo numbers, fail loudly at import
# rather than silently on stage.
_rig4 = [r for r in REPORTS if r.site == "Rig 4" and r.is_sif_precursor]
assert len(_rig4) == 11, f"Rig 4 should seed 11 precursors, got {len(_rig4)}"
assert all(r.lsr_rule is LSRRule.ENERGY_ISOLATION for r in _rig4), "Rig 4 precursors must be energy_isolation"
assert len([r for r in _rig4 if r.shift == "night"]) == 9, "Rig 4 should seed 9 night-shift precursors"

_syn = [r for r in REPORTS if r.source == "synthetic"]
assert len(_syn) == 150, f"expected 150 synthetic reports, got {len(_syn)}"
_rate = len([r for r in _syn if r.is_sif_precursor]) / len(_syn)
assert 0.20 <= _rate <= 0.25, f"positive class {_rate:.3f} outside the plan's 20-25% band"


def list_reports(
    limit: int = 20,
    offset: int = 0,
    is_sif_precursor: bool | None = None,
    lsr_rule: str | None = None,
    site: str | None = None,
    source: str | None = None,
    q: str | None = None,
) -> tuple[list[ReportSummary], int]:
    items = REPORTS
    if is_sif_precursor is not None:
        items = [r for r in items if r.is_sif_precursor is is_sif_precursor]
    if lsr_rule:
        items = [r for r in items if r.lsr_rule == lsr_rule]
    if site:
        items = [r for r in items if r.site == site]
    if source:
        items = [r for r in items if r.source == source]
    if q:
        needle = q.lower()
        items = [r for r in items if needle in r.report_text.lower()]
    total = len(items)
    fields = set(ReportSummary.model_fields)
    page = [ReportSummary(**r.model_dump(include=fields)) for r in items[offset : offset + limit]]
    return page, total


def get_report(report_id: str) -> ReportDetail | None:
    return next((r for r in REPORTS if r.report_id == report_id), None)
