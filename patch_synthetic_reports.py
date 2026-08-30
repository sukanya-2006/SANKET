"""
patch_synthetic_reports.py

One-time patch for an already-generated synthetic_reports.csv that is
missing required metadata columns. Does NOT call Groq again - the
existing report text is kept exactly as-is. This only adds columns.

Run this ONCE from the project root:
    python patch_synthetic_reports.py

Reads:  data/synthetic/synthetic_reports.csv   (original, 6 columns)
Writes: data/synthetic/synthetic_reports.csv                 (overwritten, 9 columns)
        data/synthetic/synthetic_reports_for_labeling.csv    (8 columns, no hint)
"""

import csv
import random
import datetime
import os

INPUT_FILE = "data/synthetic/synthetic_reports.csv"
LABELING_FILE = "data/synthetic/synthetic_reports_for_labeling.csv"

ACTIVITIES = [
    "Maintenance",
    "Hot Work",
    "Lifting",
    "Confined Space Entry",
    "Logistics",
    "Drilling Operations",
    "Housekeeping",
    "Vehicle Operations",
]

# A rough mapping so the assigned activity at least loosely matches the
# hazard hint already present in the row - keeps the metadata plausible
# rather than pure random noise.
HAZARD_TO_LIKELY_ACTIVITIES = {
    "fall_from_height": ["Maintenance", "Housekeeping"],
    "energy_isolation_failure": ["Maintenance", "Hot Work"],
    "vehicle_pedestrian_interaction": ["Logistics", "Vehicle Operations"],
    "confined_space_entry": ["Confined Space Entry", "Maintenance"],
    "ppe_noncompliance": ACTIVITIES,  # can happen doing anything
    "equipment_machinery_hazard": ["Lifting", "Drilling Operations", "Maintenance"],
    "fire_or_gas_leak_near_miss": ["Hot Work", "Maintenance"],
    "slip_trip_hazard": ["Housekeeping", "Logistics"],
}

REPORT_DATE_WINDOW_DAYS = 180

FULL_HEADER = [
    "report_id", "text", "site", "activity", "shift",
    "report_date", "is_contractor", "source", "hazard_type_hint",
]
LABELING_HEADER = FULL_HEADER[:-1]


def pick_activity(hazard_hint):
    choices = HAZARD_TO_LIKELY_ACTIVITIES.get(hazard_hint, ACTIVITIES)
    return random.choice(choices)


def random_report_date(today):
    offset = random.randint(0, REPORT_DATE_WINDOW_DAYS)
    return (today - datetime.timedelta(days=offset)).isoformat()


def main():
    today = datetime.date.today()

    with open(INPUT_FILE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Read {len(rows)} existing reports from {INPUT_FILE}")

    full_rows = []
    for row in rows:
        hazard_hint = row["hazard_type_hint"]
        activity = pick_activity(hazard_hint)
        report_date = random_report_date(today)

        # contractor_flag was stored as the string "True"/"False" - normalize it
        is_contractor = row["contractor_flag"].strip().lower() == "true"

        full_rows.append([
            row["report_id"],
            row["text"],
            row["site"],
            activity,
            row["shift"],
            report_date,
            is_contractor,
            "synthetic",
            hazard_hint,
        ])

    # Overwrite the full file with the new columns added
    with open(INPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(FULL_HEADER)
        writer.writerows(full_rows)

    print(f"Patched {INPUT_FILE} - now has columns: {', '.join(FULL_HEADER)}")

    # Write the labeling-safe copy - same data, hint column dropped
    with open(LABELING_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(LABELING_HEADER)
        for row in full_rows:
            writer.writerow(row[:-1])

    print(f"Wrote labeling-safe copy to {LABELING_FILE}")
    print("\nAnnotators (M1 / M3): label from synthetic_reports_for_labeling.csv only.")


if __name__ == "__main__":
    main()