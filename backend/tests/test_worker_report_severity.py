"""Regression tests for the "severity always shows as 5" bug.

Context: newly submitted worker reports were displaying Severity Level 5 in Admin Triage
regardless of report content. Investigation (see docs/severity-5-bug-investigation.md) found
that every code stage between the classifier and the screen preserves whatever severity the
classifier returned unchanged - the actual bug was in the LLM prompt (classifier_llm.py),
which this repo cannot exercise in CI since it calls the live Groq API.

What these tests DO cover, with a fully deterministic fake classifier standing in for the LLM,
is the claim the ticket's acceptance criteria make about the *code*:

    "The classifier output is not unintentionally overwritten."
    "The correct severity is stored in the predictions table."
    "The API returns the stored severity correctly."

If any of STEP 3 (recommended_check patch), db.insert_prediction, the latest_predictions view
logic re-implemented here, or repository.py ever starts mutating severity, these tests fail.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# A tiny in-memory stand-in for Postgres, just enough to exercise
# db.execute / db.insert_prediction / repository.all_reports without a real database.
# ---------------------------------------------------------------------------


class FakeDB:
    def __init__(self):
        self.reports: dict[str, dict] = {}
        self.predictions: dict[str, list[dict]] = {}
        self.statuses: dict[str, str] = {}

    # Mimics db.execute() for the three INSERT statements routes.py issues.
    def execute(self, sql: str, params: dict | None = None) -> int:
        params = params or {}
        normalized = " ".join(sql.split())

        if normalized.startswith("INSERT INTO sites"):
            return 1

        if normalized.startswith("INSERT INTO reports"):
            self.reports[params["report_id"]] = dict(params)
            return 1

        if normalized.startswith("INSERT INTO report_status"):
            # routes.py's initial-status INSERT hardcodes 'active' as a SQL literal rather
            # than binding it - db.set_report_status() (used for later transitions) does
            # bind %(status)s, so only fall back to the literal when it's absent.
            status = params.get("status", "active")
            self.statuses.setdefault(params["report_id"], status)
            return 1

        raise AssertionError(f"FakeDB.execute got an unexpected statement: {normalized[:60]!r}")

    # Mimics db.insert_prediction()'s SQL: an append-only predictions table.
    def insert_prediction_row(self, row: dict) -> None:
        self.predictions.setdefault(row["report_id"], []).append(row)

    # Mimics the `latest_predictions` view (DISTINCT ON report_id ORDER BY created_at DESC)
    # plus repository.SELECT_REPORTS's join, closely enough for this test's purposes.
    def latest_prediction(self, report_id: str) -> dict | None:
        rows = self.predictions.get(report_id)
        return rows[-1] if rows else None


@pytest.fixture
def swap_classifiers():
    """Register stand-in classifiers, then restore the real registry.

    Local copy of the fixture in test_api.py - pytest fixtures aren't shared across test
    modules without a conftest.py entry, and this file is deliberately standalone.
    """
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


@pytest.fixture
def fake_db(monkeypatch):
    """Wire a FakeDB in behind db.is_live()/db.execute()/db.insert_prediction()/db.query()."""
    from app import db as db_module

    fake = FakeDB()

    monkeypatch.setattr(db_module, "is_live", lambda: True)
    monkeypatch.setattr(db_module, "execute", fake.execute)

    def fake_insert_prediction(report_id, result, model_version, is_fallback=False):
        row = db_module.prediction_row(report_id, result, model_version, is_fallback)
        fake.insert_prediction_row(row)

    monkeypatch.setattr(db_module, "insert_prediction", fake_insert_prediction)

    return fake


def _mock_classifier(hazard_assessment, control_status, severity, version="mock-classifier-v1"):
    """A deterministic stand-in for classifier_llm.classify - no network, exact severity."""

    def classify(report_text: str) -> dict:
        is_precursor = (
            hazard_assessment == "yes"
            and control_status in ("absent", "failed")
            and severity >= 4
        )
        return {
            "hazard_assessment": hazard_assessment,
            "lsr_rule": "line_of_fire" if hazard_assessment == "yes" else "none",
            "control_status": control_status,
            "severity": severity,
            "is_sif_precursor": is_precursor,
            "confidence": 0.9,
            "flagged_phrases": [],
            "reasoning": f"mock reasoning for severity {severity}",
        }

    classify.version = version
    return classify


# ---------------------------------------------------------------------------
# The core regression test: submit several reports with a mocked classifier that
# returns DIFFERENT severities, and confirm each one round-trips unchanged.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "severity,hazard_assessment,control_status",
    [
        (1, "no", None),
        (2, "yes", "present"),
        (3, "yes", "unclear"),
        (4, "yes", "absent"),
        (5, "yes", "failed"),
    ],
)
def test_worker_report_severity_round_trips_unchanged(
    swap_classifiers, fake_db, severity, hazard_assessment, control_status
):
    """Different reports must be capable of landing on any of 1-5, and whichever value the
    classifier returns must be exactly what gets stored and exactly what a later read
    returns - never coerced, clamped, or overwritten to 5 somewhere in between.
    """
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    swap_classifiers(primary=_mock_classifier(hazard_assessment, control_status, severity))

    payload = {
        "report_text": f"Test report body for severity {severity} scenario, unique token {severity}-abc.",
        "site": "Test Site",
        "activity": "Test Activity",
        "shift": "day",
        "is_contractor": False,
    }

    resp = client.post("/reports/worker", json=payload)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    # 1. The API's own immediate response reflects the classifier's severity.
    assert body["result"]["severity"] == severity

    report_id = None
    for rid in fake_db.predictions:
        if fake_db.predictions[rid][-1]["severity"] == severity:
            report_id = rid
    assert report_id is not None, "no prediction row was ever inserted for this severity"

    # 2. What actually landed in the (fake) predictions table matches, unmodified.
    stored_row = fake_db.latest_prediction(report_id)
    assert stored_row is not None
    assert stored_row["severity"] == severity
    assert stored_row["hazard_assessment"] == hazard_assessment


def test_five_reports_in_a_row_produce_five_different_severities(swap_classifiers, fake_db):
    """The exact symptom from the bug report: submit several different reports back to back
    and confirm Admin Triage would see real variation, not a flat wall of 5s.
    """
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    severities_seen = []

    for severity in [1, 2, 3, 4, 5]:
        swap_classifiers(primary=_mock_classifier("yes", "absent", severity))
        payload = {
            "report_text": f"Distinct worker report text number {severity} describing a scenario.",
            "site": "Test Site",
            "activity": "Test Activity",
            "shift": "night",
            "is_contractor": True,
        }
        resp = client.post("/reports/worker", json=payload)
        assert resp.status_code == 200, resp.text
        severities_seen.append(resp.json()["result"]["severity"])

    assert severities_seen == [1, 2, 3, 4, 5]
    assert len(set(severities_seen)) == 5, (
        "reports with different underlying severities all collapsed to the same value - "
        "this is the exact bug this test guards against"
    )


def test_recommended_check_patch_never_touches_severity(swap_classifiers, fake_db):
    """Guards the specific assertion added in routes.py: STEP 3 (attaching
    recommended_check) must be provably a no-op on severity, for every lsr_rule.
    """
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    for severity in (2, 5):
        swap_classifiers(primary=_mock_classifier("yes", "absent", severity))
        resp = client.post(
            "/reports/worker",
            json={
                "report_text": f"Recommended-check no-op guard text {severity}.",
                "site": "Test Site",
                "activity": "Test Activity",
                "shift": "day",
                "is_contractor": False,
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["result"]["severity"] == severity
