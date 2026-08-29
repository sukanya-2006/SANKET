# SIF-2026 — SIF Precursor Detection

**PS SIH26165 (Oil India Limited).** An AI/NLP engine that reads free-text industrial safety
reports, decides which ones describe situations that could have killed someone, tags them to IOGP
Life-Saving Rules, and ranks sites and activities by precursor density.

It never closes a report. It reorders the reading queue.

> Safety programmes measure how many incidents happen. They don't measure how many could have
> killed someone. We built the second thing.

---

## Read these first, in this order

| Document | What it is |
|---|---|
| [docs/TECH_STACK.md](docs/TECH_STACK.md) | **v2, authoritative.** If any other write-up disagrees, this wins |
| [NAMES.md](NAMES.md) | Locked field names. Read before writing a line of code, SQL, or UI |
| [docs/rubric.md](docs/rubric.md) | v2.0 — the three gates, how to apply them, the labelling protocol |
| [docs/handoff/](docs/handoff/) | One page per member: what is waiting for you and how to plug it in |

**The naming rule matters more than it looks.** Field names drifted across three drafts of the
plan before v2. If you find yourself typing `category`, `hazard_category`, or `barrier_status`,
stop — the fields are `lsr_rule` and `control_status`.

---

## Start the backend in 60 seconds

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt     # Windows
# source .venv/bin/activate && pip install -r requirements.txt    # macOS/Linux

./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

No database, no API key, no configuration. It serves 180 seeded reports through the real response
shapes. Interactive docs at <http://localhost:8000/docs>.

```bash
./.venv/Scripts/python.exe -m pytest -q      # 34 tests
```

---

## What exists today

| Area | State |
|---|---|
| **API** | All endpoints live: `/analyze`, `/reports`, six `/aggregate/*`, `/meta`, `/health` |
| **Classification pipeline** | Cache → primary → retry once → baseline fallback → `is_fallback`. Working end to end with a keyword stub in both slots |
| **Aggregation** | Rate-based density ranking, small-denominator guard, OSHA exclusion. Runs plain SQL when a database is configured, Python over the stub when not |
| **Database** | Schema written with constraints that encode the rubric. Not yet pointed at a live instance |
| **Rubric** | v2.0, locked gates, sources separated from our own calibration |
| **Tests** | 34, all real. No skips |
| **Frontend** | Not started — Member 5 |
| **Classifiers** | Not started — Member 2. Two functions, one registration call each |
| **Real dataset** | Not started — Member 3. 150 synthetic + 30 OSHA |

The seeded stub is **not** the model. `/health` names the active classifier precisely so nobody
demos `stub-0.1.0` believing it is Claude.

---

## Repo layout

```
NAMES.md                  locked field names
README.md                 this file
docs/
  TECH_STACK.md           v2, authoritative
  rubric.md               v2.0 labelling rubric
  handoff/                one page per member
  demo-script.md          5-minute script, word for word
  hostile-qa.md           question bank with model answers
  idea-submission.md      SIH submission draft
  red-team-reports.md     15 adversarial reports for the rubric
  rehearsal.md            drills and per-member cheat sheets
backend/
  app/
    main.py               FastAPI app, /health
    config.py             settings
    schemas.py            the locked schema
    classifier.py         the classify() boundary: cache, timeout, retry, fallback
    cache.py              SQLite cache keyed on sha256(report_text + prompt_version)
    repository.py         reads: Postgres when configured, seeded stub when not
    aggregate.py          rate-based density aggregation
    stub.py               deterministic keyword classifier + 180 seeded reports
    db.py                 psycopg access, named-statement loader
    api/routes.py         all endpoints
    api/recommendations.py static checklists, never model output
    sql/schema.sql        tables, constraints, RLS, fixed sites
    sql/aggregates.sql    one named statement per aggregate
  scripts/ingest.py       load Member 3's CSVs, classify, write predictions
  tests/                  34 tests
frontend/                 Member 5
data/                     Member 3
render.yaml               Member 6 — API deployment
```

> **Layout note.** TECH_STACK v2 §Repo layout specifies `api/` and `web/`; the repo uses
> `backend/` and `frontend/`, which were committed before that file landed. Module names inside
> match the doc. Decide whether to rename before deploy config is finalised.

---

## The three artifacts that matter most

1. `eval/run_eval.py` — baseline F1, LLM F1, human agreement ceiling, OSHA-set LLM F1, severity
   MAE. **Not built** (Member 3).
2. `backend/app/aggregate.py` — rate-based precursor density by site, activity, rule, and
   barrier, plus trend and triage latency. **Built.**
3. The live text box on the first screen, with the offline fallback behind it. **Backend built,
   UI not started** (Member 5).

---

## Honesty rules that outlive this repo

These are not decoration; they are what makes the numbers defensible.

- **Our data is synthetic plus public OSHA.** We never imply we had Oil India data. Disclosed
  proactively, not confessed under questioning.
- **Never quote accuracy.** At ~22% positives, "always say no" scores 78%. Report F1 and PR-AUC.
- **Human agreement is the ceiling.** If two annotators agree 88% of the time, no classifier can
  honestly claim 95%.
- **Two numbers in the API are currently fake** and must not reach a slide: the 30
  `osha-placeholder-*` rows are not real OSHA text, and `median_triage_seconds` is computed from
  synthetic timestamps.
- **The model never generates safety advice.** `recommended_check` is a static lookup table.
