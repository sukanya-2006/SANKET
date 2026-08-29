# Backend — SIF Precursor Detection API

**Phase 1 status: stub.** Every endpoint returns the locked schema ([NAMES.md](../NAMES.md))
backed by deterministic fake data, so Member 5 can build all three screens before any model
exists. Phase 3 swaps the producers — Member 2's TF-IDF baseline and Claude classifier, and
Supabase behind the aggregates. **Paths and field names do not change.**

Authoritative specs: [docs/TECH_STACK.md](../docs/TECH_STACK.md) (v2, wins any disagreement),
[NAMES.md](../NAMES.md), [docs/rubric.md](../docs/rubric.md).

## Run it

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

cp .env.example .env        # optional: defaults work with no database
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
./.venv/Scripts/python.exe -m pytest -q
```

Docs at <http://localhost:8000/docs>; OpenAPI JSON at `/openapi.json` (generate the typed
frontend client from it rather than hand-writing types).

## Endpoints

| Method | Path | Screen |
|---|---|---|
| `POST` | `/analyze` | 1 — live analyse box |
| `GET` | `/reports` | 2 — ranked queue (`is_sif_precursor`, `lsr_rule`, `site`, `source`, `q`, `limit`, `offset`) |
| `GET` | `/reports/{report_id}` | 2 — detail |
| `GET` | `/aggregate/summary` | 3 — stat cards |
| `GET` | `/aggregate/sites` | 3 — site rate ranking |
| `GET` | `/aggregate/activities` | 3 — activity rate ranking |
| `GET` | `/aggregate/rules` | 3 — rule × barrier view |
| `GET` | `/aggregate/shifts` | 3 — site × shift |
| `GET` | `/aggregate/trend` | 3 — monthly line |
| `GET` | `/meta`, `/health` | all |

> **Migration note (v1.1 → v2, 29 Aug).** The Day-3 draft shipped `/api/v1/classify`,
> `/api/v1/reports`, `/api/v1/dashboard/summary` with invented field names (`label`, `gates`,
> `energy_source`, `lsr`, `rationale`, `evidence_spans`). Those pre-dated the master plan and
> **are gone**. Everything now uses the locked names. If Member 5 wrote anything against the old
> shape, it needs updating — better today than on day 12.

## /analyze response

```json
{
  "result": {
    "hazard_assessment": "yes",
    "lsr_rule": "energy_isolation",
    "control_status": "absent",
    "severity": 4,
    "is_sif_precursor": true,
    "confidence": 0.82,
    "flagged_phrases": ["isolated", "no lockout"],
    "reasoning": "Hazard present (energy_isolation) with the direct control absent; ...",
    "recommended_check": "Verify energy isolation: sources identified, isolated, locked, ..."
  },
  "model_version": "stub-0.1.0",
  "is_fallback": false,
  "latency_ms": 1,
  "created_at": "2026-08-29T09:08:01Z"
}
```

Contract notes for Member 5:

- `hazard_assessment` is three-valued. `insufficient_information` is **not** a "no" — render it
  as its own state; those reports go to human review, not to the bottom of the queue.
- `control_status` is four-valued (`absent` / `failed` / `present` / `unclear`). `present` means
  the barrier held, so the report is **not** a precursor even though the hazard was real. That is
  the ambiguous demo case, and the UI must make it legible.
- `flagged_phrases` are verbatim substrings of the submitted text — `indexOf` them to highlight.
  Asserted by a test.
- `recommended_check` is non-null only when `is_sif_precursor` is true. It is a **static lookup**,
  never model output.
- `is_fallback` is always `false` in Phase 1. It flips true in Phase 4 when the Claude call fails
  or times out and the local TF-IDF baseline answers. **Build the "degraded mode — keyword
  baseline" banner against this field now.**
- Stub results are deterministic: same text, same result.

## Aggregation rules a judge will probe

Implemented in [app/aggregate.py](app/aggregate.py); the Phase 3 SQL is already written in
[app/sql/aggregates.sql](app/sql/aggregates.sql).

1. **Rate, not raw count.** Raw counts penalise sites that report diligently — the opposite of the
   incentive a safety system should create.
2. **Both count and rate, always.** Rank by rate; keep the count visible so nobody mistakes 2 of 6
   for a crisis.
3. **Small-denominator guard**, `MIN_GROUP_N = 5`. Groups below it go to `insufficient_volume`,
   which the frontend greys out — never hides.
4. **Latest prediction per report, current `model_version` only.**
5. **`source = 'osha'` excluded from every aggregate** — no site taxonomy. Stated plainly, not hidden.

## Seeded stub dataset

180 reports: 150 synthetic across 10 fixed sites + 30 OSHA-shaped rows. Positive class 22%,
inside the plan's 20–25% band. Distribution is deliberately uneven so the rate ranking has a clean
winner — Rig 4, 11 of 20 reports, all `energy_isolation`, 9 on night shift. Import-time assertions
fail loudly if a template edit breaks those numbers, rather than silently on stage.

**Two honesty warnings that must survive into the pitch:**

- The 30 `osha-placeholder-*` rows are **not real OSHA reports**. Member 3/6 replace them with the
  real pull. Never show them on stage as real OSHA text.
- `median_triage_seconds` is computed from synthetic timestamps. It is not a measured number and
  must not be quoted as the before/after headline until real timings exist.

## Layout

```
backend/app/
  main.py             FastAPI app, CORS, /health
  config.py           env settings
  schemas.py          locked schema (master plan §5)
  aggregate.py        rate-based density aggregation  ← artifact #2 of the three that matter
  stub.py             deterministic fake classifier + seeded dataset
  api/routes.py       all endpoints
  api/recommendations.py  static checklists, never model output
  db.py               Supabase client; returns None when unconfigured
  sql/schema.sql      Supabase tables, constraints, RLS, fixed site list
  sql/aggregates.sql  Phase 3 SQL, one statement per aggregate
backend/tests/        the ten tests named in TECH_STACK v2
```

## Database

[app/sql/schema.sql](app/sql/schema.sql) — run it once in the Supabase SQL editor, then
[app/sql/aggregates.sql](app/sql/aggregates.sql) for the `latest_predictions` view. Four tables:
`sites`, `reports`, `predictions`, `gold_labels`.

- **`predictions` is append-only.** Never UPDATE a row; write a new one. That makes "every
  judgement is logged and reviewable" a property of the schema rather than a promise.
- **Two CHECK constraints encode rubric v2.0 §6 and §2** — `is_sif_precursor` must equal
  `hazard yes AND control absent/failed AND severity >= 4`, and `control_status` must be null
  unless the hazard is `yes`. A prompt change cannot quietly redefine the label.
- **`gold_labels.gate_split`** records which gate the annotators disagreed on. That column is the
  whole diagnostic if agreement lands under 70%: it says which gate to revise instead of
  rewriting the rubric wholesale.
- **RLS is on with no policies.** The frontend never talks to Supabase — it goes through FastAPI,
  which holds the service key. A leaked anon key reads nothing.
- Three tests assert that the SQL vocabulary, the Pydantic enums, and the locked names have not
  drifted apart.

The API runs fine with no database: `db.get_client()` returns None and the routes serve the
seeded stub. Member 5 is never blocked on an instance being awake, and the demo does not die if
a free-tier database went to sleep.

**Not built yet:** the real classifiers, the SQLite cache, and the offline fallback. Three tests
for those are present and explicitly skipped rather than faked.

**Open question for the team:** TECH_STACK v2 §"Repo layout" specifies `api/` and `web/`; the repo
uses `backend/` and `frontend/`. Module names match the doc. Decide before deploy config is written.

## Owner

Member 4. Depends on Member 1's rubric and Member 2's final `ClassificationResult`.
Consumed by Member 5.
