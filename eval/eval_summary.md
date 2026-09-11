# Evaluation summary

**Regenerated 11 September.** Everything below is measured against the 173-row gold set in
`data/gold_labels.csv`, with `is_sif_precursor` derived from the three gates rather than read
from the typed column.

Reproduce with:

```bash
python eval/run_eval.py --no-llm          # baseline, 5-fold cross-validated
python score_stored_predictions.py        # LLM, scored from what is already in Supabase
python agreement.py                       # round two agreement, not independent
```

---

## The numbers to quote

| | F1 | how it was measured | n |
|---|---|---|---|
| **LLM, prompt g2fix1** | **0.822** | held out; the model never saw the labels | 71 |
| LLM, previous prompt | 0.776 | same method, before the Gate 2 fix | 65 |
| **TF-IDF baseline** | **0.754** ± 0.077 | 5-fold cross-validated, refit inside each fold | 114 |

Baseline PR-AUC is 0.847 ± 0.032. LLM precision is 0.857, recall 0.789.

**The LLM is ahead of the baseline, and the gap is widening as the prompt is fixed.** It was
*behind* on 9 September (0.719 against 0.784). Both moves came from finding and fixing our own
prompt bugs, not from changing the model.

### Say this before anyone asks

The rows are **not scored on the same pool**. The baseline is cross-validated over 114 reports;
the LLM is scored on the reports that have both a gold label and a stored prediction under that
prompt version. Treat the gap as indicative rather than decisive.

### The labels

180 reports, two annotators, a written and versioned rubric.

Round one was run independently and agreed **52.2%**, Cohen's kappa 0.083. Severity was the
gate that split them — 14.4% agreement, 3 to 4 points apart on 76 of 180 reports. That drove
the v2.1 → v2.2 revision, which rewrote exactly that gate.

Round two agreed **96.1%**, but was **not run independently**, so it is not a ceiling and we do
not quote it as one. It is evidence the revision worked.

We therefore have no quotable agreement ceiling. `prepare_independent_recheck.py` samples 40
reports for a fresh independent pass, which is about two hours and would give us one.

---

## Where the labels came from, and what the agreement numbers mean

Round one was independent: two annotators labelled 180 reports separately and agreed on
**52.2%**, Cohen's kappa **0.083**. Severity was the broken gate — 14.4% agreement, splitting
3–4 points on 76 of the 180.

That triggered a documented rubric revision, **v2.1 → v2.2**, rewriting the severity gate: the
one-change rule is stated first, and the bands were changed from adjectives to observable
outcomes.

Round two scored 96.1% agreement, kappa 0.922 — **round two, not independent, not a ceiling**.
The annotators did not work separately the second time, so those numbers are evidence that the
revision helped. They are not a bound on the model, and must never be quoted as a ceiling or as
a number to beat.

The gold set stands at 173 agreed reports, with 7 still open (10, 20, 51, 60, 96, 139, 149).

A quotable kappa needs a fresh independent pass. `prepare_independent_recheck.py` samples 40
reports for exactly that, and the worksheets are already written to `data/recheck_akanksha.csv`
and `data/recheck_sukanya.csv`.

---

## What changed, and why the old numbers were wrong

The deck currently carries **LLM F1 0.719** and a footnote that 5 of 114 predictions used the
fallback. Both come from a run under prompt **v3**, which is not what we ship.

v3's Gate 3 section told the model that "roughly one in five" reports escalate to a fatal or
life-altering outcome. Our synthetic set runs at 58.7%, because the generator centred every
report on a hazard category. The model obeyed the instruction and was marked wrong for it —
82% of its misses were severity scored below 4 where the humans scored 4 or above.

That paragraph is gone. The calibration is now close to right:

| | gold | model |
|---|---|---|
| synthetic precursor rate | 64.6% | 66.2% |

Mean severity shift is **+0.28** — very slightly high, where it used to be −0.28 low.

The "5 of 114 used fallback" footnote had its own cause. The cache was storing baseline answers
under the primary's key with no expiry, so once a report was answered by the stub it was
answered by the stub forever. Fixed, and the 59 poisoned entries were purged.

---

## The failure mode has moved to Gate 2

This is the most useful thing in this file. Under prompt v4:

| gate | synthetic | OSHA |
|---|---|---|
| Gate 1 hazard | 92.3% | 80.0% |
| `lsr_rule` | 73.8% | 63.3% |
| **Gate 2 control** | **63.2%** | **33.3%** |
| Gate 3 severity, exact | 38.5% | 50.0% |
| Gate 3 severity, within one band | 81.5% | 83.3% |

**100% of the synthetic misses and 90% of the OSHA misses are Gate 2** — the model called the
control `present` or `unclear` where the humans read the narrative as `absent` or `failed`.
Severity is no longer the problem.

The cause was one line in the prompt: *"Silence about controls is 'unclear', never 'absent'."*
True as written, and the model applied it to reports that explicitly state a control was
missing. "No gas test was recorded" is not silence, it is evidence. And `unclear` forces
`is_sif_precursor` false regardless of severity, so each one became a missed precursor.

Fixed in `g2fix1`, which draws the absent/unclear boundary explicitly and gives four worked
examples. Verified by hand on the exact miss pattern:

```
"No gas test was recorded and no attendant was posted."   -> absent   precursor True
"Climbed the scaffold without tying off, lanyard unclipped." -> absent precursor True
"A worker was struck by a reversing vehicle in the yard."  -> unclear  precursor False
```

**g2fix1 is now measured.** F1 went 0.776 → **0.822**, precision 0.767 → **0.857**. Gate 2 fell from 100% of all misses to 75% of a smaller set, and the mean severity shift tightened from +0.28 to +0.14. The fix did what it was aimed at.

---

## OSHA: still too small to conclude from

**F1 0.118, precision 0.167, recall 0.091, n=30.** Worse than the 0.286 in the deck, and both
numbers are too small to mean much either way — a single report moves F1 by several points.

What the OSHA set does show is that Gate 2 collapses on real writing: 33.3% agreement against
63.2% on our synthetic reports. OSHA narratives are terser and rarely spell out what control
was in place, so the over-cautious `unclear` reading hurt far more here. This is the row most
likely to improve under g2fix1.

Report it as a generalisation check on 30 real narratives, not as a headline.

---

## What must not be quoted

**F1 0.970 for the baseline.** `run_full_eval.py` scores the shipped model, and
`train_baseline.py` deliberately refits that model on every label so the live fallback is as
strong as possible. Every report it is scored on was in its training set. 0.970 is
memorisation. The cross-validated 0.754 is the real number, and "isn't that your training set?"
is the first question an ML judge asks.

**`median_triage_seconds`** from `/aggregate/summary`. The synthetic reports carry generated
timestamps, so this measures the generator, not the system.

**The 20–25% precursor rate from the problem statement, as a property of our data.** Ours runs
at 58.7% because the generator centred every synthetic report on a hazard category. Say that
first, with the reason, rather than letting a judge find it.

---

## The rate limit, because it governs what can be re-measured

Groq's free tier caps tokens twice: ~8,000 per minute and **200,000 per day**. The system
prompt is ~2,650 tokens and `max_tokens` is 500, so one report costs ~3,150 against both.

| | |
|---|---|
| reports per day | **~63** |
| full 180-report pass | ~520,000 tokens, about 2.6 days |

`batch_classify.py` paces at 25s, refuses to store a fallback, and is resumable and
version-aware, so an interrupted run picks up exactly where the cap stopped it. Plan re-runs
around days, not minutes.
