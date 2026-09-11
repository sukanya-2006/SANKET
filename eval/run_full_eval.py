# This script MUST NOT write eval/eval_summary.md.
#
# It scores the shipped backend/app/baseline_model.joblib, which train_baseline.py refits on
# every label, so the baseline F1 below is in-sample memorisation. eval_summary.md is the
# hand-curated honest summary: it carries the retraction of that exact number, the
# not-the-same-pool caveat and the "what must not be quoted" list. This file used to point
# SUMMARY_MD at it, so one run silently replaced all of that with the memorised figure. Output
# goes to run_full_eval_output_DO_NOT_QUOTE.md instead.

import os
import sys
import time
import pandas as pd
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from sklearn.metrics import f1_score, average_precision_score, precision_score, recall_score

# Ensure backend directory is in path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import cache, classifier_base, classifier_llm
from app.schemas import ClassificationResult

GOLD_PATH = ROOT / "data" / "gold_labels.csv"
SYNTHETIC_PATH = ROOT / "data" / "synthetic" / "synthetic_reports_for_labeling.csv"
SYNTHETIC_FULL_PATH = ROOT / "data" / "synthetic" / "synthetic_reports.csv"
OSHA_PATH = ROOT / "data" / "osha" / "osha_real_reports.csv"
OUTPUT_CSV = ROOT / "eval" / "llm_vs_baseline_results.csv"
SUMMARY_MD = ROOT / "eval" / "run_full_eval_output_DO_NOT_QUOTE.md"

def load_data():
    gold = pd.read_csv(GOLD_PATH)
    
    reports = []
    if SYNTHETIC_PATH.exists():
        syn = pd.read_csv(SYNTHETIC_PATH, encoding="utf-8-sig")
        syn["source"] = "synthetic"
        reports.append(syn[["report_id", "text", "source"]])
    elif SYNTHETIC_FULL_PATH.exists():
        syn = pd.read_csv(SYNTHETIC_FULL_PATH, encoding="utf-8-sig")
        syn["source"] = "synthetic"
        reports.append(syn[["report_id", "text", "source"]])

    if OSHA_PATH.exists():
        osha = pd.read_csv(OSHA_PATH, encoding="utf-8-sig")
        osha["source"] = "osha"
        text_col = "text" if "text" in osha.columns else "report_text"
        osha = osha.rename(columns={text_col: "text"})
        reports.append(osha[["report_id", "text", "source"]])

    all_reports = pd.concat(reports, ignore_index=True)
    all_reports["report_id"] = all_reports["report_id"].astype(str).str.strip()
    gold["report_id"] = gold["report_id"].astype(str).str.strip()

    merged = gold.merge(all_reports, on="report_id", how="inner")
    merged["actual_is_sif_precursor"] = merged["is_sif_precursor"].astype(str).str.strip().str.upper() == "TRUE"
    merged["actual_severity"] = merged["severity"].astype(int)
    
    return merged

def process_single_report(row):
    report_id = row.report_id
    text = row.text
    source = row.source
    actual_precursor = row.actual_is_sif_precursor
    actual_sev = row.actual_severity

    # Baseline prediction.
    #
    # WARNING - THIS IS NOT A FAIR BASELINE SCORE.
    # classifier_base loads backend/app/baseline_model.joblib, which train_baseline.py
    # deliberately retrains on EVERY label so the shipped fallback is as strong as possible.
    # Every report scored here was therefore in its training set, so the resulting F1 (0.970
    # when last run) is memorisation. eval/run_eval.py refits inside cross-validation folds
    # and gets 0.784 on the same data. Quote that one. See docs/eval-diagnosis.md.
    base_res = classifier_base.classify(text)
    base_pred = bool(base_res["is_sif_precursor"])

    # LLM prediction with cache
    hit = cache.get(text)
    if hit is not None:
        llm_res, _ = hit
        from_cache = True
    else:
        from_cache = False
        time.sleep(1.0)  # Inter-request delay to manage Groq TPM limit
        raw_dict = classifier_llm.classify(text)
        llm_res = ClassificationResult.model_validate(raw_dict)
        cache.put(text, llm_res, getattr(classifier_llm.classify, "version", "groq-llm"))

    llm_pred = bool(llm_res.is_sif_precursor)
    llm_sev = int(llm_res.severity)

    return {
        "report_id": report_id,
        "source": source,
        "actual_is_sif_precursor": actual_precursor,
        "baseline_predicted": base_pred,
        "llm_predicted": llm_pred,
        "actual_severity": actual_sev,
        "llm_severity": llm_sev,
        "from_cache": from_cache
    }

def run_evaluation():
    df = load_data()
    total_reports = len(df)
    print(f"Starting classification on {total_reports} reports from gold_labels.csv...\n")

    results_dict = {}
    completed_count = 0

    rows = list(df.itertuples())

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_row = {executor.submit(process_single_report, row): row for row in rows}
        for future in as_completed(future_to_row):
            res = future.result()
            results_dict[res["report_id"]] = res
            completed_count += 1
            if completed_count % 20 == 0 or completed_count == total_reports:
                print(f"Progress: {completed_count}/{total_reports} done")

    # Order by original dataframe order
    results = [results_dict[row.report_id] for row in rows]
    res_df = pd.DataFrame(results)
    
    # Save main comparison table
    save_cols = [
        "report_id", "source", "actual_is_sif_precursor",
        "baseline_predicted", "llm_predicted", "actual_severity", "llm_severity"
    ]
    os.makedirs(OUTPUT_CSV.parent, exist_ok=True)
    res_df[save_cols].to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved comparison table to {OUTPUT_CSV}")

    # --- METRICS CALCULATIONS ---
    # 4a. Synthetic Only
    syn_df = res_df[res_df["source"] == "synthetic"]
    syn_y_true = syn_df["actual_is_sif_precursor"].values
    syn_base_pred = syn_df["baseline_predicted"].values
    syn_llm_pred = syn_df["llm_predicted"].values

    syn_base_f1 = f1_score(syn_y_true, syn_base_pred, zero_division=0)
    syn_base_prauc = average_precision_score(syn_y_true, syn_base_pred)
    syn_base_prec = precision_score(syn_y_true, syn_base_pred, zero_division=0)
    syn_base_rec = recall_score(syn_y_true, syn_base_pred, zero_division=0)

    syn_llm_f1 = f1_score(syn_y_true, syn_llm_pred, zero_division=0)
    syn_llm_prauc = average_precision_score(syn_y_true, syn_llm_pred)
    syn_llm_prec = precision_score(syn_y_true, syn_llm_pred, zero_division=0)
    syn_llm_rec = recall_score(syn_y_true, syn_llm_pred, zero_division=0)

    # 4b. OSHA Only (LLM Only)
    osha_df = res_df[res_df["source"] == "osha"]
    osha_y_true = osha_df["actual_is_sif_precursor"].values
    osha_llm_pred = osha_df["llm_predicted"].values

    osha_llm_f1 = f1_score(osha_y_true, osha_llm_pred, zero_division=0)
    osha_llm_prauc = average_precision_score(osha_y_true, osha_llm_pred)
    osha_llm_prec = precision_score(osha_y_true, osha_llm_pred, zero_division=0)
    osha_llm_rec = recall_score(osha_y_true, osha_llm_pred, zero_division=0)

    # 5. Severity Matching Analysis (LLM vs Human across all reports)
    sev_diff = res_df["llm_severity"] - res_df["actual_severity"]
    abs_diff = np.abs(sev_diff)
    
    exact_matches = int(np.sum(abs_diff == 0))
    off_by_1 = int(np.sum(abs_diff == 1))
    off_by_2_plus = int(np.sum(abs_diff >= 2))
    total_sev = len(res_df)

    mean_sev_shift = float(np.mean(sev_diff))

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 60)
    print(f"\nSynthetic Reports (n={len(syn_df)}):")
    print(f"  Baseline  -> F1: {syn_base_f1:.3f} | PR-AUC: {syn_base_prauc:.3f} | Precision: {syn_base_prec:.3f} | Recall: {syn_base_rec:.3f}")
    print(f"  LLM       -> F1: {syn_llm_f1:.3f} | PR-AUC: {syn_llm_prauc:.3f} | Precision: {syn_llm_prec:.3f} | Recall: {syn_llm_rec:.3f}")
    print(f"  F1 Improvement (LLM vs Baseline): {syn_llm_f1 - syn_base_f1:+.3f}")

    print(f"\nOSHA Reports (Generalization Check, n={len(osha_df)}):")
    print(f"  LLM       -> F1: {osha_llm_f1:.3f} | PR-AUC: {osha_llm_prauc:.3f} | Precision: {osha_llm_prec:.3f} | Recall: {osha_llm_rec:.3f}")

    print(f"\nSeverity Analysis (LLM vs Human, n={total_sev}):")
    print(f"  Exact Match : {exact_matches:3d} / {total_sev} ({exact_matches/total_sev:.1%})")
    print(f"  Off by 1    : {off_by_1:3d} / {total_sev} ({off_by_1/total_sev:.1%})")
    print(f"  Off by 2+   : {off_by_2_plus:3d} / {total_sev} ({off_by_2_plus/total_sev:.1%})")
    print(f"  Mean Severity Shift (LLM - Human): {mean_sev_shift:+.3f}")

    # Write summary file
    summary_content = f"""# run_full_eval.py raw output - DO NOT QUOTE

> **The baseline numbers in this file are in-sample memorisation, not a result.**
> `train_baseline.py` refits the shipped model on every label, and this script scores that model
> on those same labels. Every report below was in its training set.
>
> **`eval/eval_summary.md` is the curated honest summary.** It carries the cross-validated
> baseline figure, the not-the-same-pool caveat and the retraction of the number below.
>
> This file is a run log. Never quote it, paste it into the deck, or cite it anywhere.

## Synthetic Reports (n={len(syn_df)})
- **Baseline Classifier** (in-sample, see banner - not a fair comparison):
  - F1 Score: {syn_base_f1:.3f}
  - PR-AUC: {syn_base_prauc:.3f}
  - Precision: {syn_base_prec:.3f}
  - Recall: {syn_base_rec:.3f}

- **LLM Classifier**:
  - F1 Score: {syn_llm_f1:.3f}
  - PR-AUC: {syn_llm_prauc:.3f}
  - Precision: {syn_llm_prec:.3f}
  - Recall: {syn_llm_rec:.3f}

- **F1 Difference (LLM - Baseline)**: {syn_llm_f1 - syn_base_f1:+.3f}

---

## OSHA Real Reports (Generalization Check, LLM Only, n={len(osha_df)})
- **LLM Classifier**:
  - F1 Score: {osha_llm_f1:.3f}
  - PR-AUC: {osha_llm_prauc:.3f}
  - Precision: {osha_llm_prec:.3f}
  - Recall: {osha_llm_rec:.3f}

---

## Severity Assessment Error Distribution (n={total_sev})
- **Exact Match (0 level diff)**: {exact_matches} ({exact_matches/total_sev:.1%})
- **Off by 1 Level**: {off_by_1} ({off_by_1/total_sev:.1%})
- **Off by 2+ Levels**: {off_by_2_plus} ({off_by_2_plus/total_sev:.1%})
- **Mean Severity Shift (LLM - Human Ground Truth)**: {mean_sev_shift:+.3f}
"""

    with open(SUMMARY_MD, "w", encoding="utf-8") as f:
        f.write(summary_content)

    print(f"\nWrote summary markdown to {SUMMARY_MD}")

if __name__ == "__main__":
    run_evaluation()
