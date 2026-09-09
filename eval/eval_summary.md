> ### THE BASELINE NUMBER BELOW IS NOT A FAIR SCORE - DO NOT QUOTE IT
>
> This file is produced by `run_full_eval.py`, which scores the baseline using the **shipped**
> model. `train_baseline.py` deliberately retrains that model on **every** label so the live
> fallback is as strong as possible - so every report scored here was in its training set.
> **F1 0.970 is memorisation, not performance.**
>
> The number to quote comes from `eval/run_eval.py`, which refits the pipeline inside
> cross-validation folds: **0.784**. "Isn't that your training set?" is the first question an
> ML judge asks, and for 0.970 the answer is yes.
>
> The LLM row is also stale. It was measured under prompt **v3**, whose Gate 3 section told the
> model that "roughly one in five" reports escalate to a fatal or life-altering outcome. Our set
> runs at 55-59%, so the model was penalised for obeying an instruction - 82% of its misses were
> severity scored below 4 where humans scored 4 or above. Fixed on main; `prompt_version` is now
> **v4**. Re-run before quoting anything.
>
> The OSHA row (n=28, F1 0.133, recall 0.100) is too small to conclude from either way.
>
> Full diagnosis: [../docs/eval-diagnosis.md](../docs/eval-diagnosis.md).

# SIF Precursor Classifier Evaluation Summary

## Synthetic Reports (Fair Comparison, n=144)
- **Baseline Classifier**:
  - F1 Score: 0.970
  - PR-AUC: 0.963
  - Precision: 0.976
  - Recall: 0.965

- **LLM Classifier**:
  - F1 Score: 0.740
  - PR-AUC: 0.748
  - Precision: 0.826
  - Recall: 0.671

- **F1 Difference (LLM - Baseline)**: -0.230

---

## OSHA Real Reports (Generalization Check, LLM Only, n=28)
- **LLM Classifier**:
  - F1 Score: 0.133
  - PR-AUC: 0.341
  - Precision: 0.200
  - Recall: 0.100

---

## Severity Assessment Error Distribution (n=172)
- **Exact Match (0 level diff)**: 63 (36.6%)
- **Off by 1 Level**: 74 (43.0%)
- **Off by 2+ Levels**: 35 (20.3%)
- **Mean Severity Shift (LLM - Human Ground Truth)**: -0.297
