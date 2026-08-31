"""
create_labeling_template.py

Generates a personal labeling worksheet for one annotator. Pre-fills every
report's id, source, and text (so you can read and judge in one file,
without needing two windows open) and leaves the judgment columns empty
for you to fill in.

Usage:
    python create_labeling_template.py --annotator sukanya

Reads:  data/synthetic/synthetic_reports_for_labeling.csv  (150 reports)
        data/osha/osha_real_reports.csv                     (30 reports)

Writes: data/gold_labels_<annotator>.csv

Fill in these columns for every row, using rubric v2.1's three gates:
    hazard_assessment   -> yes / no / insufficient_information
    lsr_rule            -> energy_isolation / hot_work / confined_space /
                            line_of_fire / work_at_height / lifting /
                            driving / permit_to_work / none
    control_status      -> absent / failed / present / unclear  (leave
                            blank if hazard_assessment isn't "yes")
    severity            -> 1-5
    is_sif_precursor    -> TRUE / FALSE (per rubric section 6's table -
                            never set this by feel)
    notes               -> mandatory for insufficient_information, unclear,
                            or any call you found hard. One line.

Do NOT touch report_id, source, or text - those are reference columns only,
carried through so the merge script can match your labels back to the
right report.
"""

import argparse
import os
import pandas as pd

SYNTHETIC_PATH = "data/synthetic/synthetic_reports_for_labeling.csv"
OSHA_PATH = "data/osha/osha_real_reports.csv"

JUDGMENT_COLUMNS = [
    "hazard_assessment",
    "lsr_rule",
    "control_status",
    "severity",
    "is_sif_precursor",
    "notes",
]

RUBRIC_VERSION = "2.1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--annotator", required=True,
        help="Your name/id, used in the output filename, e.g. --annotator sukanya"
    )
    args = parser.parse_args()

    frames = []

    if os.path.exists(SYNTHETIC_PATH):
        syn = pd.read_csv(SYNTHETIC_PATH, encoding="utf-8-sig")
        syn = syn[["report_id", "source", "text"]].copy()
        frames.append(syn)
    else:
        print(f"[!] Warning: {SYNTHETIC_PATH} not found, skipping.")

    if os.path.exists(OSHA_PATH):
        osha = pd.read_csv(OSHA_PATH, encoding="utf-8-sig")

        # osha_real_reports.csv currently has only a single "report_text"
        # column - no report_id, no source. Generate both here so this
        # file lines up with the synthetic file's shape.
        osha = osha.rename(columns={"report_text": "text"})
        if "report_id" not in osha.columns:
            # Continue numbering after the synthetic reports (1-150) so
            # every report_id across both files is unique.
            osha["report_id"] = range(151, 151 + len(osha))
        if "source" not in osha.columns:
            osha["source"] = "osha"

        osha = osha[["report_id", "source", "text"]].copy()
        frames.append(osha)
    else:
        print(f"[!] Warning: {OSHA_PATH} not found, skipping.")

    if not frames:
        raise SystemExit("No report files found - nothing to label.")

    combined = pd.concat(frames, ignore_index=True)

    # Shuffle so synthetic and OSHA reports are interleaved, not labeled
    # in two obvious back-to-back blocks - reduces the chance of settling
    # into a rhythm that treats one source differently from the other.
    combined = combined.sample(frac=1, random_state=hash(args.annotator) % (2**32)).reset_index(drop=True)

    for col in JUDGMENT_COLUMNS:
        combined[col] = ""

    combined["rubric_version"] = RUBRIC_VERSION
    combined["annotator"] = args.annotator

    output_path = f"data/gold_labels_{args.annotator}.csv"
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Created {output_path} with {len(combined)} reports to label.")
    print(f"({len(combined[combined['source'] == 'synthetic'])} synthetic, "
          f"{len(combined[combined['source'] == 'osha'])} OSHA)")
    print("\nOpen it in Excel or Google Sheets and fill in the 6 judgment "
          "columns for every row, using rubric v2.1.")


if __name__ == "__main__":
    main()