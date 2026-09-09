# The database is live — what running against it found

**9 September.** Supabase is connected, the schema is applied, 180 reports and their labels are
in Postgres, and the aggregation SQL has now executed against a real database for the first time.

Until today the live path was written but never run. `repository.py` said so in its own
docstring. Everything below is a bug that only appears once a real database is behind the API,
which is why none of it showed up in 37 passing tests.

---

## Status

| | |
|---|---|
| `/health` (local) | `database: connected` |
| `reports` | 180 — 150 synthetic, 30 OSHA |
| `gold_labels` | 534 — akanksha 180, sukanya 180, agreed 174 |
| `predictions` | append-only, multiple versions retained |
| Aggregation SQL | all eight statements execute and return rows |

The SQL itself was correct. Every statement in `app/sql/aggregates.sql` ran first time and
returned sensible results. What was broken was everything around it.

---

## Six bugs, none of which raised an error

### 1. The aggregates were empty, and nothing said why

Every `/aggregate/*` query filters `l.model_version = :model_version` against the version the
API currently ships. The database held predictions from `...rubric-v2.1-g3fix3`. Under the
current version, `sites_ranked` returned 0 rows, `activities_ranked` 0 rows, `rules` 0 rows.
Under the stored version, the same queries returned 7, 6 and 19.

A dashboard wired to this would have rendered empty panels with a 200 status and no log line.

### 2. `batch_classify.py` refused to fix it

Its skip query was `SELECT DISTINCT report_id FROM predictions` — any report classified under
any version counted as done. So the one script that could refresh the stale rows reported
"nothing to do" and exited cleanly.

The two failures compound: the prompt moves to v4, the version string moves with it, every
aggregate goes quiet, and the tool you would reach for tells you there is nothing to fix. Fixed
by making the skip version-aware, which also makes `reclassify_all.py` redundant.

### 3. `latest_predictions` is the wrong view to aggregate over

The view picks the newest prediction per report *across all versions*. The aggregates then
filter by version — after the row has already been chosen. A report whose newest row belongs to
some other version is not re-resolved to its own row for the version requested. It disappears
from the result entirely.

This is not hypothetical. A classifier run that fell back to the baseline wrote 111
`stub-0.1.0` rows, which became the newest rows for 111 reports. Every one of them would have
dropped out of the site and activity rankings, silently, and the ranking would still have
looked plausible.

`latest_predictions_by_version` partitions by `(report_id, model_version)` first, so the filter
selects among rows that are each already the newest for their own version. The original view
stays, because `repository.py` genuinely wants the newest row regardless of version — what do
we currently think about this report. Both views now exist and a test pins which reads which.

### 4. `groq==0.13.0` cannot call the classifier

`classifier_llm.py` passes `reasoning_effort` to `chat.completions.create`. The 0.13 client
rejects it with a `TypeError`, `classifier.py` catches it, the baseline stub answers, and the
response comes back with `is_fallback: true`. No exception surfaces.

A clean `pip install -r backend/requirements.txt` produced an API that passed its health check,
answered every request, and never once called the model. The first batch run wrote 111 stub
rows before this was spotted — they are still in the table, because the table is append-only
and a run where the model was unreachable is exactly the kind of thing that log is for.

Pin corrected to `groq>=1.7.0`.

### 5. The cache made a bad minute permanent

This is the worst of them, and it is the one that took longest to see.

`classifier.py` cached the baseline answer alongside real ones, deliberately — the comment
said it kept a demo that fell back consistent. The cache has no expiry. So a report answered
by the stub once is answered by the stub forever: every later call returns it instantly, with
no error, no log line, and no network request. There is no path back except deleting the row.

The broken-client run above wrote **56 stub answers into the cache under the current prompt
version**. Those 56 reports were then permanently downgraded, on this machine and on any
deployment sharing the cache.

It hid the underlying problem for an hour. Calling `classifier_llm.classify` directly worked
perfectly. Calling `classifier.classify` on the same text returned a fallback with nothing
logged, because it never got as far as the model. The two observations look contradictory
until you notice the cache sits between them.

Fallback answers are no longer cached. A degraded answer that gets recomputed and succeeds
next time is not an inconsistency — it is the system recovering, which is the entire point of
having a degraded mode. The 59 poisoned rows have been purged; the 12 real answers were kept.

### 6. `batch_classify.py` stored the stub answers as if they were data

Separately from the cache: when the model was unreachable, the batch wrote the baseline's
answer into `predictions` and printed it as a success. 111 stub rows went into the table that
the dashboard and the eval both read, indistinguishable downstream from a real judgement
except by a boolean nobody was filtering on.

It now refuses to store a fallback, and stops after five in a row rather than grinding through
the rest of the set against the same wall. An unclassified report is recoverable — the next
run picks it up. A stub row looks like data forever.

### And the rate limit underneath all of it

The trigger for most of the above: Groq's free tier caps **tokens** per minute, not requests.
The system prompt is around 3,000 tokens and the observed ceiling is 8,000 TPM, which is
roughly **two calls a minute**. `batch_classify.py` paced at 1.5 seconds, issuing forty.

The retry loop made it worse. It backed off 3, 6 and 9 seconds against a bucket that refills
every ~25 seconds, then fell out of the loop with `response` still `None` and died on
`response.choices` — an `AttributeError` that `classifier.py` reported as a generic fallback,
hiding the rate limit completely. Backoff is now 30 and 45 seconds, exhaustion raises a message
that names the actual problem, and the batch paces at 25 seconds by default.

A full 180-report pass therefore takes about 75 minutes on this tier. That is the real number;
plan demos and re-runs around it.

---

## The deployed service

`https://sanket-backend-put3.onrender.com` is up. Its classifier works — a live `/analyze` call
returns `is_fallback: false` against the real model.

Its `/health` reports `database: not_configured`, so it is serving the seeded stub for every
aggregate. **`SUPABASE_DB_URL` needs setting in the Render dashboard**, not in the repo.

`render.yaml` also declared `ANTHROPIC_API_KEY`, which no code reads — the classifier looks for
`GROQ_API_KEY`. A service created from that file alone would have run the stub for every
request while reporting itself healthy. Corrected, along with the `PROMPT_VERSION` and
`LLM_TIMEOUT_SECONDS` values that should not be left to a default on a slower free-tier box.

---

## Agreement, computed from the database rather than a merged file

`gold_labels` keeps each annotator's raw row, so the ceiling is measurable directly. Run
`python agreement.py`.

| | agreement | kappa |
|---|---|---|
| `is_sif_precursor` | 173/180 — 96.1% | **0.922** |
| Gate 1 `hazard_assessment` | 180/180 — 100% | 1.000 |
| `lsr_rule` | 176/180 — 97.8% | 0.974 |
| Gate 2 `control_status` | 162/164 — 98.8% | 0.978 |
| Gate 3 `severity`, exact | 108/180 — 60.0% | 0.452 |
| Gate 3 `severity`, within one band | 180/180 — 100% | — |

Two things worth saying out loud.

**Severity never disagrees by more than one band.** Not once in 180 reports. The gate with 60%
exact agreement is not chaotic; it is two people splitting hairs on a boundary, and six of the
seven headline disagreements straddle the 3/4 line that defines the label.

**Gate 1 agreement is perfect because the dataset is enriched.** Every synthetic report was
generated centred on a hazard category, so both annotators said `yes` almost every time. A
kappa of 1.000 here reflects the construction of the set, not the difficulty of the judgement.
Say that before a judge asks.

### This is a ceiling only if the labelling was independent

No script can check that, including `agreement.py`. If the two files were ever edited to match
after a discussion, 0.922 is not a ceiling and must not be quoted as one. **This is still
unconfirmed** and it is the one number in the pitch that depends on a fact about process rather
than about data.

---

## What the loader corrected, and why it is not relabelling

`load_gold_labels.py` applied 31 corrections across the three files. Every one is printed with
its `report_id` when the script runs. None is a judgement about a report.

**Ten rows spelled `lsr_rule` with a space** — `energy isolation`, `confined space` — in
akanksha's file, which the merged `gold_labels.csv` inherited verbatim. A space instead of an
underscore splits one rule into two buckets in every `GROUP BY`, under-counting it on the
dashboard and in eval. Normalised.

**Four rows carried a `control_status` where `hazard_assessment` was not `yes`.** Rubric §2:
there is no control to assess for a hazard we could not name. The schema rejects these outright
via a CHECK constraint. Set to NULL.

**Seven rows had a typed `is_sif_precursor` that contradicted the gates the same annotator
recorded.** The rubric says the field is derived, never typed. The loader recomputes it from the
gates in every row, so the CSVs' typed column is now advisory only.

That last one changed which reports the annotators disagree on, in both directions:

- Report **56** stopped being a disagreement. sukanya's gates said precursor; her typed column
  said not. The gates agree with akanksha. The disagreement was a data-entry artefact.
- Reports **51** and **96** became disagreements. akanksha's typed `True` had been masking a
  genuine Gate 3 split.

**Open tiebreaks are now 10, 20, 51, 60, 96, 139, 149** — seven, not the six previously
circulated. Six are Gate 3 at the 3/4 boundary; report 96 is Gate 2, `unclear` against `failed`.

### On the two agreement figures in circulation

Both are real; they measure different things.

| what is compared | result |
|---|---|
| `is_sif_precursor` alone — the label the product predicts | 96.1%, kappa 0.922 |
| all four fields matching exactly | 58.3% |
| the three gates matching exactly, ignoring `lsr_rule` | 59.4% |

The headline number is the one about the label we actually ship. Quote it as that, explicitly,
and give the severity breakdown alongside — not as a bare 96%.

---

## Reproducing this from a clean clone

```
pip install -r backend/requirements.txt
# backend/.env needs SUPABASE_DB_URL and GROQ_API_KEY. Both stay out of git.

python -c "import sys; sys.path.insert(0,'backend'); from app import db; db.apply_schema()"
python load_reports.py         # 150 synthetic + 30 OSHA
python load_gold_labels.py     # 534 human labels, prints every correction
python batch_classify.py       # one Groq call per report, resumable
python agreement.py            # the ceiling
```

`batch_classify.py` paces at 25 seconds per report to stay inside the free tier's token
limit, so budget about 75 minutes for a full 180-report pass. It is resumable: stop it and re-run, and it picks
up the reports that have no prediction under the current model version.
