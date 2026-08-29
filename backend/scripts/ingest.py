"""Load reports and gold labels into Supabase.

    python scripts/ingest.py --reports  ../data/reports_metadata.csv
    python scripts/ingest.py --labels   ../data/gold_labels.csv
    python scripts/ingest.py --classify            # run every report through the classifier
    python scripts/ingest.py --apply-schema        # create tables + the latest_predictions view

MEMBER 3 produces the two CSVs. Column names must match NAMES.md exactly — the loader refuses a
file with unexpected or missing columns rather than silently importing nulls, because a report
missing `site` is invisible to the dashboard and that is the most likely silent failure in the
whole project.

Expected columns
----------------
reports_metadata.csv : report_id, report_text, source, site, activity, shift, report_date,
                       is_contractor
                       (site/activity/shift may be blank for source='osha' only)

gold_labels.csv      : report_id, annotator, hazard_assessment, lsr_rule, control_status,
                       severity, is_sif_precursor, notes, gate_split, rubric_version, is_tiebreak
                       (control_status blank unless hazard_assessment='yes')
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import classifier, db  # noqa: E402
from app.schemas import ControlStatus, HazardAssessment, LSRRule  # noqa: E402

REPORT_COLUMNS = {
    "report_id", "report_text", "source", "site", "activity", "shift",
    "report_date", "is_contractor",
}
LABEL_COLUMNS = {
    "report_id", "annotator", "hazard_assessment", "lsr_rule", "control_status",
    "severity", "is_sif_precursor", "notes", "gate_split", "rubric_version", "is_tiebreak",
}

INSERT_REPORT = """
INSERT INTO reports (report_id, report_text, source, site, activity, shift, report_date, is_contractor)
VALUES (%(report_id)s, %(report_text)s, %(source)s, %(site)s, %(activity)s, %(shift)s,
        %(report_date)s, %(is_contractor)s)
ON CONFLICT (report_id) DO UPDATE SET
    report_text = EXCLUDED.report_text, site = EXCLUDED.site, activity = EXCLUDED.activity,
    shift = EXCLUDED.shift, report_date = EXCLUDED.report_date,
    is_contractor = EXCLUDED.is_contractor
"""

INSERT_LABEL = """
INSERT INTO gold_labels (report_id, annotator, hazard_assessment, lsr_rule, control_status,
                         severity, is_sif_precursor, notes, gate_split, rubric_version, is_tiebreak)
VALUES (%(report_id)s, %(annotator)s, %(hazard_assessment)s, %(lsr_rule)s, %(control_status)s,
        %(severity)s, %(is_sif_precursor)s, %(notes)s, %(gate_split)s, %(rubric_version)s,
        %(is_tiebreak)s)
ON CONFLICT (report_id, annotator) DO UPDATE SET
    hazard_assessment = EXCLUDED.hazard_assessment, lsr_rule = EXCLUDED.lsr_rule,
    control_status = EXCLUDED.control_status, severity = EXCLUDED.severity,
    is_sif_precursor = EXCLUDED.is_sif_precursor, notes = EXCLUDED.notes,
    gate_split = EXCLUDED.gate_split, rubric_version = EXCLUDED.rubric_version
"""


def _blank_to_none(value: str | None) -> str | None:
    return value.strip() or None if value else None


def _bool(value: str | None) -> bool | None:
    if value is None or not value.strip():
        return None
    return value.strip().lower() in {"1", "true", "yes", "y", "t"}


def _check_columns(path: Path, header: set[str], expected: set[str]) -> None:
    missing, unexpected = expected - header, header - expected
    if missing or unexpected:
        raise SystemExit(
            f"{path.name}: column mismatch against NAMES.md\n"
            f"  missing:    {sorted(missing) or 'none'}\n"
            f"  unexpected: {sorted(unexpected) or 'none'}\n"
            "Fix the CSV rather than this script — the names are locked."
        )


def load_reports(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        _check_columns(path, set(reader.fieldnames or []), REPORT_COLUMNS)
        rows = []
        for line, raw in enumerate(reader, start=2):
            row = {k: _blank_to_none(v) for k, v in raw.items()}
            row["is_contractor"] = _bool(raw.get("is_contractor"))

            if row["source"] not in {"synthetic", "osha"}:
                raise SystemExit(f"{path.name}:{line}: source must be synthetic or osha")
            # The schema enforces this too; failing here gives a line number.
            if row["source"] == "synthetic" and not all(
                (row["site"], row["activity"], row["shift"])
            ):
                raise SystemExit(
                    f"{path.name}:{line}: synthetic reports need site, activity and shift — "
                    "without them the report is invisible to the dashboard"
                )
            rows.append(row)

    db.executemany(INSERT_REPORT, rows)
    return len(rows)


def load_labels(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        _check_columns(path, set(reader.fieldnames or []), LABEL_COLUMNS)
        rows = []
        for line, raw in enumerate(reader, start=2):
            row = {k: _blank_to_none(v) for k, v in raw.items()}
            row["is_sif_precursor"] = _bool(raw.get("is_sif_precursor"))
            row["is_tiebreak"] = _bool(raw.get("is_tiebreak")) or False
            row["severity"] = int(row["severity"]) if row["severity"] else None
            row["gate_split"] = int(row["gate_split"]) if row["gate_split"] else None

            try:
                HazardAssessment(row["hazard_assessment"])
                LSRRule(row["lsr_rule"])
                if row["control_status"]:
                    ControlStatus(row["control_status"])
            except ValueError as exc:
                raise SystemExit(f"{path.name}:{line}: {exc}") from None

            if row["severity"] is None or not 1 <= row["severity"] <= 5:
                raise SystemExit(f"{path.name}:{line}: severity must be 1-5")
            rows.append(row)

    db.executemany(INSERT_LABEL, rows)
    return len(rows)


def classify_all() -> int:
    """Run every stored report through the classifier and append the predictions."""
    reports = db.query("SELECT report_id, report_text FROM reports ORDER BY report_id")
    for i, row in enumerate(reports, start=1):
        outcome = classifier.classify(row["report_text"])
        db.insert_prediction(
            row["report_id"], outcome.result, outcome.model_version, outcome.is_fallback
        )
        if i % 25 == 0:
            print(f"  classified {i}/{len(reports)}")
    return len(reports)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-schema", action="store_true", help="create tables and the view")
    parser.add_argument("--reports", type=Path, help="reports_metadata.csv")
    parser.add_argument("--labels", type=Path, help="gold_labels.csv")
    parser.add_argument("--classify", action="store_true", help="classify every stored report")
    args = parser.parse_args()

    if not db.is_live():
        raise SystemExit(
            "No database configured. Set SUPABASE_DB_URL in backend/.env and install psycopg:\n"
            "  pip install 'psycopg[binary]'"
        )

    if args.apply_schema:
        db.apply_schema()
        print("schema applied")
    if args.reports:
        print(f"loaded {load_reports(args.reports)} reports")
    if args.labels:
        print(f"loaded {load_labels(args.labels)} gold labels")
    if args.classify:
        print(f"classified {classify_all()} reports")

    if not any((args.apply_schema, args.reports, args.labels, args.classify)):
        parser.print_help()


if __name__ == "__main__":
    main()
