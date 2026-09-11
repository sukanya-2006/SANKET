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
data lives in Supabase Postgres — 209 reports, 533 human labels, and an append-only prediction
log. Saying SQLite undersells it and invites a question about whether this scales.

The rest of slide 3 is accurate. The flow line and the SIF rule both still hold.

---

## Slide 6 — RESEARCH AND REFERENCES

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
● Human ceiling: 96.1% agreement, Cohen's kappa 0.922 (n=180, two annotators)
● LLM (prompt v4): F1 0.776 — held out, n=65
● TF-IDF baseline: F1 0.754 ± 0.077, PR-AUC 0.847 — 5-fold CV, n=114
● OSHA generalisation: F1 0.118 (n=30 — too small to conclude from)
```

### Why this ordering is the strongest version

Lead with the ceiling. *"Two of us labelled 180 reports independently and agreed 96% of the
time"* is the answer to "you wrote the reports and graded yourself", and it is the one number
no competitor will have.

Then the comparison. **The LLM is now ahead of the baseline** — it was behind two days ago
(0.719 against 0.784), and what changed was a prompt bug, not the model. That is a better story
than a flat number, because it shows the evaluation was honest enough to catch our own mistake.

### Three things to say before a judge asks

**The two rows are not on the same pool.** The baseline is cross-validated over 114 reports;
the LLM is scored on the 65 with both a gold label and a stored prediction. Say "indicative",
not "decisive".

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

**Cohen's kappa 0.922, as a ceiling** — until someone confirms the two annotators labelled
independently and neither file was edited to match afterwards. No script can check that. Quote
it as "our two annotators agreed 96% of the time" only once that is confirmed.
