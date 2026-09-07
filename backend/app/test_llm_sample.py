import sys
sys.path.insert(0, ".")
import pandas as pd
from classifier_llm import classify

labels = pd.read_csv("../data/gold_labels.csv")

synthetic = pd.read_csv("../data/synthetic/synthetic_reports.csv")
osha = pd.read_csv("../data/osha/osha_real_reports.csv")
reports = pd.concat([synthetic, osha], ignore_index=True)

print("Label columns:", labels.columns.tolist())
print("Report columns:", reports.columns.tolist())

df = labels.merge(reports, on="report_id", how="inner")
print(f"\nMerged {len(df)} reports with text.\n")

text_col = "text" if "text" in df.columns else "report_text"

samples = df[df["is_sif_precursor"] == True].head(1)
samples = pd.concat([samples, df[df["is_sif_precursor"] == False].head(1)])
samples = pd.concat([samples, df[df["severity"] == 3].head(1)])

for _, row in samples.iterrows():
    print("=" * 60)
    print(f"Report ID: {row['report_id']}")
    print(f"Text: {row[text_col][:200]}...")
    print(f"\nACTUAL LABEL -> precursor: {row['is_sif_precursor']}, severity: {row['severity']}, control: {row['control_status']}")

    result = classify(row[text_col])
    print(f"\nMODEL SAID   -> precursor: {result['is_sif_precursor']}, severity: {result['severity']}, control: {result['control_status']}")
    print(f"Model reasoning: {result['reasoning']}")
    print()