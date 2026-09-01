# Hand-off — Member 2 (ML)

You own both classifiers, the prompt, and the `ClassificationResult` schema.

**Status: both classifiers are written. Neither is finished.**

- `classifier_llm.py` — Groq (`openai/gpt-oss-20b`), prompted with rubric v2.1, **registered and
  answering**. Needs `GROQ_API_KEY`.
- `classifier_base.py` — TF-IDF + logistic regression, written but **untrained**. It needs
  `app/baseline_model.joblib`, which `train_baseline.py` produces once `data/gold_labels.csv`
  exists. Until then the fallback path answers with the keyword stub, which is weaker than the
  baseline the pitch describes.

Registration is already wired defensively in `main.py` for both slots — the baseline plugs itself
in the moment the model file appears, so there is no code change to remember on demo day.

**What is left for you:** train the baseline the hour labels land, then tune the prompt on the
~30-report dev split. Score the baseline *before* comparing — the baseline-vs-LLM gap is only
evidence if the baseline was a real attempt rather than a strawman built afterwards.

---

## What is already done for you

- `ClassificationResult` is defined in [backend/app/schemas.py](../../backend/app/schemas.py),
  matching master plan §5 and [NAMES.md](../../NAMES.md).
- The whole pipeline around you — cache, wall-clock timeout, retry-once-on-schema-failure,
  fallback to baseline, `is_fallback` propagation, schema-failure-rate metric — is built and
  tested in [backend/app/classifier.py](../../backend/app/classifier.py).
- Ten tests exercise that machinery with deliberately broken classifiers: malformed output,
  connection failure, timeout, both-classifiers-down, cache hit, missing API key.

**You do not edit `classifier.py`.** You write two functions; registration is already wired.

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

Registration already happens in `backend/app/main.py`, wrapped in try/except for both slots. If
your module fails to import — missing package, missing key, missing model file — the API starts
on whatever is available and logs the reason, rather than refusing to boot. **Do not remove that
guard**: a deployment that cannot start has no degraded mode at all, and the frontend needs a
running API regardless of your key.

---

## The two classifiers

### Baseline — `backend/app/classifier_base.py` (written, untrained)

scikit-learn, TF-IDF → logistic regression. Its own train/test split, stated explicitly.
Explainability is the top-weighted words:

```python
sorted(zip(vec.get_feature_names_out(), model.coef_[0]))
```

No SHAP. The baseline predicts `is_sif_precursor` with real ML and fills the other schema fields
with coarse, honest heuristics. It is allowed to be worse — that is the point of it.

**It needs `app/baseline_model.joblib`.** Run `python train_baseline.py` from the project root the
hour `data/gold_labels.csv` lands. Until then the module raises on import, the guard catches it,
and the fallback path answers with the keyword stub — which is weaker than the baseline the pitch
describes, so this is worth doing immediately rather than on day 12.

### Real classifier — `backend/app/classifier_llm.py` (written, live)

Groq, `openai/gpt-oss-20b`, prompted with rubric v2.1, registered in the primary slot. Needs
`GROQ_API_KEY`. The client is built lazily, so a missing key degrades rather than killing the app.

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
- **The timeout is currently 25s**, raised from 10 to reduce false fallbacks under batch load.
  That is a long silence on stage, and the demo plans to *show* the fallback. Worth revisiting —
  or splitting: a long timeout for `batch_classify.py`, a short one for the live box.

Tune on the ~30-report dev split only. The held-out set opens exactly once, at the end.

---

## What "done" looks like

```bash
cd backend
../.venv/Scripts/python.exe -m pytest -q          # still 36 passing
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload
curl localhost:8000/health
```

`/health` should name **both** slots as yours — `primary_classifier` the Groq version and
`baseline_classifier` the TF-IDF one, neither showing `stub-0.1.0`. Then `/meta` shows a real
`schema_failure_rate`, and killing your network mid-request returns `is_fallback: true` rather
than an error.

---

## Your hostile questions

- *Understanding vs pattern-matching* — it is sophisticated pattern-matching, and that is enough
  for a reading-comprehension task. Do not overclaim.
- *Why not fine-tune* — 180 examples would overfit; prompting wins at this scale.
- *What TF-IDF actually does* — counts weighted words, no meaning. That is exactly why the gap to
  the LLM is meaningful evidence rather than a benchmark.
- *What happens on hallucination* — schema-constrained, retry once, then human review via the
  baseline, and the rate is logged. Point at `/meta`.
