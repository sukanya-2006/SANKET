"""Rate-based precursor density aggregation — TECH_STACK v2, patch v1.1 Amendment A.

Four rules apply to every aggregate in this module:

1. **Latest prediction per report, current `model_version` only.** Never mix model versions
   inside one aggregate — a rate computed across two models measures neither.
2. **Exclude `source = 'osha'`.** OSHA narratives carry no site taxonomy, so they cannot be
   grouped. This is a stated limitation, not a gap to hide.
3. **Small-denominator guard.** A group with fewer than `MIN_GROUP_N` reports is excluded from
   rate-ranked output and returned in `insufficient_volume` instead. A site with one report and
   one precursor is not "100% risk"; it is noise. The frontend greys these out — never hides them.
4. **Both count and rate, always.** The frontend ranks by rate; the count stays visible so
   nobody mistakes 2 of 6 for a crisis.

Why rate and not raw count: raw counts penalise sites that report diligently, which is the exact
opposite of the incentive a safety system should create — and a judge will ask.

Phase 1 computes these in Python over the seeded dataset. Phase 3 swaps in the plain
parameterised SQL in `sql/aggregates.sql`, one statement per function, each readable aloud in
two sentences. The response models do not change.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from statistics import median

from .schemas import (
    ActivityAggregate,
    ActivityAggregateResponse,
    AggregateSummary,
    ControlStatus,
    HazardAssessment,
    LSRRule,
    RuleControlBucket,
    ShiftAggregate,
    SiteAggregate,
    SiteAggregateResponse,
    TrendPoint,
)
from .stub import MODEL_VERSION, REPORTS, ReportDetail

# Below this many reports, a group's rate is noise rather than signal.
MIN_GROUP_N = 5


def _scope() -> list[ReportDetail]:
    """Rules 1 and 2: current model_version, synthetic only.

    In Phase 3 this becomes the `WHERE p.model_version = %(model_version)s AND r.source
    <> 'osha'` clause plus the latest-prediction-per-report join.
    """
    return [
        r for r in REPORTS if r.source != "osha" and r.model_version == MODEL_VERSION
    ]


def _rate(precursors: int, total: int) -> float:
    return round(precursors / total, 4) if total else 0.0


def _top_rule(rows: list[ReportDetail]) -> str:
    """Most frequent lsr_rule among a group's precursors."""
    rules = [r.lsr_rule.value for r in rows if r.is_sif_precursor and r.lsr_rule]
    if not rules:
        return LSRRule.NONE.value
    return Counter(rules).most_common(1)[0][0]


def summary() -> AggregateSummary:
    rows = _scope()
    total = len(rows)
    precursors = [r for r in rows if r.is_sif_precursor]
    confidences = [r.confidence for r in rows if r.confidence is not None]

    # Triage latency: report received -> report classified. The PS's stated pain is that this
    # takes a month; ours is the same number in seconds.
    latencies = [
        (r.classified_at - r.created_at).total_seconds()
        for r in rows
        if r.classified_at is not None
    ]

    return AggregateSummary(
        total_reports=total,
        precursor_count=len(precursors),
        precursor_rate=_rate(len(precursors), total),
        insufficient_information_count=len(
            [
                r
                for r in rows
                if r.result
                and r.result.hazard_assessment is HazardAssessment.INSUFFICIENT_INFORMATION
            ]
        ),
        avg_confidence=round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
        median_triage_seconds=round(median(latencies), 2) if latencies else 0.0,
        model_version=MODEL_VERSION,
        last_updated=datetime.now(timezone.utc),
    )


def _group(rows: list[ReportDetail], key: str) -> list[tuple[str, list[ReportDetail]]]:
    buckets: dict[str, list[ReportDetail]] = {}
    for row in rows:
        value = getattr(row, key)
        if value is None:
            continue
        buckets.setdefault(value, []).append(row)
    return list(buckets.items())


def _rank(items: list, ) -> list:
    """Rule: precursor_rate DESC, then precursor_count DESC."""
    return sorted(items, key=lambda a: (-a.precursor_rate, -a.precursor_count))


def sites() -> SiteAggregateResponse:
    ranked, small = [], []
    for name, rows in _group(_scope(), "site"):
        precursors = [r for r in rows if r.is_sif_precursor]
        agg = SiteAggregate(
            site=name,
            report_count=len(rows),
            precursor_count=len(precursors),
            precursor_rate=_rate(len(precursors), len(rows)),
            top_rule=_top_rule(rows),
        )
        (ranked if len(rows) >= MIN_GROUP_N else small).append(agg)
    return SiteAggregateResponse(
        ranked=_rank(ranked),
        insufficient_volume=sorted(small, key=lambda a: -a.report_count),
        min_group_n=MIN_GROUP_N,
    )


def activities() -> ActivityAggregateResponse:
    ranked, small = [], []
    for name, rows in _group(_scope(), "activity"):
        precursors = [r for r in rows if r.is_sif_precursor]
        agg = ActivityAggregate(
            activity=name,
            report_count=len(rows),
            precursor_count=len(precursors),
            precursor_rate=_rate(len(precursors), len(rows)),
            top_rule=_top_rule(rows),
        )
        (ranked if len(rows) >= MIN_GROUP_N else small).append(agg)
    return ActivityAggregateResponse(
        ranked=_rank(ranked),
        insufficient_volume=sorted(small, key=lambda a: -a.report_count),
        min_group_n=MIN_GROUP_N,
    )


def rules() -> list[RuleControlBucket]:
    """Counts by lsr_rule x control_status — the barrier-failure view on screen 3."""
    tally: Counter[tuple[LSRRule, ControlStatus | None]] = Counter()
    for row in _scope():
        if row.lsr_rule:
            tally[(row.lsr_rule, row.control_status)] += 1
    return [
        RuleControlBucket(lsr_rule=rule, control_status=status, count=count)
        for (rule, status), count in sorted(tally.items(), key=lambda kv: -kv[1])
    ]


def shifts() -> list[ShiftAggregate]:
    """Site x shift. This is what makes 'nine of them on night shift' a sentence."""
    buckets: dict[tuple[str, str], list[ReportDetail]] = {}
    for row in _scope():
        if row.site and row.shift:
            buckets.setdefault((row.site, row.shift), []).append(row)

    out = []
    for (site, shift), rows in buckets.items():
        precursors = [r for r in rows if r.is_sif_precursor]
        out.append(
            ShiftAggregate(
                site=site,
                shift=shift,  # type: ignore[arg-type]
                report_count=len(rows),
                precursor_count=len(precursors),
                precursor_rate=_rate(len(precursors), len(rows)),
            )
        )
    return sorted(out, key=lambda a: (-a.precursor_count, a.site, a.shift))


def trend() -> list[TrendPoint]:
    """Monthly buckets of report_date, ascending. A display, not a model — no forecasting."""
    buckets: dict[str, list[ReportDetail]] = {}
    for row in _scope():
        buckets.setdefault(row.report_date.strftime("%Y-%m"), []).append(row)

    return [
        TrendPoint(
            month=month,
            report_count=len(rows),
            precursor_count=len([r for r in rows if r.is_sif_precursor]),
            precursor_rate=_rate(len([r for r in rows if r.is_sif_precursor]), len(rows)),
        )
        for month, rows in sorted(buckets.items())
    ]
