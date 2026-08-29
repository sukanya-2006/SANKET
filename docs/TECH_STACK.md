# FINAL TECH STACK — v2 CONSOLIDATED (supersedes all previous versions)

If any other stack write-up disagrees with this file, this file wins. Version drift has now
reintroduced dead bugs three times — stop keeping copies in chats and notes.

---

## Backend
Python 3.11, FastAPI + Uvicorn, Pydantic v2 (validates LLM output; schema-failure rate becomes a free metric). All SQL parameterised. No auth, no Docker, no websockets, no background workers — 22-day prototype, simplicity is a feature.

## Database
Supabase (managed Postgres, free tier). No pgvector, no embeddings, no clustering.
Tables: `sites`, `reports`, `predictions` (append-only, carries `model_version`, `is_fallback`), `gold_labels` (carries `annotator`).

## Locked names (NAMES.md — verbatim, no synonyms anywhere)
Classification: `lsr_rule`, `hazard_assessment`, `control_status`, `severity`, `is_sif_precursor`, `flagged_phrases`, `confidence`, `reasoning`, `recommended_check`
Metadata: `site`, `activity`, `shift`, `report_date`, `is_contractor`, `source`
Banned synonyms that keep creeping back: ~~category~~, ~~hazard_category~~, ~~barrier_status~~ (UI may *display* "barrier failure"; the field is `control_status`).

## Classification — two classifiers, deliberately
- **Baseline:** scikit-learn, TF-IDF → logistic regression, ~30 lines. Explainability: top-weighted words via `sorted(zip(vec.get_feature_names_out(), model.coef_[0]))`. No SHAP.
- **Real classifier:** one structured Claude API call per report returning the full locked schema: `hazard_assessment` (yes / no / insufficient_information), `lsr_rule` (8 IOGP categories + none), `control_status` (absent / failed / present / unclear), `severity` (1–5), `is_sif_precursor`, `confidence` (float 0–1 — required for PR-AUC), `flagged_phrases`, `reasoning`. Validated by Pydantic; on failure retry once, then baseline fallback + human-review flag, rate logged.
- Both share one boundary: `classify(text) -> ClassificationResult`. Backend never knows which is inside.
- The baseline-vs-LLM gap is the strongest differentiator. Baseline is built and scored FIRST.

## Multilingual
Inside the Claude prompt (Hindi/Hinglish/code-mixed). No separate pipeline. A handful of code-mixed reports sit in the dataset to prove it.

## Aggregation (v1.1 — rate-based, not count-based)
Plain SQL only. Endpoints:
- `/aggregate/summary` — totals, precursor count & rate, insufficient_information count, avg confidence, **median_triage_seconds** (the monthly-triage-to-seconds headline), model_version.
- `/aggregate/sites` and `/aggregate/activities` — per group: report_count, precursor_count, **precursor_rate**, top_rule; ranked by rate then count. **Small-denominator guard:** groups with <5 reports go to an `insufficient_volume` list (greyed in UI, never silently hidden). Rate exists so diligent-reporting sites aren't punished — a judge will ask.
- `/aggregate/rules` — lsr_rule × control_status counts.
- `/aggregate/shifts` — site × shift counts and rates.
- `/aggregate/trend` — monthly report_count, precursor_count, precursor_rate.

Rules for every aggregate: latest prediction per report for current model_version only; exclude `source='osha'` (no site taxonomy); every query readable aloud in two sentences.

## Recommendations (static, never generated)
`api/recommendations.py`: plain dict LSRRule → one fixed verification checklist string. Returned as `recommended_check` when `is_sif_precursor` is true. The model never generates safety advice — say exactly that if asked.

## Caching + offline fallback (both, not either)
- Cache: SQLite keyed on `sha256(report_text + prompt_version)` — reproducible evals, wifi-proof for seen reports.
- **Offline fallback (do not drop this again):** the live box takes NEW text, which the cache cannot cover. On API failure/timeout (10s): local TF-IDF baseline answers, `is_fallback: true`, UI shows "degraded mode — keyword baseline" plainly. Wired early (Stage 4, ~day 7), not in the final 48 hours — untested resilience is not resilience.

## Frontend
React + Vite + TypeScript + Tailwind + Recharts. Three screens: (1) live analyse box on the LANDING page with the degraded-mode banner; (2) ranked report queue (severity-sorted, precursors on top, flagged phrases highlighted); (3) density dashboard — site & activity rate rankings with counts visible, rule × barrier view, monthly trend line, summary stat cards. UI vocabulary mirrors the PS: "SIF-potential", "barrier failure".

## Deployment
Vercel (frontend) + Render or Railway (API), free tiers. Secrets: python-dotenv locally, platform env vars in production, `.env` gitignored from commit one. Never commit keys — judges read repos.

## Testing
pytest locally, ~10 real tests: /analyze contract, 422 on malformed/empty input, schema-validation retry, fallback trigger, cache hit, rate correctness (2/4 = 0.5), small-denominator exclusion, trend bucketing, OSHA exclusion from aggregates, recommended_check behaviour. No CI. The pitch may claim a test suite only because it exists.

## Ground truth / labelling (locked — the part judges will probe hardest)
- Three-gate rubric: Gate 1 hazard (yes/no/insufficient_information, 8 IOGP categories — nine exist; *Bypassing Safety Controls* deliberately excluded because Gate 2 measures barrier defeat) → Gate 2 control status (present = STOP, not a precursor) → Gate 3 plausible-variation test (small realistic change → death/life-altering injury?).
- Sourced from the PS's own citations (DEKRA Martin & Black 2015, EEI SIF model, VelocityEHS 2024) + IOGP Report 459. 15-minute external EHS review before finalising; record reviewer name.
- Rubric-writer (M1) and report-writer (M3) work with no cross-contact until both finish.
- **Dataset: 150 synthetic** (not 90 — at ~22% positives, 90 leaves ~6 test positives and F1 swings ~8 points per flipped prediction) **+ 30 real OSHA narratives** (pulled by M6). Every synthetic report carries site/activity/shift/report_date/is_contractor across 8–10 fixed sites, distributed unevenly so the rate ranking has a clean winner. Positive class 20–25%; never rebalance.
- Both annotators (M1, M3) label ALL 180 independently, batched (90 by day 4 for the early agreement signal, rest by day 6). M6 tiebreaks, recording which gate split. <70% agreement → revise only the offending gate, re-label only its reports.

## Evaluation (two tables + one line — never the single merged table)
1. **Synthetic held-out split:** baseline F1/PR-AUC vs LLM F1/PR-AUC — the fair fight. (~30 dev reports for prompt tuning; held-out opened exactly ONCE.)
2. **OSHA set: LLM only** — generalisation check on real text nobody on the team wrote. (Baseline-on-OSHA measures domain transfer, not quality — an unfair fight we don't stage.)
3. **Severity MAE** on precursor cases vs adjudicated human severity.

Report F1 and PR-AUC, never accuracy. Recall over precision, stated as a design choice. Plus: annotator agreement % and Cohen's kappa as the ceiling.

## Repo layout
```
sif-detector/
├── NAMES.md
├── docs/TECH_STACK.md          ← this file
├── api/    main.py, schemas.py, classifier_llm.py, classifier_base.py,
│           aggregate.py, recommendations.py, db.py
├── eval/   label_reports.py, kappa.py, run_eval.py
├── data/   synthetic/, osha/, gold_labels.csv, reports_metadata.csv
├── web/
└── tests/
```

> **Layout deviation, flagged not resolved (Member 4).** The repo as committed uses `backend/app/`
> and `frontend/` rather than `api/` and `web/` — those directories were created by another member
> before this file landed. Module names inside match the doc (`aggregate.py`,
> `api/recommendations.py`, `schemas.py`, `main.py`). Renaming the directories touches Member 5's
> working tree and Member 6's deploy config, so it needs the three of us to agree rather than a
> unilateral move. **Decide this before Render/Vercel config is written.**

## The three artifacts that matter most
1. `eval/run_eval.py` → one output: baseline F1, LLM F1, human ceiling, OSHA-set LLM F1, severity MAE.
2. `api/aggregate.py` → rate-based precursor density ranking by site/activity/rule/barrier + trend + triage-latency stat.
3. The live text box, first screen, with the offline fallback behind it.

## Cost
Free tiers throughout; ~500 Claude calls across dev + demo. Budget ₹1,000 (₹500 is optimistic once prompt-tuning re-runs are counted). Still effectively free.

---
*Changelog v2: names re-locked (category/hazard_category/barrier_status purged again); dataset restored to 150; two-table evaluation restored; offline fallback restored; v1.1 aggregation (rates, activities, trend, summary, guard, recommended_check) merged; severity MAE and metadata columns confirmed.*
