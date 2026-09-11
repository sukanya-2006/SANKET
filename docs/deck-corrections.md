# Deck corrections — SIH idea submission

**11 September.** Two slides carry numbers that are no longer true. Slide 6's evaluation
figures were measured under a prompt we no longer ship, and slide 3 names the wrong database.

Paste-ready replacements below. Everything is reproducible from the repo — the commands are in
[../eval/eval_summary.md](../eval/eval_summary.md).

---

## Slide 3 — TECHNICAL APPROACH

**Currently says:** `React • FastAPI • Python • Groq • GPT-OSS-20B • TF-IDF • SQLite`

**Replace with:**

```
React • FastAPI • Python • Groq • GPT-OSS-20B • TF-IDF • Supabase (Postgres)
```

SQLite is still in the system, but only as the classification cache on the API instance. The
data lives in Supabase Postgres — 180 labelled reports (150 synthetic, 30 OSHA), 533 human
labels, and an append-only prediction log. The `reports` table holds more rows than that, but
the extras are submissions the worker demo wrote in and they carry no labels, so 180 is the
corpus number and the one every other document uses. Saying SQLite undersells it and invites a
question about whether this scales.

The rest of slide 3 is accurate. The flow line and the SIF rule both still hold.

---

## Slide 6 — RESEARCH AND REFERENCES

> ### 11 September, later the same day — the LLM figure is withdrawn
>
> An adversarial audit found that the shipped prompt contained a **held-out report**, with an
> instruction to score it the opposite of its gold label, and separately disclosed the set's
> precursor base rate six lines after telling the model it had no such information.
>
> Every LLM F1 this project has quoted — 0.719, 0.776, 0.822 — was measured under a prompt
> holding part of its own answer key. **None of them goes on a slide.** The prompt is fixed
> (`...-clean1`), and a re-measurement needs a full re-classification pass, which the Groq free
> tier caps at about 63 reports a day.
>
> The TF-IDF baseline's 0.754 is unaffected and still quotable — it never saw the prompt.
>
> If the deck is due before the re-run finishes, present the baseline number, the labelling
> story, and the Gate 2 diagnosis, and say the LLM figure is being re-measured after we found
> our own leak. That is a stronger position than a number that dies on the first follow-up.



**Currently says:**

```
Synthetic LLM F1: 0.719 ± 0.044*
OSHA F1: 0.286
OSHA Precision: 0.500
OSHA Recall: 0.200
*5/114 synthetic predictions used fallback.
```

Those came from a run under prompt **v3**, whose Gate 3 section told the model that "roughly
one in five" reports escalate to a fatal outcome. Our synthetic set runs at 58.7%, so the model
was penalised for obeying an instruction. The footnote about fallbacks had its own cause: the
cache was storing baseline answers under the primary's key, so once a report was answered by
the stub it stayed that way. Both are fixed.

**Replace with:**

```
Prototype Evaluation:
● TF-IDF baseline: F1 0.754 ± 0.077, PR-AUC 0.847 — 5-fold CV, n=114
● LLM: re-measurement in progress — the prompt it was scored under contained
  a held-out report, so the previous figure is withdrawn
● OSHA generalisation: F1 0.118 (n=30 — too small to conclude from)
● Labels: 180 reports, two annotators, written rubric (v2.2). Round 1 independent:
  52% agreement, kappa 0.083 — so we rewrote the severity gate. Round 2: 96%, but
  not run independently — not a ceiling.
```

### Why this ordering is the strongest version

Lead with the comparison. **The LLM is now ahead of the baseline** — it was behind two days
ago (0.719 against 0.784), and what changed was a prompt bug, not the model. That is a better
story than a flat number, because it shows the evaluation was honest enough to catch our own
mistake.

Then the labels, and say the whole arc. *"Our first labelling round was independent and agreed
52% — kappa 0.083. Severity was the gate that split us, so we rewrote it. The second round
agreed 96%, but it was not run independently, so we do not quote it as a ceiling — it is
evidence the revision worked, not a bound on the system."* That is the answer to "you wrote the
reports and graded yourself": not one number no competitor will have, but a rubric revision no
competitor will have measured before and after, on the gate that was actually failing. To claim
a ceiling we would need a fresh independent pass, and we would rather report that number than
one we cannot defend.

### Three things to say before a judge asks

**The two rows are not on the same pool.** The baseline is cross-validated over 114 reports;
the LLM is scored on the 71 with both a gold label and a stored prediction under g2fix1 — the
same 71 as on the slide. Say "indicative", not "decisive".

**Our precursor rate is 58.7%, not the 20–25% the problem statement cites.** The generator
centred every synthetic report on a hazard category, so almost every report clears Gate 1. It
does not affect the baseline-versus-LLM comparison, which runs on the same data for both. Say
it first, with the reason.

**We do not quote F1 0.970.** `train_baseline.py` refits the shipped model on every label so
the live fallback is as strong as possible, which means it has seen every report it would be
scored on. The cross-validated 0.754 is the real number, and "isn't that your training set?" is
the first question an ML judge asks.

---

## What else could go on slide 6 if there is room

The most interesting finding is not a number, it is a diagnosis.

```
● Failure analysis: 100% of remaining misses trace to one gate (control status),
  not to the model's comprehension. Fixed in prompt g2fix1.
```

Gate 1 agreement is 92%, severity is within one band 82% of the time, but Gate 2 sits at 63%
on synthetic and 33% on OSHA. One prompt line caused it — *"Silence about controls is
'unclear', never 'absent'"* — applied to reports that explicitly state a control was missing.
"No gas test was recorded" is evidence, not silence, and `unclear` forces the label false
regardless of severity.

A team that can say which gate is failing and why has demonstrably measured its own system.

---

## Two numbers that must never reach a slide

**`median_triage_seconds`** from `/aggregate/summary`. The synthetic reports carry generated
timestamps, so it measures the generator, not the system.

**Cohen's kappa 0.922, as a ceiling.** Settled on 11 September: round two was not run
independently — the annotators worked differently the second time, so 0.922 measures agreement
reached with contact, not two independent judgements. The slide keeps the 96% only where it
belongs — beside the round-one figure it improved on, marked *not independent* — and the kappa
stays off the deck entirely. A fresh independent re-label of a ~40-report subset, no contact
between annotators, is a couple of hours' work and gives a kappa we can quote without a caveat.
Nothing short of that turns 0.922 into a ceiling.
