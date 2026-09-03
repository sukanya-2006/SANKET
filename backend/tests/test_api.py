"""Contract tests — the ten named in TECH_STACK v2 "Testing".

These assert the shape Member 5 builds against, the resilience behaviour Member 6 will be asked
about, and the aggregation rules a judge will probe. They must keep passing after Member 2's
classifiers replace the stub — that is the point of them.

All ten are real. The cache, retry and fallback tests drive the actual machinery in
app/classifier.py by registering deliberately broken classifiers; nothing here is faked.
"""

import pytest
from fastapi.testclient import TestClient

from app import aggregate, classifier, repository
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


@pytest.fixture
def swap_classifiers():
    """Register stand-in classifiers, then restore the real registry."""
    from app import classifier

    original_primary = classifier._primary
    original_baseline = classifier._baseline

    def _swap(primary=None, baseline=None):
        if primary is not None:
            classifier.register_primary(primary)
        if baseline is not None:
            classifier.register_baseline(baseline)

    yield _swap
    classifier.register_primary(original_primary)
    classifier.register_baseline(original_baseline)


def _baseline_stub():
    from app.stub import classify_stub

    def baseline(text):
        return classify_stub(text)

    baseline.version = "tfidf-test"
    return baseline


def test_schema_validation_retries_once_then_falls_back(swap_classifiers):
    """A model returning malformed output must not reach the database.

    Retry once, then degrade to the baseline - and count it, so hallucination becomes a logged
    rate rather than an unbounded risk.
    """
    from app import classifier

    calls = []

    def malformed(text):
        calls.append(text)
        return {"hazard_assessment": "definitely", "severity": 99}

    malformed.version = "claude-test"
    swap_classifiers(primary=malformed, baseline=_baseline_stub())

    outcome = classifier.classify(PRECURSOR_TEXT)

    assert len(calls) == 2, "should attempt once, retry once, then stop"
    assert outcome.is_fallback is True
    assert outcome.model_version == "tfidf-test"
    metrics = classifier.metrics()
    assert metrics["schema_failures"] == 2
    assert metrics["retries"] == 1
    assert metrics["fallbacks"] == 1


def test_valid_output_on_the_retry_is_accepted(swap_classifiers):
    """One bad response should not condemn the call to degraded mode."""
    from app import classifier

    attempts = {"n": 0}

    def flaky(text):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return {"nonsense": True}
        from app.stub import classify_stub

        return classify_stub(text)

    flaky.version = "claude-test"
    swap_classifiers(primary=flaky, baseline=_baseline_stub())

    outcome = classifier.classify(PRECURSOR_TEXT)
    assert attempts["n"] == 2
    assert outcome.is_fallback is False
    assert outcome.model_version == "claude-test"


def test_api_failure_triggers_baseline_fallback_and_sets_is_fallback(swap_classifiers):
    """The resilience answer: the live box keeps working when the API does not."""

    def broken(text):
        raise ConnectionError("API unreachable")

    broken.version = "claude-test"
    swap_classifiers(primary=broken, baseline=_baseline_stub())

    body = client.post("/analyze", json={"report_text": PRECURSOR_TEXT}).json()
    assert body["is_fallback"] is True
    assert body["model_version"] == "tfidf-test"
    assert body["result"]["is_sif_precursor"] is True


def test_timeout_falls_back_rather_than_hanging(swap_classifiers):
    """A wedged connection must not hold the stage hostage."""
    import time

    from app import classifier
    from app.config import get_settings

    def slow(text):
        time.sleep(2)
        return {}

    slow.version = "claude-test"
    swap_classifiers(primary=slow, baseline=_baseline_stub())

    settings = get_settings()
    object.__setattr__(settings, "llm_timeout_seconds", 0.2)
    try:
        started = time.perf_counter()
        outcome = classifier.classify(PRECURSOR_TEXT)
        elapsed = time.perf_counter() - started
    finally:
        object.__setattr__(settings, "llm_timeout_seconds", 10.0)

    assert outcome.is_fallback is True
    assert elapsed < 1.5, "should give up at the timeout, not wait for the slow call"


def test_both_classifiers_down_returns_503_not_a_guess(swap_classifiers):
    """We would rather say nothing than invent a safety judgement."""

    def broken(text):
        raise ConnectionError("down")

    broken.version = "claude-test"

    def also_broken(text):
        raise RuntimeError("also down")

    also_broken.version = "tfidf-test"
    swap_classifiers(primary=broken, baseline=also_broken)

    assert client.post("/analyze", json={"report_text": PRECURSOR_TEXT}).status_code == 503


def test_repeat_report_text_hits_the_cache(swap_classifiers):
    """Keyed on sha256(report_text + prompt_version): reproducible evals, wifi-proof demos."""
    from app import cache, classifier

    calls = []

    def counting(text):
        calls.append(text)
        from app.stub import classify_stub

        return classify_stub(text)

    counting.version = "claude-test"
    swap_classifiers(primary=counting, baseline=_baseline_stub())

    first = classifier.classify(PRECURSOR_TEXT)
    second = classifier.classify(PRECURSOR_TEXT)

    assert len(calls) == 1, "second call must be served from cache"
    assert first.from_cache is False and second.from_cache is True
    assert second.result.is_sif_precursor == first.result.is_sif_precursor
    assert cache.size() == 1


def test_changing_the_prompt_version_invalidates_the_cache():
    """Otherwise an eval quietly mixes answers produced by two different prompts."""
    from app import cache

    assert cache.cache_key(PRECURSOR_TEXT, "v1") != cache.cache_key(PRECURSOR_TEXT, "v2")


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
            model_version=classifier.active_versions()["primary"],
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

    monkeypatch.setattr(repository, "all_reports", lambda: rows)
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
    assert summary["model_version"] == classifier.active_versions()["primary"]
    assert summary["median_triage_seconds"] > 0


# --- Vocabulary drift: Pydantic vs SQL ---------------------------------------------------


def test_sql_schema_uses_the_same_vocabulary_as_the_pydantic_enums():
    """NAMES.md exists because these three copies drifted across three drafts.

    A value added to an enum without being added to the CHECK constraint fails on insert at
    runtime, in Phase 3, probably during the demo. Catch it here instead.
    """
    from app.schemas import ControlStatus, HazardAssessment

    from app.db import SCHEMA_SQL

    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    for enum in (HazardAssessment, ControlStatus, LSRRule):
        for member in enum:
            assert f"'{member.value}'" in sql, f"{member.value} missing from schema.sql"


def test_sql_schema_carries_every_locked_field_name():
    from app.db import SCHEMA_SQL

    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    for field in (
        "hazard_assessment", "lsr_rule", "control_status", "severity", "is_sif_precursor",
        "confidence", "flagged_phrases", "reasoning",
        "site", "activity", "shift", "report_date", "is_contractor", "source",
        "model_version", "is_fallback", "annotator", "rubric_version",
    ):
        assert field in sql, f"locked name {field} missing from schema.sql"


def test_recommended_check_is_not_persisted():
    """It is a static lookup; a stored copy would drift from the checklist we ship."""
    from app.db import SCHEMA_SQL

    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    assert "recommended_check text" not in sql
    assert "recommended_check" in sql  # explained in a comment, not stored


def test_api_runs_without_a_database():
    """Member 5 is never blocked on an instance being awake; the demo survives a sleeping DB."""
    from app import db

    assert db.is_live() is False
    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["database"] == "not_configured"
    assert health["data_source"] == "seeded_stub"


def test_health_names_whichever_classifier_is_actually_registered():
    """/health must not flatter us.

    Nobody should demo the keyword stub believing it is the real classifier, so this reports
    what is registered right now rather than what we hoped would be. The conftest fixture pins
    the stub, so that is what we expect here.
    """
    from app import classifier

    health = client.get("/health").json()
    assert health["primary_classifier"] == classifier.active_versions()["primary"]
    assert health["baseline_classifier"] == classifier.active_versions()["baseline"]
    assert health["primary_classifier"] == "stub-0.1.0"


def test_missing_api_key_degrades_instead_of_killing_the_app(swap_classifiers):
    """A clean clone with no GROQ_API_KEY must still serve a usable answer.

    This is the exact failure a teammate hits on first setup, and the exact failure a judge
    would see if the key expired: the real classifier raises on every call, and the API has to
    answer from the baseline with is_fallback true rather than returning an error.
    """

    def no_key(text):
        raise RuntimeError("The api_key client option must be set")

    no_key.version = "groq-test"
    swap_classifiers(primary=no_key, baseline=_baseline_stub())

    body = client.post("/analyze", json={"report_text": PRECURSOR_TEXT}).json()
    assert body["is_fallback"] is True
    assert body["result"]["is_sif_precursor"] is True
    assert body["model_version"] == "tfidf-test"


def test_meta_exposes_measured_model_health():
    body = client.get("/meta").json()
    assert body["rubric_version"] == "2.1"
    assert set(body["lsr_rule"]) == {r.value for r in LSRRule}
    assert body["sites"] and body["activities"]
    assert "schema_failure_rate" in body["metrics"]
    assert "fallback_rate" in body["metrics"]


def test_every_named_sql_statement_parses():
    """aggregate.py asks for these by name; a typo must fail here, not during the demo."""
    from app import db

    names = set(db.named_statements())
    assert {
        "latest_predictions", "summary", "sites_ranked", "sites_insufficient_volume",
        "activities_ranked", "activities_insufficient_volume", "rules", "shifts", "trend",
    } <= names
    for name in names:
        assert db.statement(name).strip()


def test_queue_puts_precursors_first_then_severity():
    """The ranked order is the product, so it lives in the API, not in the client."""
    items = client.get("/reports", params={"limit": 40}).json()["items"]
    flags = [bool(i["is_sif_precursor"]) for i in items]
    assert flags == sorted(flags, reverse=True), "precursors must lead the queue"
    severities = [i["severity"] for i in items if i["is_sif_precursor"]]
    assert severities == sorted(severities, reverse=True)
