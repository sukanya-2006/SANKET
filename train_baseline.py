"""
train_baseline.py

Trains the baseline classifier: TF-IDF -> Logistic Regression, predicting
is_sif_precursor (binary). This is the "fair fight" baseline the tech stack
doc calls for - simple, fast, and explainable via top-weighted words, no
SHAP needed.

RUN THIS ONCE gold_labels.csv EXISTS (i.e. after M1/M3 finish labeling).
Running it before that file exists will fail loudly and tell you why -
it will not silently train on fake data.

Usage:
    python train_baseline.py

Reads:  data/gold_labels.csv
        (expected columns: report_id, hazard_assessment, lsr_rule,
         control_status, severity, is_sif_precursor, notes, rubric_version)
        + the report text, joined in from the synthetic/OSHA files by report_id

Writes: backend/app/baseline_model.joblib   (the trained pipeline)
        backend/app/baseline_top_words.json (top positive/negative words,
                                              for the dashboard's
                                              explainability display)
"""

import json
import os
import sys

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

GOLD_LABELS_PATH = "data/gold_labels.csv"
SYNTHETIC_PATH = "data/synthetic/synthetic_reports_for_labeling.csv"
OSHA_PATH = "data/osha/osha_real_reports.csv"

MODEL_OUTPUT_PATH = "backend/app/baseline_model.joblib"
TOP_WORDS_OUTPUT_PATH = "backend/app/baseline_top_words.json"

TOP_N_WORDS = 15


def load_and_join_data() -> pd.DataFrame:
    if not os.path.exists(GOLD_LABELS_PATH):
        sys.exit(
            f"\n[!] {GOLD_LABELS_PATH} does not exist yet.\n"
            "    This script trains on human-labeled ground truth - it cannot run\n"
            "    until M1/M3 finish labeling the 180 reports and their labels are\n"
            "    merged into data/gold_labels.csv (report_id, hazard_assessment,\n"
            "    lsr_rule, control_status, severity, is_sif_precursor, notes,\n"
            "    rubric_version, annotator).\n"
        )

    labels = pd.read_csv(GOLD_LABELS_PATH)

    reports = []
    if os.path.exists(SYNTHETIC_PATH):
        syn = pd.read_csv(SYNTHETIC_PATH, encoding="utf-8-sig")
        reports.append(syn[["report_id", "text"]])
    if os.path.exists(OSHA_PATH):
        osha = pd.read_csv(OSHA_PATH, encoding="utf-8-sig")
        reports.append(osha[["report_id", "text"]])

    if not reports:
        sys.exit(f"[!] Neither {SYNTHETIC_PATH} nor {OSHA_PATH} were found.")

    all_reports = pd.concat(reports, ignore_index=True)

    merged = labels.merge(all_reports, on="report_id", how="inner")

    if len(merged) < len(labels):
        missing = len(labels) - len(merged)
        print(f"[!] Warning: {missing} labeled report_id(s) had no matching report "
              f"text and were dropped. Check report_id alignment.")

    if merged.empty:
        sys.exit(
            "[!] No rows matched between gold_labels.csv and the report text files. "
            "Check that report_id values line up across both files."
        )

    return merged


def main():
    df = load_and_join_data()
    print(f"Loaded {len(df)} labeled reports.")

    positive_rate = df["is_sif_precursor"].mean()
    print(f"Positive class rate: {positive_rate:.1%} "
          f"(expect roughly 20-25% per the labeling design)")

    X = df["text"]
    y = df["is_sif_precursor"].astype(bool)

    # Stratified split so the small positive class is represented in both sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=2000,
            ngram_range=(1, 2),
            stop_words="english",
            min_df=2,
        )),
        ("clf", LogisticRegression(
            class_weight="balanced",  # positives are ~20-25% of the data
            max_iter=1000,
            random_state=42,
        )),
    ])

    pipeline.fit(X_train, y_train)

    # Report F1 and PR-AUC - never accuracy, per the tech stack doc's own
    # warning: at ~22% positives, "always say no" scores ~78% accuracy.
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    f1 = f1_score(y_test, y_pred)
    pr_auc = average_precision_score(y_test, y_proba)

    print(f"\nHeld-out test set ({len(X_test)} reports):")
    print(f"  F1:      {f1:.3f}")
    print(f"  PR-AUC:  {pr_auc:.3f}")

    # Retrain on the FULL dataset for the model that actually ships - the
    # train/test split above was only to get an honest accuracy estimate.
    pipeline.fit(X, y)

    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
    joblib.dump(pipeline, MODEL_OUTPUT_PATH)
    print(f"\nSaved trained pipeline to {MODEL_OUTPUT_PATH}")

    # Explainability: top-weighted words, both directions. This is what
    # classifier_base.py's flagged_phrases draws from at inference time.
    vectorizer = pipeline.named_steps["tfidf"]
    clf = pipeline.named_steps["clf"]
    feature_names = vectorizer.get_feature_names_out()
    coefficients = clf.coef_[0]

    ranked = sorted(zip(feature_names, coefficients), key=lambda x: x[1])
    top_negative = [{"word": w, "weight": round(float(c), 4)} for w, c in ranked[:TOP_N_WORDS]]
    top_positive = [{"word": w, "weight": round(float(c), 4)} for w, c in ranked[-TOP_N_WORDS:]][::-1]

    with open(TOP_WORDS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"top_positive": top_positive, "top_negative": top_negative}, f, indent=2)
    print(f"Saved top-weighted words to {TOP_WORDS_OUTPUT_PATH}")

    print("\nTop words pushing TOWARD 'SIF precursor':")
    for item in top_positive[:8]:
        print(f"  {item['word']:25s} {item['weight']:+.3f}")


if __name__ == "__main__":
    main()