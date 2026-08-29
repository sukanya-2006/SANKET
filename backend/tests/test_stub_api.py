"""Contract tests for the Phase 1 stub API.

These assert the *shape* Member 5 builds against. They must keep passing after Phase 3
swaps the stub for the real pipeline — that is the point of them.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import LifeSavingRule

client = TestClient(app)

PRECURSOR = (
    "Employee reached into the running conveyor to clear a jam. Lockout was not applied "
    "and his index finger was amputated."
)
NOT_SIF = "Worker slipped on a wet floor in the break room and fractured his wrist."
THIN = "Employee was injured."


def test_health():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["stub_mode"] is True


def test_classify_returns_full_contract():
    r = client.post("/api/v1/classify", json={"narrative": PRECURSOR})
    assert r.status_code == 200
    body = r.json()
    assert body["label"] == "SIF_PRECURSOR"
    assert 0.0 <= body["confidence"] <= 1.0
    assert set(body["gates"]) == {
        "gate_1_high_energy",
        "gate_2_control_failed",
        "gate_3_serious_injury_plausible",
    }
    assert all(g["passed"] is True for g in body["gates"].values())
    assert body["energy_source"] == "mechanical"
    assert body["lsr"] == "energy_isolation"
    assert body["model"] == "stub"
    assert body["rubric_version"] == "1.0"
    assert body["offline_fallback"] is False


def test_evidence_spans_index_into_the_narrative():
    body = client.post("/api/v1/classify", json={"narrative": PRECURSOR}).json()
    assert body["evidence_spans"]
    for span in body["evidence_spans"]:
        assert PRECURSOR[span["start"] : span["end"]] == span["text"]
        assert span["gate"] in (1, 2, 3)


def test_classification_is_deterministic():
    a = client.post("/api/v1/classify", json={"narrative": PRECURSOR}).json()
    b = client.post("/api/v1/classify", json={"narrative": PRECURSOR}).json()
    assert a["label"] == b["label"] and a["confidence"] == b["confidence"]


def test_low_energy_report_is_not_sif():
    body = client.post("/api/v1/classify", json={"narrative": NOT_SIF}).json()
    assert body["label"] == "NOT_SIF"
    assert body["gates"]["gate_1_high_energy"]["passed"] is False


def test_thin_narrative_is_unclear_with_null_gates():
    body = client.post("/api/v1/classify", json={"narrative": THIN}).json()
    assert body["label"] == "UNCLEAR"
    assert all(g["passed"] is None for g in body["gates"].values())


def test_empty_narrative_is_rejected():
    assert client.post("/api/v1/classify", json={"narrative": ""}).status_code == 422


def test_batch_classify():
    r = client.post(
        "/api/v1/classify/batch",
        json={"items": [{"narrative": PRECURSOR}, {"narrative": NOT_SIF}]},
    )
    body = r.json()
    assert body["count"] == 2
    assert [x["label"] for x in body["results"]] == ["SIF_PRECURSOR", "NOT_SIF"]


def test_reports_pagination_and_filter():
    page = client.get("/api/v1/reports", params={"limit": 3}).json()
    assert len(page["items"]) == 3
    assert page["total"] >= 3

    filtered = client.get("/api/v1/reports", params={"label": "SIF_PRECURSOR"}).json()
    assert filtered["total"] > 0
    assert all(i["predicted_label"] == "SIF_PRECURSOR" for i in filtered["items"])


def test_report_detail_and_404():
    detail = client.get("/api/v1/reports/stub-0001").json()
    assert detail["id"] == "stub-0001"
    assert detail["classification"]["label"] == detail["predicted_label"]
    assert client.get("/api/v1/reports/does-not-exist").status_code == 404


def test_dashboard_buckets_use_plain_enum_values():
    body = client.get("/api/v1/dashboard/summary").json()
    assert body["total_reports"] > 0
    assert 0.0 <= body["precursor_rate"] <= 1.0
    for bucket in body["by_label"]:
        assert bucket["key"] in ("SIF_PRECURSOR", "NOT_SIF", "UNCLEAR")
    assert body["model_health"]["active_model"] == "stub"


def test_lsr_taxonomy_is_the_eight_rules_we_use():
    """Bypassing Safety Controls is excluded — Gate 2 already measures barrier defeat."""
    values = client.get("/api/v1/meta").json()["life_saving_rules"]
    assert "bypassing_safety_controls" not in values
    assert len([v for v in values if v != "none"]) == 8
    assert set(values) == {r.value for r in LifeSavingRule}
