# Hand-off — Member 2 (ML)

You own both classifiers, the prompt, and the `ClassificationResult` schema. Everything that
consumes your work already exists and is under test, so you can build in isolation and plug in
when ready.

**Build the baseline first, and score it before you write the LLM classifier.** The gap between
them is the strongest thing in the pitch, and it only exists if the baseline is a real attempt
rather than a strawman built afterwards.

---

## What is already done for you

- `ClassificationResult` is defined in [backend/app/schemas.py](../../backend/app/schemas.py),
  matching master plan §5 and [NAMES.md](../../NAMES.md).
- The whole pipeline around you — cache, 10-second timeout, retry-once-on-schema-failure,
  fallback to baseline, `is_fallback` propagation, schema-failure-rate metric — is built and
  tested in [backend/app/classifier.py](../../backend/app/classifier.py).
- Nine tests already exercise that machinery with deliberately broken classifiers. Run
  `pytest -q` in `backend/` and you will see them pass before you write anything.

**You do not edit `classifier.py`.** You write two functions and register them.

---

## The contract

```python
def my_classifier(report_text: str) -> ClassificationResult | dict: ...
my_classifier.version = "claude-sonnet-4-5-v1"   # goes into predictions.model_version
```

Return either a `ClassificationResult` or a plain dict. **Returning a dict is preferred for the
LLM** — it gets validated by Pydantic in `classifier._coerce`, so malformed model output triggers
retry-then-fallback instead of a half-built object reaching the database. That validation is
where the schema-failure rate comes from; if you validate inside your own function and swallow
the error, the metric silently becomes zero and we lose the answer to "what happens when it
hallucinates".

Register at import time, in `backend/app/main.py` after the app is created:

```python
from . import classifier
from .classifier_base import baseline
from .classifier_llm import llm

classifier.register_baseline(baseline)
classifier.register_primary(llm)
```

Until you do, both slots hold the keyword stub and the API works — that is why the frontend could
start on day 3.

---

## Files to create

```
backend/app/classifier_base.py    TF-IDF + logistic regression, ~30 lines
backend/app/classifier_llm.py     one structured Claude call
```

### Baseline

scikit-learn, TF-IDF → logistic regression. Its own train/test split, stated explicitly.
Explainability is the top-weighted words:

```python
sorted(zip(vec.get_feature_names_out(), model.coef_[0]))
```

No SHAP. The baseline predicts `is_sif_precursor` and a `severity`; fill `hazard_assessment`,
`lsr_rule` and `control_status` as best it can and set `reasoning` to something honest like
`"keyword baseline: top features were ..."`. It is allowed to be worse — that is the point of it.

### LLM classifier

One structured call per report returning the full locked schema. Add `anthropic` to
`backend/requirements.txt`. Read the `claude-api` skill reference before writing it rather than
working from memory — model IDs and structured-output parameters change.

Points that will be attacked, so get them right:

- **`confidence` must be a real float 0–1.** PR-AUC is not computable without it. A model that
  always answers 0.9 makes the metric meaningless.
- **`flagged_phrases` must be verbatim substrings of `report_text`.** The UI highlights them with
  `indexOf`. A test asserts this for the stub; write the same assertion for yours.
- **Multilingual is handled inside the prompt** — Hindi, Hinglish, code-mixed. No separate
  pipeline, no translation step.
- **Do not let the prompt restate the rubric loosely.** Gate 2 `present` means the barrier held
  and the report is *not* a precursor. If the prompt blurs that, every barrier-held case becomes
  a false positive and the ambiguous demo case stops working.
- **Bump `PROMPT_VERSION` in `.env` whenever the prompt changes.** It is part of the cache key,
  so forgetting means an eval quietly mixes answers from two prompts.

Tune on the ~30-report dev split only. The held-out set opens exactly once, at the end.

---

## What "done" looks like

```bash
cd backend
./.venv/Scripts/python.exe -m pytest -q          # still 34+ passing
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
curl localhost:8000/health                        # primary_classifier is yours, not stub-0.1.0
```

Then `/meta` shows a real `schema_failure_rate`, and killing your network mid-request should
return `is_fallback: true` rather than an error.

---

## Your hostile questions

- *Understanding vs pattern-matching* — it is sophisticated pattern-matching, and that is enough
  for a reading-comprehension task. Do not overclaim.
- *Why not fine-tune* — 180 examples would overfit; prompting wins at this scale.
- *What TF-IDF actually does* — counts weighted words, no meaning. That is exactly why the gap to
  the LLM is meaningful evidence rather than a benchmark.
- *What happens on hallucination* — schema-constrained, retry once, then human review via the
  baseline, and the rate is logged. Point at `/meta`.
