# Evaluation summary

**Regenerated 11 September.** Everything below is measured against the 173-row gold set in
`data/gold_labels.csv`, with `is_sif_precursor` derived from the three gates rather than read
from the typed column.

Reproduce with:

```bash
python eval/run_eval.py --no-llm          # baseline, 5-fold cross-validated
python score_stored_predictions.py        # LLM, scored from what is already in Supabase
python agreement.py                       # the human ceiling
```

---

## The three numbers to quote

| | F1 | how it was measured | n |
|---|---|---|---|
| **Human ceiling** | 96.1% agreement, **kappa 0.922** | two annotators, independently | 180 |
| **LLM, prompt v4** | **0.776** | held out; the model never saw the labels | 65 |
| **TF-IDF baseline** | **0.754** ± 0.077 | 5-fold cross-validated, refit inside each fold | 114 |

PR-AUC for the baseline is 0.847 ± 0.032.

**The LLM is now ahead of the baseline.** It was behind as recently as 9 September (0.719
against 0.784), and the thing that changed was a prompt bug, not the model.

### Say this out loud before anyone asks

The two rows are **not scored on the same pool**, so treat the gap as indicative rather than
decisive. The baseline is cross-validated over 114 reports; the LLM is scored on the 65 that
have both a gold label and a stored prediction under that prompt version. Putting both on one
pool needs a full re-run, which is a token-budget problem rather than a hard one — see the
rate-limit note at the bottom.

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

**The g2fix1 numbers are not measured yet.** Re-run `batch_classify.py` and then
`score_stored_predictions.py` before quoting anything for it. Nothing in the table above
includes this change.

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
