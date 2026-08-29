"""Contract tests — the ten named in TECH_STACK v2 "Testing".

These assert the shape Member 5 builds against and the aggregation rules a judge will probe.
They must keep passing after Phase 3 swaps the stub for the real pipeline; that is the point.

Three of the ten cover machinery that does not exist until Phase 3/4 (schema-validation retry,
fallback trigger, cache hit). They are present and explicitly skipped rather than faked, so the
suite never overstates what is built. The pitch may claim a test suite only because it exists.
"""

import pytest
from fastapi.testclient import TestClient

from app import aggregate
from app.main import app
from app.schemas import LSRRule

client = TestClient(app)

PRECURSOR_TEXT = (
    "Technician opened the pump starter panel to clear a fault. The circuit was not isolated "
    "and no lockout was applied before the cover came off."
)
BARRIER_HELD_TEXT = (
    "Fitter slipped while moving along the north scaffold. His harness was clipped to a rated "
    "anchor and the fall arrest system functioned as designed; he was recovered to the deck unhurt."
)
LOW_HAZARD_TEXT = (
    "During routine inspection a worker reported damaged paint coating on the north walkway "
    "handrail and requested a touch-up."
)


# --- 1. /analyze contract ---------------------------------------------------------------


def test_analyze_returns_the_locked_schema():
    r = client.post("/analyze", json={"report_text": PRECURSOR_TEXT})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"result", "model_version", "is_fallback", "latency_ms", "created_at"}
    assert body["is_fallback"] is False

    result = body["result"]
    assert set(result) == {
        "hazard_assessment", "lsr_rule", "control_status", "severity", "is_sif_precursor",
        "confidence", "flagged_phrases", "reasoning", "recommended_check",
    }
    assert result["hazard_assessment"] == "yes"
    assert result["lsr_rule"] == "energy_isolation"
    assert result["control_status"] == "absent"
    assert result["is_sif_precursor"] is True
    assert 1 <= result["severity"] <= 5
    assert 0.0 <= result["confidence"] <= 1.0


def test_flagged_phrases_are_verbatim_substrings():
    """The UI highlights these in place, so they must appear in the submitted text exactly."""
    result = client.post("/analyze", json={"report_text": PRECURSOR_TEXT}).json()["result"]
    assert result["flagged_phrases"]
    for phrase in result["flagged_phrases"]:
        assert phrase in PRECURSOR_TEXT


def test_barrier_held_case_is_not_a_precursor():
    """The ambiguous demo case: hazard real, control held. Gate 2 stops it."""
    result = client.post("/analyze", json={"report_text": BARRIER_HELD_TEXT}).json()["result"]
    assert result["hazard_assessment"] == "yes"
    assert result["control_status"] == "present"
    assert result["is_sif_precursor"] is False


def test_thin_report_is_insufficient_information():
    result = client.post("/analyze", json={"report_text": "Issue reported."}).json()["result"]
    assert result["hazard_assessment"] == "insufficient_information"
    assert result["is_sif_precursor"] is False


# --- 2. 422 on malformed/empty input ----------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [{"report_text": ""}, {}, {"report_text": None}, {"wrong_field": "text"}],
)
def test_malformed_input_is_rejected(payload):
    assert client.post("/analyze", json=payload).status_code == 422


# --- 3, 4, 5. Phase 3/4 machinery -------------------------------------------------------


@pytest.mark.skip(reason="Phase 3: schema-validation retry lands with the Claude classifier")
def test_schema_validation_retries_once_then_falls_back():
    ...


@pytest.mark.skip(reason="Phase 4: offline fallback lands at Stage 4, ~day 7")
def test_api_failure_triggers_tfidf_fallback_and_sets_is_fallback():
    ...


@pytest.mark.skip(reason="Phase 3: SQLite cache keyed on sha256(report_text + prompt_version)")
def test_repeat_report_text_hits_the_cache():
    ...


# --- 6. Rate correctness ----------------------------------------------------------------


@pytest.fixture
def fixture_reports(monkeypatch):
    """Four sites: 8/4, 10/2, 4/2 and 3/0 reports/precursors, plus one OSHA row."""
    from datetime import date, datetime, timedelta, timezone

    from app.schemas import ReportDetail

    def row(idx, site, precursor, source="synthetic", month=1, shift="day"):
        created = datetime(2026, month, 5, 8, 0, tzinfo=timezone.utc)
        return ReportDetail(
            report_id=f"fx-{idx:03d}",
            report_text=PRECURSOR_TEXT if precursor else LOW_HAZARD_TEXT,
            source=source,
            site=site,
            activity="maintenance",
            shift=shift,
            report_date=date(2026, month, 5),
            is_contractor=False,
            is_sif_precursor=precursor,
            severity=4 if precursor else 1,
            lsr_rule=LSRRule.ENERGY_ISOLATION if precursor else LSRRule.NONE,
            control_status=None,
            confidence=0.8,
            created_at=created,
            classified_at=created + timedelta(seconds=4),
            model_version=aggregate.MODEL_VERSION,
            result=None,
        )

    rows = []
    n = 0
    for site, total, precursors in [("Big A", 8, 4), ("Big B", 10, 2), ("Small C", 4, 2), ("Small D", 3, 0)]:
        for i in range(total):
            n += 1
            rows.append(row(n, site, i < precursors))
    # Second month, so trend bucketing has two rows.
    n += 1
    rows.append(row(n, "Big A", True, month=2))
    # OSHA row: no site taxonomy, must never reach an aggregate.
    n += 1
    rows.append(row(n, None, True, source="osha"))

    monkeypatch.setattr(aggregate, "REPORTS", rows)
    return rows


def test_rate_is_precursors_over_reports_for_that_group(fixture_reports):
    body = aggregate.sites()
    ranked = {s.site: s for s in body.ranked}
    small = {s.site: s for s in body.insufficient_volume}

    # 4 reports / 2 precursors = 0.5, per patch Amendment C.
    assert small["Small C"].report_count == 4
    assert small["Small C"].precursor_count == 2
    assert small["Small C"].precursor_rate == 0.5

    # Rate ranks above count: Big A (5/9) outranks Big B (2/10) despite similar volume.
    assert [s.site for s in body.ranked] == ["Big A", "Big B"]
    assert ranked["Big A"].precursor_count == 5
    assert ranked["Big B"].precursor_rate == 0.2


def test_both_count_and_rate_are_always_returned(fixture_reports):
    for group in aggregate.sites().ranked + aggregate.sites().insufficient_volume:
        assert group.report_count > 0
        assert group.precursor_count >= 0
        assert 0.0 <= group.precursor_rate <= 1.0


# --- 7. Small-denominator guard ---------------------------------------------------------


def test_groups_under_min_group_n_are_set_aside_not_hidden(fixture_reports):
    body = aggregate.sites()
    assert body.min_group_n == aggregate.MIN_GROUP_N == 5

    ranked = [s.site for s in body.ranked]
    small = [s.site for s in body.insufficient_volume]

    assert "Small D" in small and "Small D" not in ranked  # 3 reports
    assert "Small C" in small and "Small C" not in ranked  # 4 reports
    assert set(ranked) == {"Big A", "Big B"}
    # Set aside, never dropped: every site still appears somewhere.
    assert set(ranked) | set(small) == {"Big A", "Big B", "Small C", "Small D"}


# --- 8. Trend bucketing -----------------------------------------------------------------


def test_trend_buckets_by_month_ascending(fixture_reports):
    points = aggregate.trend()
    assert [p.month for p in points] == ["2026-01", "2026-02"]
    assert points[0].report_count == 25
    assert points[0].precursor_count == 8
    assert points[1].report_count == 1
    assert points[1].precursor_count == 1
    assert points[1].precursor_rate == 1.0


# --- 9. OSHA exclusion ------------------------------------------------------------------


def test_osha_rows_never_appear_in_any_aggregate(fixture_reports):
    """OSHA narratives carry no site taxonomy. Stated limitation, enforced here."""
    assert sum(s.report_count for s in aggregate.sites().ranked) == 19  # Big A 9 + Big B 10
    assert sum(s.report_count for s in aggregate.sites().insufficient_volume) == 7
    assert aggregate.summary().total_reports == 26  # 25 + 1 second-month row, no OSHA
    assert sum(p.report_count for p in aggregate.trend()) == 26
    assert sum(b.count for b in aggregate.rules()) == 26
    assert sum(s.report_count for s in aggregate.shifts()) == 26


def test_osha_reports_are_still_listable_just_not_aggregated():
    page = client.get("/reports", params={"source": "osha", "limit": 1}).json()
    assert page["total"] == 30
    assert page["items"][0]["site"] is None


# --- 10. recommended_check behaviour ----------------------------------------------------


def test_recommended_check_is_present_on_precursors_only():
    precursor = client.post("/analyze", json={"report_text": PRECURSOR_TEXT}).json()["result"]
    assert precursor["recommended_check"] is not None

    for text in (BARRIER_HELD_TEXT, LOW_HAZARD_TEXT):
        result = client.post("/analyze", json={"report_text": text}).json()["result"]
        assert result["is_sif_precursor"] is False
        assert result["recommended_check"] is None


def test_recommended_check_never_varies_for_the_same_rule():
    """It is a lookup table, not model output — same rule, same string, every time."""
    from app.api.recommendations import RECOMMENDED_CHECKS, recommended_check_for

    texts = [
        PRECURSOR_TEXT,
        "Fitter opened the MCC cubicle. The circuit was not isolated and no lockout was applied.",
        "Crew worked on the separator pump breaker; it was not isolated and no lockout was applied.",
    ]
    seen = set()
    for text in texts:
        result = client.post("/analyze", json={"report_text": text}).json()["result"]
        assert result["lsr_rule"] == "energy_isolation"
        seen.add(result["recommended_check"])
    assert len(seen) == 1
    assert seen.pop() == RECOMMENDED_CHECKS[LSRRule.ENERGY_ISOLATION]
    assert recommended_check_for(LSRRule.ENERGY_ISOLATION, False) is None


# --- Seeded-dataset guarantees the demo depends on --------------------------------------


def test_seeded_dataset_matches_the_plan():
    page = client.get("/reports", params={"limit": 1}).json()
    assert page["total"] == 180  # 150 synthetic + 30 OSHA

    synthetic = client.get("/reports", params={"source": "synthetic", "limit": 1}).json()
    assert synthetic["total"] == 150


def test_rig_4_is_the_seeded_density_winner():
    """Backend patch acceptance: highest-density site ranks first BY RATE, counts visible."""
    body = client.get("/aggregate/sites").json()
    top = body["ranked"][0]
    assert top["site"] == "Rig 4"
    assert top["precursor_count"] == 11
    assert top["top_rule"] == "energy_isolation"
    assert top["precursor_rate"] == max(s["precursor_rate"] for s in body["ranked"])
    assert [s["site"] for s in body["insufficient_volume"]] == ["Naharkatiya Depot", "Makum Terminal"]


def test_shift_split_behind_the_demo_sentence():
    """'Eleven at Rig 4 this quarter, nine of them on night shift.'"""
    rows = client.get("/aggregate/shifts").json()
    night = next(r for r in rows if r["site"] == "Rig 4" and r["shift"] == "night")
    assert night["precursor_count"] == 9


def test_positive_class_stays_in_the_20_to_25_percent_band():
    """Plan §6: never rebalance to 50/50 — it flatters every model."""
    summary = client.get("/aggregate/summary").json()
    assert 0.20 <= summary["precursor_rate"] <= 0.25
    assert summary["model_version"] == aggregate.MODEL_VERSION
    assert summary["median_triage_seconds"] > 0
