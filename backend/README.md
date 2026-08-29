# Backend — SIF Precursor Detection API

**Phase 1 status: stub.** Every endpoint returns the final response shape backed by fake,
deterministic data, so Member 5 can build all three frontend screens before any model exists.
Phase 3 swaps the bodies for Supabase + the real ML pipeline — **paths and response models do not
change**.

## Run it

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

cp .env.example .env        # optional: defaults work with no database
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

- Interactive docs: <http://localhost:8000/docs>
- OpenAPI JSON (generate a typed frontend client from this): <http://localhost:8000/openapi.json>

```bash
./.venv/Scripts/python.exe -m pytest -q
```

## Endpoints

| Method | Path | Screen | Notes |
|---|---|---|---|
| GET | `/health` | — | stub mode + database status |
| GET | `/api/v1/meta` | all | enum values for dropdowns; rubric version |
| POST | `/api/v1/classify` | 1 — live analyze | `{"narrative": "...", "report_id": null}` |
| POST | `/api/v1/classify/batch` | — | up to 100 narratives |
| GET | `/api/v1/reports` | 2 — report list | `limit`, `offset`, `label`, `energy_source`, `q` |
| GET | `/api/v1/reports/{id}` | 2 — detail | 404 when unknown |
| GET | `/api/v1/dashboard/summary` | 3 — dashboard | tiles, buckets, model health |

## The classification contract

Defined in [app/schemas.py](app/schemas.py). Mirrors the three gates in
[docs/rubric.md](../docs/rubric.md) v1.0.

```json
{
  "report_id": null,
  "label": "SIF_PRECURSOR",
  "confidence": 0.91,
  "gates": {
    "gate_1_high_energy":              { "passed": true, "rationale": "..." },
    "gate_2_control_failed":           { "passed": true, "rationale": "..." },
    "gate_3_serious_injury_plausible": { "passed": true, "rationale": "..." }
  },
  "energy_source": "mechanical",
  "lsr": "energy_isolation",
  "rationale": "All three gates pass: ...",
  "evidence_spans": [{ "text": "lockout", "start": 62, "end": 69, "gate": 2 }],
  "model": "stub",
  "model_version": "stub-0.1.0",
  "rubric_version": "1.0",
  "offline_fallback": false,
  "latency_ms": 1,
  "created_at": "2026-08-29T06:59:08Z"
}
```

Contract notes for Member 5:

- `label` is one of `SIF_PRECURSOR`, `NOT_SIF`, `UNCLEAR`. Never assume two classes.
- Each gate's `passed` is **`true` / `false` / `null`**. `null` means the narrative could not
  support a judgement — render it as "insufficient information", not as a failed gate.
- `evidence_spans` are character offsets into the submitted narrative, so the UI can highlight
  in place: `narrative.slice(span.start, span.end) === span.text`.
- `lsr` uses **eight** IOGP Report 459 rules. "Bypassing Safety Controls" is deliberately absent —
  barrier defeat is what Gate 2 measures, so listing it as a category would double-count. A
  bypassed control arrives as gate 2 `passed: true` with `lsr: "none"`.
- `offline_fallback` is always `false` in Phase 1. In Phase 4 it turns `true` when the Claude API
  fails and the local TF-IDF baseline takes over — **build the offline-mode UI indicator against
  this field now**.
- Stub results are deterministic: the same narrative always returns the same result.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `SUPABASE_URL` | `""` | blank ⇒ no database, stub data only |
| `SUPABASE_SERVICE_KEY` | `""` | server-side key; never ship to the frontend |
| `STUB_MODE` | `true` | flip to `false` in Phase 3 |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | comma-separated |

## Layout

```
backend/
  app/
    main.py        FastAPI app, CORS, /health
    config.py      env settings
    schemas.py     the classification contract (provisional — Member 2 owns the final version)
    stub.py        deterministic fake classifier + 15-report fake dataset
    api/routes.py  all /api/v1 endpoints
  tests/           contract tests that must survive the Phase 3 swap
```

## Owner and hand-offs

Member 4. Depends on Member 1's rubric ([docs/rubric.md](../docs/rubric.md)) for the gate
definitions and Member 2's final Pydantic schema. Consumed by Member 5.

**Not built yet:** the Supabase schema and SQL aggregations (Phase 1/3), the real pipeline wiring
(Phase 3), and the offline-fallback logic (Phase 4).
