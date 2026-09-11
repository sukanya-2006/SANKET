"""
merge_labels.py

Run this once BOTH annotators have finished their independent labeling
files. Compares them, computes raw agreement and Cohen's kappa (the
"human ceiling" number your pitch depends on), and produces the final
data/gold_labels.csv.

is_sif_precursor is RE-DERIVED from the three gates before anything is
compared, per rubric sections 2 and 6 - the CSVs carry it as a typed column and
a typo there must not be able to decide whether two people agreed. Rows where
both annotators agree on the derived label use it directly. Rows where they disagree are NOT silently resolved here -
they're written to data/labeling_disagreements.csv for the tiebreaker
(M6) to review and adjudicate by hand, per rubric v2.2 section 10's
protocol. gold_labels.csv will have blank judgment fields for those rows
until the tiebreak happens - this is intentional, not a bug in the script.

Usage:
    python merge_labels.py --a data/gold_labels_sukanya.csv --b data/gold_labels_<other>.csv

Writes:
    data/gold_labels.csv                 (agreed rows, ready for training)
    data/labeling_disagreements.csv      (disagreements, needs tiebreak)
    Prints raw agreement % and Cohen's kappa to the terminal.
"""

import argparse
import pandas as pd
from sklearn.metrics import cohen_kappa_score

JUDGMENT_COLUMNS = ["hazard_assessment", "lsr_rule", "control_status", "severity", "is_sif_precursor"]


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Clean up spelling, then RE-DERIVE is_sif_precursor from the three gates.

    The rubric (sections 2 and 6) says the label is computed, never typed. This script used to
    compare the typed column straight from the CSV, and that produced two opposite errors on
    the real files:

      report 56  both annotators recorded identical gates - yes / failed / 4 - but one typed
                 the boolean as False. Compared on the typed column they "disagreed", so a
                 report they fully agreed on was held out of the gold set awaiting a tiebreak
                 that was never needed.

      reports    one annotator typed True against her own gates (severity 3, and an 'unclear'
      51 and 96  control). The other typed True from gates that genuinely gave True. Compared
                 on the typed column they "agreed", so the merge took annotator A's row as
                 gold without anyone adjudicating - on two reports where the annotators
                 actually differ, on severity and on control_status respectively.

    A typo in a derived field cannot be allowed to decide either whether two people agree or
    what the gold answer is. Deriving here makes both impossible.
    """
    df = df.copy()
    for col in ["hazard_assessment", "lsr_rule", "control_status"]:
        df[col] = df[col].astype(str).str.strip().str.lower().replace({"nan": ""})

    # lsr_rule vocabulary is underscored (NAMES.md). A space splits one rule into two buckets
    # in every GROUP BY downstream, so normalise it before anything compares on it.
    df["lsr_rule"] = df["lsr_rule"].str.replace(" ", "_", regex=False)

    # There is no control to assess for a hazard we could not name (rubric section 2).
    df.loc[df["hazard_assessment"] != "yes", "control_status"] = ""

    df["severity"] = pd.to_numeric(df["severity"], errors="coerce")

    typed = df["is_sif_precursor"].astype(str).str.strip().str.upper().map(
        {"TRUE": True, "FALSE": False}
    )
    df["is_sif_precursor"] = (
        (df["hazard_assessment"] == "yes")
        & (df["control_status"].isin(["absent", "failed"]))
        & (df["severity"] >= 4)
    )

    contradicted = (typed.notna()) & (typed != df["is_sif_precursor"])
    if contradicted.any():
        ids = df.loc[contradicted, "report_id"].tolist()
        print(f"  [i] Re-derived is_sif_precursor on {contradicted.sum()} row(s) whose typed "
              f"value contradicted their own gates: {ids}")

    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", required=True, help="First annotator's completed CSV")
    parser.add_argument("--b", required=True, help="Second annotator's completed CSV")
    args = parser.parse_args()

    df_a = normalize(pd.read_csv(args.a, encoding="utf-8-sig"))
    df_b = normalize(pd.read_csv(args.b, encoding="utf-8-sig"))

    if len(df_a) != len(df_b):
        print(f"[!] Warning: annotator A has {len(df_a)} rows, annotator B has "
              f"{len(df_b)} rows - they should both cover all 180 reports.")

    merged = df_a.merge(
        df_b, on="report_id", suffixes=("_a", "_b"), how="inner"
    )

    if merged.empty:
        raise SystemExit("No matching report_id values between the two files - check both files.")

    print(f"Comparing {len(merged)} reports labeled by both annotators.\n")

    # --- Agreement on the field that matters most for the pitch ---
    is_precursor_a = merged["is_sif_precursor_a"]
    is_precursor_b = merged["is_sif_precursor_b"]

    raw_agreement = (is_precursor_a == is_precursor_b).mean()
    kappa = cohen_kappa_score(is_precursor_a, is_precursor_b)

    print("=" * 60)
    print("HUMAN AGREEMENT — is_sif_precursor")
    print("=" * 60)
    print(f"  Raw agreement:  {raw_agreement:.1%}")
    print(f"  Cohen's kappa:  {kappa:.3f}")
    print("  (This is the ceiling your classifier gets measured against.)")

    if raw_agreement < 0.70:
        print("\n  [!] Below 70% agreement. Per rubric v2.2 section 10: revise the "
              "rubric on whichever gate is splitting, then re-label ONLY the "
              "reports that turned on that gate - not all 180 again.")

    # --- Per-gate agreement, to see which gate is actually splitting ---
    print("\nPer-field raw agreement (diagnostic - which gate disagrees most):")
    for col in ["hazard_assessment", "lsr_rule", "control_status", "severity"]:
        col_agreement = (merged[f"{col}_a"] == merged[f"{col}_b"]).mean()
        print(f"  {col:20s} {col_agreement:.1%}")

    # --- Split into agreed vs disagreed rows ---
    agree_mask = is_precursor_a == is_precursor_b
    agreed = merged[agree_mask].copy()
    disagreed = merged[~agree_mask].copy()

    # For agreed rows, take annotator A's values as gold.
    #
    # "Agreed" here means agreed on the DERIVED label, which is the thing being predicted.
    # Two annotators can land on the same label from severity 4 and severity 5; A's row is
    # taken in that case, and that is a documented tie-break, not a claim they were identical.
    # What must never happen is this branch running because a typed boolean matched while the
    # gates did not - see normalize().
    gold_rows = []
    for _, row in agreed.iterrows():
        gold_rows.append({
            "report_id": row["report_id"],
            "hazard_assessment": row["hazard_assessment_a"],
            "lsr_rule": row["lsr_rule_a"],
            "control_status": row["control_status_a"],
            "severity": row["severity_a"],
            "is_sif_precursor": row["is_sif_precursor_a"],
            "rubric_version": row.get("rubric_version_a", "2.1"),
            "annotator": "agreed",
        })

    gold_df = pd.DataFrame(gold_rows)
    gold_df.to_csv("data/gold_labels.csv", index=False, encoding="utf-8-sig")
    print(f"\nWrote {len(gold_df)} agreed labels to data/gold_labels.csv")

    if not disagreed.empty:
        disagree_cols = ["report_id", "text_a"] + [
            f"{c}_{s}" for c in JUDGMENT_COLUMNS for s in ("a", "b")
        ]
        disagree_cols = [c for c in disagree_cols if c in disagreed.columns]
        disagreed[disagree_cols].to_csv(
            "data/labeling_disagreements.csv", index=False, encoding="utf-8-sig"
        )
        print(f"Wrote {len(disagreed)} disagreements to "
              f"data/labeling_disagreements.csv for M6 to tiebreak.")
        print("Once tiebroken, append those resolved rows to data/gold_labels.csv "
              "by hand before running train_baseline.py.")
    else:
        print("No disagreements - every report matched. gold_labels.csv is complete.")


if __name__ == "__main__":
    main()