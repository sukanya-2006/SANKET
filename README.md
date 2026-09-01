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
| [docs/rubric.md](docs/rubric.md) | v2.1 — the three gates, how to apply them, the labelling protocol |
| [docs/handoff/](docs/handoff/) | One page per member: what is waiting for you and how to plug it in |

**The naming rule matters more than it looks.** Field names drifted across three drafts of the
plan before v2. If you find yourself typing `category`, `hazard_category`, or `barrier_status`,
stop — the fields are `lsr_rule` and `control_status`.

---

## Start the backend in 60 seconds

```bash
git clone https://github.com/sukanya-2006/SIH-2026.git && cd SIH-2026
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt    # Windows
# source .venv/bin/activate && pip install -r backend/requirements.txt   # macOS/Linux

cd backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
../.venv/Scripts/python.exe -m pytest -q          # 36 tests
```

No database, no API key, no configuration needed. It serves 180 seeded reports through the real
response shapes and logs plainly what it could not load. Interactive docs at
<http://localhost:8000/docs>; generate the frontend's types from `/openapi.json`.

Verified from a clean clone: 36 tests pass with no API key and no database.

---

## What exists today

| Area | State |
|---|---|
| **API** | ✅ All endpoints live: `/analyze`, `/reports`, six `/aggregate/*`, `/meta`, `/health` |
| **Classification pipeline** | ✅ Cache → primary → retry once → baseline fallback → `is_fallback` |
| **Real classifier** | ✅ Groq (`openai/gpt-oss-20b`) prompted with rubric v2.1, registered in the primary slot. Needs `GROQ_API_KEY` |
| **TF-IDF baseline** | ⚠️ Written, **not yet trained** — needs `gold_labels.csv`. Until then the fallback answers with the keyword stub |
| **Aggregation** | ✅ Rate-based density ranking, small-denominator guard, OSHA exclusion. Plain SQL when a database is configured, Python over the stub when not |
| **Database** | ⚠️ Schema written, constraints encode the rubric. **No live instance** — no `backend/.env` yet |
| **Rubric** | ✅ v2.1, locked gates, sources separated from our own calibration |
| **Dataset** | ✅ 150 synthetic + 30 real OSHA reports, with metadata |
| **Labelling** | 🔴 **0 of 180 by either annotator — this is the critical path** |
| **Tests** | ✅ 36, all real, no skips, hermetic |
| **Frontend** | 🔴 Not started — Member 5 |

Two honesty properties worth knowing before you demo anything:

- **`/health` names the classifier that is actually registered.** If the Groq key is missing it
  says `stub-0.1.0`, so nobody presents the keyword stub believing it is the real classifier.
- **The API always boots.** Missing key, missing database, untrained baseline — it degrades and
  logs why rather than refusing to start. A deployment that cannot start has no degraded mode.

---

## The critical path

Everything downstream is blocked on one thing.

```
labelling (M1 + M3, 0/180)  ──▶  merge_labels.py  ──▶  gold_labels.csv
                                                            │
                        ┌───────────────────────────────────┤
                        ▼                                   ▼
              train_baseline.py                     load_reports.py
              (baseline F1/PR-AUC)                  batch_classify.py
                        │                                   │
                        └──────────▶  eval table  ◀─────────┘
                                    (the pitch's core number)
```

Both annotators label all 180 **independently**, with no discussion of any case until both are
completely finished. That independence is what makes Cohen's kappa mean anything, and it is the
answer to the hardest question a judge will ask: *"you wrote the reports and graded yourself."*

---

## Repo layout

```
NAMES.md                  locked field names
docs/
  TECH_STACK.md           v2, authoritative
  rubric.md               v2.1 labelling rubric
  handoff/                one page per member
  demo-script.md          5-minute script, word for word
  hostile-qa.md           40 questions with model answers
  idea-submission.md      SIH submission draft
  red-team-reports.md     15 adversarial reports for the rubric
  rehearsal.md            drills and per-member cheat sheets

create_labeling_template.py   per-annotator worksheet generator
merge_labels.py               agreement %, Cohen's kappa, writes gold_labels.csv
train_baseline.py             trains the TF-IDF baseline (needs gold_labels.csv)
load_reports.py               loads reports into Supabase
batch_classify.py             runs the real classifier over every stored report
reclassify_fallbacks.py       retries reports that only got a fallback answer
generate_synthetic_reports_free.py · extract_osha.py · patch_synthetic_reports.py

backend/
  app/
    main.py               FastAPI app, /health, classifier registration
    config.py             settings
    schemas.py            the locked schema
    classifier.py         the classify() boundary: cache, timeout, retry, fallback
    classifier_llm.py     the real classifier — one structured Groq call
    classifier_base.py    TF-IDF baseline; auto-registers once trained
    cache.py              SQLite cache keyed on sha256(report_text + prompt_version)
    repository.py         reads: Postgres when configured, seeded stub when not
    aggregate.py          rate-based density aggregation
    stub.py               deterministic keyword classifier + 180 seeded reports
    db.py                 psycopg access, named-statement loader
    api/routes.py         all endpoints
    api/recommendations.py  static checklists, never model output
    sql/schema.sql        tables, constraints, RLS, fixed sites
    sql/aggregates.sql    one named statement per aggregate
  tests/                  36 hermetic tests
frontend/                 Member 5
data/                     150 synthetic + 30 OSHA reports, annotator worksheets
render.yaml               Member 6 — API deployment
```

> **Layout note.** TECH_STACK v2 §Repo layout specifies `api/` and `web/`; the repo uses
> `backend/` and `frontend/`, committed before that file landed. Module names inside match the
> doc. Decide whether to rename before deploy config is finalised.

---

## The three artifacts that matter most

1. `eval/run_eval.py` — baseline F1, LLM F1, human agreement ceiling, OSHA-set LLM F1, severity
   MAE. **Not built** (Member 3), and blocked behind labelling regardless.
2. `backend/app/aggregate.py` — rate-based precursor density by site, activity, rule and barrier,
   plus trend and triage latency. **Built.**
3. The live text box on the first screen, with the offline fallback behind it. **Backend built,
   UI not started** (Member 5).

---

## Open decisions

- **LLM timeout is 25s**; TECH_STACK v2 says 10. Twenty-five seconds of silence on stage is worse
  than showing the fallback, which the demo script plans to show anyway.
- **`load_reports.py` and `backend/scripts/ingest.py` do the same job.** Keep one. `ingest.py` has
  strict column validation that would reject the `gold_labels.csv` that `merge_labels.py` writes.
- **`requirements_groq.txt`** at the root is a leftover; `backend/requirements.txt` covers
  everything.
- **Is 20 September the build deadline or the submission-form date?** The schedule assumes ~22
  days with days 1–6 on labelling.

---

## Honesty rules that outlive this repo

These are not decoration; they are what makes the numbers defensible.

- **Our data is synthetic plus public OSHA.** We never imply we had Oil India data. Disclosed
  proactively, not confessed under questioning.
- **Never quote accuracy.** At ~22% positives, "always say no" scores 78%. Report F1 and PR-AUC.
- **Human agreement is the ceiling.** If two annotators agree 88% of the time, no classifier can
  honestly claim 95%.
- **`median_triage_seconds` is currently computed from synthetic timestamps.** It must not appear
  on a slide as a measured result until real timings exist.
- **The model never generates safety advice.** `recommended_check` is a static lookup table.
