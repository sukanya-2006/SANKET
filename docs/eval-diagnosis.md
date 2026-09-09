# Why the baseline appears to beat the LLM

**Written 9 Sep, from `eval/llm_vs_baseline_results.csv` and `eval_run_log.txt`.**
**Nothing here is a reason to abandon the LLM. Two of the three causes are measurement
artefacts, and the third is a one-line prompt fix.**

---

## The headline that isn't real

`eval/eval_summary.md` reports:

| | F1 | PR-AUC |
|---|---|---|
| Baseline | **0.970** | 0.963 |
| LLM | 0.740 | 0.748 |

`eval_run_log.txt`, from `eval/run_eval.py`, reports the same baseline at **F1 0.784**.

Same model, same data, two numbers. The difference is that **`run_full_eval.py` scores the
baseline on its own training data.**

It calls `classifier_base.classify()`, which loads `backend/app/baseline_model.joblib`. That file
is written by `train_baseline.py`, which ends with `pipeline.fit(X, y)` — a deliberate retrain on
every label so the *shipped fallback* is as strong as possible. Correct for shipping; fatal for
measurement. Every synthetic report it is then scored on was in its training set.

**F1 0.970 on 144 reports is the fingerprint of memorisation.** `eval/run_eval.py` refits the
pipeline inside each cross-validation fold precisely to avoid this, and gets 0.784.

**Use 0.784. Do not put 0.970 in front of an ML judge** — "isn't that your training set?" is the
first question, and the answer is yes.

---

## The real comparison, and where the LLM actually loses

Honest numbers: **baseline 0.784, LLM 0.719.** The baseline is still ahead. Here is why.

LLM confusion matrix on the 144 synthetic reports:

```
TP 57   FN 28   FP 12   TN 47
```

It **misses 28 real precursors** and false-alarms on only 12. That is not a model that fails to
understand the task — it is a model tuned too conservative.

**Of those 28 misses, 23 are severity.** The LLM scored `severity < 4` where the humans scored
≥ 4. **82% of every mistake the LLM makes is one gate**, and it is the same gate the two human
annotators agreed on only 60% of the time.

Severity shift, LLM minus human, across all 172 reports:

```
-4:  1    -3:  5    -2: 15    -1: 35    0: 52    +1: 29    +2:  7
mean -0.28
```

Systematically low, not random.

---

## The root cause: the prompt and the labels disagree about the base rate

The gold set is **59% precursors**.

The prompt in `backend/app/classifier_llm.py` says:

> *"across a large set of real safety reports where a hazard was present, only roughly one in
> five plausibly escalates to a life-altering or fatal outcome. If you find yourself scoring 4 or
> 5 for most reports you read, you are almost certainly over-scoring — stop and re-examine..."*

**We are explicitly instructing the model to expect ~20% and penalising it against a ground truth
of 59%.** It is obeying its instructions and being marked wrong for it. That single paragraph is
a plausible explanation for most of the 23 severity-driven misses.

This was not a careless edit. Member 2 added that guidance because the model *was* over-scoring
against the earlier labels — the correction was right for the data as it stood then. The labels
have since moved.

---

## Which base rate is correct?

This is the question the team has to answer, and it is not a modelling question.

- **The master plan designed for 20–25%** and says "never rebalance — it flatters every model."
- **The gold labels say 59%.**
- The evaluation flags it itself: `[!] outside the plan's 20-25% band`.

Either the dataset is genuinely more hazardous than intended, or severity is being scored too
generously in the labels. Recall that human severity agreement was **60%** even in the good
round, and that severity is what gates the label — so the ground truth is weakest exactly where
it matters most.

Whatever the answer, **the prompt and the labels must agree.** They currently pull in opposite
directions, and the LLM is being scored on the gap.

---

## What to do, in order

1. **Stop quoting 0.970.** Use `eval/run_eval.py`'s cross-validated numbers. Consider deleting or
   clearly labelling `run_full_eval.py`, which cannot produce an honest baseline figure as written.
2. **Fix the 5 fallback rows.** `eval_run_log.txt` warns that 5 of 114 "LLM" answers were baseline
   answers. Run `reclassify_fallbacks.py` and re-run. It will not close a 0.065 gap alone, but the
   number is not clean until it is done.
3. **Settle the base rate**, then align the prompt to it. If 59% is correct, the "one in five"
   paragraph must go. If 20–25% is correct, the labels need a severity re-pass.
4. **Re-run and re-judge.** Only after 1–3 does the baseline-vs-LLM comparison mean anything.

## If the gap survives all of that

Say so plainly. *"We built both, measured them honestly, and on this dataset the keyword baseline
held up"* is a legitimate finding, and a team that reports it has more credibility than one whose
model conveniently wins. The pitch would shift from "look at the gap" to "we can tell you when a
simple method suffices, which is worth knowing before anyone buys an LLM licence."

That is a fallback position, not the expected outcome. Do 1–3 first.

## The OSHA number needs its own answer

**LLM on OSHA: F1 0.133–0.286, recall 0.100–0.200.** On real writing it finds roughly one
precursor in five to ten. That is the generalisation table, and a judge will ask about it.

The same base-rate mismatch applies, and OSHA narratives are terser than our synthetic ones, so
expect the conservative prompt to hurt more here. Re-check after step 3 before deciding what this
table says.
