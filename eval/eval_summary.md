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
