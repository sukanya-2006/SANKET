# Investigation: newly submitted worker reports all showing Severity Level 5

## Summary

**Root cause: the Gate 3 prompt in `backend/app/classifier_llm.py`, not the storage or
display pipeline.** Every stage between the classifier and Admin Triage was audited and
confirmed to pass `severity` through unchanged. The bias was introduced by two prompt edits
that were each individually correct at the time, but which combined to leave nothing
counterbalancing an instruction to lean toward high severity once applied to real (as
opposed to synthetic, hazard-enriched) worker report text.

## What was ruled out (code audit, not guesswork)

Traced `severity` through every file the ticket named:

| Stage | File | Finding |
|---|---|---|
| Classifier output | `classifier_llm.py` | Model output only - no code-level override of `severity`. |
| Fallback classifier | `classifier_base.py` | Returns `4` (precursor) or `2` (non-precursor) as an honest coarse heuristic - never `5`, so this is not the source of a "flat 5" symptom. |
| Orchestration | `classifier.py` | Cache/retry/fallback machinery; never touches individual field values. |
| Route handler | `api/routes.py` (`submit_worker_report`) | `result = outcome.result.model_copy(update={"recommended_check": ...})` - only `recommended_check` is patched; `severity` passes through. |
| DB write | `db.py` (`insert_prediction` / `prediction_row`) | `"severity": result.severity` - direct pass-through, parameterised SQL, no coercion. |
| DB read | `sql/aggregates.sql` (`latest_predictions` view) | `DISTINCT ON (p.report_id) ... ORDER BY p.report_id, p.created_at DESC` - correctly picks the newest prediction per report; no aggregation that could collapse values to a max. |
| Repository | `repository.py` | Straight `SELECT ... l.severity ...` join, no post-processing on the value itself (only on ordering). |
| Frontend | `AdminTriage.jsx` | `Number(report.severity_score ?? report.severity ?? 0)` - `severity_score` is never sent by the backend, so this always reads `report.severity` as-is. Not the source (a bug here would default to `0`, not `5`). |

No hardcoded `severity = 5` (or `>= 4`, `= 4`, etc. that could round up) exists anywhere in the
non-prompt codebase. Grepped the full repo to confirm.

## What the git history actually shows

1. **`ec3f7e3` "Improve SIF classifier rubric and OSHA labels"** added an "IMPORTANT SEVERITY
   CALIBRATION" block to Gate 3, instructing the model not to under-score severity just
   because a report used a mild-sounding word like "hospitalized." This was a legitimate fix:
   `docs/eval-diagnosis.md` shows the LLM was at the time scoring systematically *low*
   (mean shift −0.28, 82% of misses were `severity < 4` where humans scored ≥ 4).

2. **`0cdd7e8` "Answer the base-rate question"** separately removed the prompt's "roughly one
   in five reports escalate" base-rate anchor, because the gold-label set is hazard-enriched
   by construction (59% precursors, not the 20-25% of a realistic report stream) and the
   anchor was empirically wrong for that dataset.

Each change was correct in isolation and is well-documented in `docs/eval-diagnosis.md`. But
together they left the one-directional "don't under-score" instruction from (1) with nothing
in the prompt pulling the distribution back down for (2) real, un-enriched worker-submitted
text. On live worker reports - which unlike the synthetic gold set are *not* guaranteed to
center on a severe hazard - the model had every incentive to lean toward 4/5 and none to land
on 1-3, so it increasingly did, converging on 5 for most submissions.

## Fix applied (`backend/app/classifier_llm.py`)

- Reframed "IMPORTANT SEVERITY CALIBRATION" as a correction to *wording* ("hospitalized" is not
  informative on its own), not a general push toward high scores.
- Added a third worked example: a "hospitalized overnight, discharged next day, no lasting
  deficit" scenario that should still score 3, directly countering the misreading that
  "hospitalized" implies 4/5.
- Added an explicit self-check before finalizing a 4 or 5: the model's own `reasoning` must
  name a specific mechanism of death/permanent disability after exactly one change, not just
  restate the hazard category.
- Bumped `classify.version` (`g3fix4` -> `g3fix5`) and `settings.prompt_version` (`v5` -> `v6`)
  so the SQLite classification cache does not keep serving over-scored answers cached under
  the old prompt.

**This fix could not be validated against the live Groq API in the environment this work was
done in** (no network route to `api.groq.com`; no `GROQ_API_KEY` configured). Before merging,
run it against real traffic:

```powershell
python test_calibration_sample.py
python batch_classify.py --limit 20   # or however many recent worker-style reports you have
```

and confirm severity is no longer clustering at 5 for reports that don't describe a genuinely
fatal-mechanism scenario. If it's still skewed high, the next place to look is whether
`reasoning_effort="low"` combined with `max_tokens=500` is truncating the model's chain of
thought before it reaches the self-check paragraph - consider raising `max_tokens` back toward
1200 (it was cut to 500 in `57ff065`, ostensibly for Groq TPM budget, but that leaves very
little headroom for a `reasoning_effort="low"` model on an 8-field JSON response with a
`reasoning` string).

## Tests added

`backend/tests/test_worker_report_severity.py` - a fully mocked (no network) regression suite
that submits reports through `/reports/worker` with a deterministic fake classifier returning
each of severity 1-5, and asserts:

- the immediate API response reflects the classifier's severity exactly,
- the row handed to `db.insert_prediction` matches exactly,
- STEP 3 (`recommended_check` patch) never mutates `severity` (explicit assertion),
- five reports submitted back-to-back with different underlying severities produce five
  different displayed severities, not a flat wall of one value - the literal symptom this bug
  report describes.

These tests pass, confirming the code-level pipeline is not the source of the bug (it was
already fine) and will now catch a regression if a future change ever does introduce one.

## Tracing added for future incidents

Structured `severity_trace stage=...` log lines were added at each checkpoint the ticket asked
to inspect (`api/routes.py` after classification and immediately before `insert_prediction`;
`db.py` inside `insert_prediction`; `repository.py` on each row read at debug level). Filtering
logs for `severity_trace` and a `report_id` now shows the value at every hop without needing to
re-instrument the code by hand next time.
