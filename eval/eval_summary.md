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

## We have a ceiling now

**11 September.** Both annotators independently re-labelled a 40-report subset under rubric
v2.2, with no contact until both files were finished. Reproduce with `python score_recheck.py`.

| | agreement | kappa |
|---|---|---|
| **`is_sif_precursor`** | **37/38 — 97.4%** | **0.947** |
| `lsr_rule` | 38/38 — 100% | 1.000 |
| Gate 2 `control_status` | 36/37 — 97.3% | 0.956 |
| Gate 3 `severity`, exact | 36/38 — 94.7% | 0.926 |
| Gate 3 `severity`, within one band | 38/38 — 100% | — |
| Gate 1 `hazard_assessment` | 37/38 — 97.4% | n/a |

Exactly **one** headline disagreement in 38 reports: report 46, severity 3 against 4, on the
boundary that defines the label.

**Gate 1's kappa is suppressed, not zero.** Both annotators answered `yes` on 37 of 38, so
there is almost no variance for chance agreement to be measured against, and kappa collapses
toward zero at near-total agreement. Printing 0.000 there would read as total disagreement and
be exactly backwards. Raw agreement is 97.4%.

### Two caveats to say before a judge asks

**n = 38.** The confidence interval is wide. Quote it as "on a 38-report independent subset",
never as a flat 0.947.

**These are re-labels.** Both annotators had seen these reports in earlier rounds, so
familiarity flatters the number against two people reading them cold. It is a genuine ceiling
for *this* pair applying *this* rubric; it is not a claim about how legible the task is to a
stranger.

Two rows were excluded as incomplete rather than guessed at: akanksha left report 3 blank and
sukanya left report 52's severity blank. A missing judgement is not a disagreement, and
counting it either way would move the number.

---

## The one number to quote

| | F1 | how it was measured | n |
|---|---|---|---|
| **TF-IDF baseline** | **0.754** ± 0.077 | 5-fold cross-validated, refit inside each fold | 114 |

PR-AUC 0.847 ± 0.032. This one is sound: the baseline never saw the prompt, so nothing that
happened to the prompt affects it.

### The LLM number is retracted. Do not quote 0.822 or 0.776.

Both were measured under prompts that contained part of their own answer key.

The Gate 3 worked example about a two-foot fall onto a steel floor was **report 113 nearly
verbatim**, and it instructed the model to score that report 2. Report 113 is in the
**held-out** split, and its gold label is severity 5, `is_sif_precursor` true. So the prompt
guaranteed a wrong answer on a scored report, and `docs/hostile-qa.md` rehearsed the line "we
opened the held-out set exactly once".

A second leak sat six lines below an instruction forbidding it. The prompt said "You have no
reliable information about the base rate of the set you are reading" and then, parenthetically,
"our own labelled set runs at roughly 59% precursors". `docs/eval-diagnosis.md` records that
paragraph as removed. It was not removed — the wrong number had been swapped for the right one.
Telling a model the base rate of the set it is scored against is leakage whether the number is
right or wrong, and it is most of the 0.719 → 0.822 move.

Both are gone. `classify.version` is now `...-clean1`.

### What it takes to get an LLM number back

```bash
python batch_classify.py            # re-classify under clean1
python score_stored_predictions.py  # now excludes the dev split
```

`score_stored_predictions.py` previously had no concept of `eval/split.json`, so 14 of the 73
scored reports were dev reports the prompt was tuned on. It loads the split now and prints the
pool size before and after excluding them.

Budget the re-run in days, not minutes — see the rate limit note at the end.

### The honest position until then

We have a cross-validated baseline at 0.754, an independent human ceiling of kappa 0.947,
and no current LLM figure. That is a worse table
than the one we had this morning and a much better answer under questioning, because every
number in it survives the follow-up question.

---

## Where the labels came from, and what the agreement numbers mean

Round one was independent: two annotators labelled 180 reports separately and agreed on
**52.2%**, Cohen's kappa **0.083**. Severity was the broken gate — 14.4% agreement, splitting
3–4 points on 76 of the 180.

That triggered a documented rubric revision, **v2.1 → v2.2**, rewriting the severity gate: the
one-change rule is stated first, and the bands were changed from adjectives to observable
outcomes.

> **BOTH LABELLING ROUNDS USED RUBRIC v2.1.** Confirmed by Member 1 on 11 September, and
> consistent with all 173 rows in `data/gold_labels.csv` recording `rubric_version 2.1`.
>
> So the move from 52.2% to 96.1% **cannot be attributed to the v2.2 revision** — the revision
> was never applied to a label. The one thing known to differ between the rounds is that the
> second was not run independently, which is the simplest explanation for the whole jump.
>
> A second consequence, easy to miss: the shipped prompt encodes **v2.2** (the one-change rule,
> the observable-outcome severity bands) while the gold labels encode **v2.1**. Part of every
> model-versus-gold disagreement is therefore a rubric mismatch rather than model error, and it
> lands hardest on Gate 3 — exactly where the disagreements are. Any future re-labelling should
> be done under v2.2 so the model and the labels are graded against the same document.

Round two scored 96.1% agreement, kappa 0.922 — **round two, not independent, not a ceiling**.
The annotators did not work separately the second time, so those numbers are evidence that the
revision helped. They are not a bound on the model, and must never be quoted as a ceiling or as
a number to beat.

The gold set stands at 173 agreed reports, with 7 still open (10, 20, 51, 60, 96, 139, 149).

That fresh independent pass has now been run - see the ceiling section at the top of this
file. kappa 0.947 on 38 scorable reports, under rubric v2.2.

---

## What changed, and why the old numbers were wrong

The deck currently carries **LLM F1 0.719** and a footnote that 5 of 114 predictions used the
fallback. Both come from a run under prompt **v3**, which is not what we ship.

v3's Gate 3 section told the model that "roughly one in five" reports escalate to a fatal or
life-altering outcome. Our synthetic set runs at 58.7% — 84 of the 143 synthetic reports in
the gold set — because the generator centred every report on a hazard category. The model
obeyed the instruction and was marked wrong for it — 82% of its misses were severity scored
below 4 where the humans scored 4 or above.

That paragraph is gone. The calibration is now close to right. Both columns below are the
**scored subset** — the synthetic reports that had a stored prediction under the previous
prompt, the n=65 row in the table at the top of this file — which is why the gold column here
is not the 58.7% measured over all 143:

| | gold | model |
|---|---|---|
| synthetic precursor rate, scored subset | 64.6% | 66.2% |

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
at 58.7% — 84 of the 143 synthetic reports in the gold set — because the generator centred
every synthetic report on a hazard category. Say that first, with the reason, rather than
letting a judge find it.

---

## The rate limit, because it governs what can be re-measured

Groq's free tier caps tokens twice: ~8,000 per minute and **200,000 per day**. The system
prompt is ~2,650 tokens and `max_tokens` is 500, so one report costs ~3,150 against both.

| | |
|---|---|
| reports per day | **~63** |
| full 180-report pass | ~567,000 tokens, about 2.8 days |

`batch_classify.py` paces at 25s, refuses to store a fallback, and is resumable and
version-aware, so an interrupted run picks up exactly where the cap stopped it. Plan re-runs
around days, not minutes.
