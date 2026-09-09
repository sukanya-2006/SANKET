"""
load_gold_labels.py

Loads the human labels into the live Supabase `gold_labels` table.

    python load_gold_labels.py --dry-run    # audit only, writes nothing
    python load_gold_labels.py              # audit, then write

WHAT IT LOADS

  data/global_labels_akanksha2M6.csv   annotator 'akanksha'   independent
  data/global_labels_sukanya2M6.csv    annotator 'sukanya'    independent
  data/gold_labels.csv                 annotator 'agreed'     adjudicated

Both independent files are loaded, not just the adjudicated set. Cohen's kappa
is only meaningful if the two annotators' raw judgements survive somewhere, and
"two of us labelled independently and agreed X% of the time" is the answer to
"you wrote the reports and graded yourself". Keeping only the merged row throws
that away.

WHAT IT CORRECTS, AND WHY THAT IS NOT RELABELLING

Three corrections are applied. None of them is a judgement about a report -
each is a mechanical application of a rule the rubric already states, and every
one is printed with its report_id so a human can audit it.

  1. lsr_rule spelling.  'energy isolation' -> 'energy_isolation'. NAMES.md
     fixes the vocabulary; a space instead of an underscore silently splits one
     rule into two buckets in every GROUP BY, under-counting it on the
     dashboard and in eval. The annotator meant the same rule.

  2. control_status where hazard_assessment is not 'yes' becomes NULL. Rubric
     section 2: there is no control to assess for a hazard we could not name.
     The schema enforces the same thing with a CHECK constraint, so these rows
     would be rejected outright.

  3. is_sif_precursor is DERIVED, always, from the three gates:
         hazard == 'yes' AND control in ('absent','failed') AND severity >= 4
     Rubric sections 2 and 6: the field is computed, never typed. The CSVs carry
     it as a typed column, and in a handful of rows the typed value contradicts
     the gates the same annotator recorded. The gates are the judgement; the
     flag is arithmetic. So the gates win and the flag is recomputed.

     This matters beyond tidiness. The `predictions` table carries a CHECK
     constraint asserting exactly this identity, so the model structurally
     cannot emit a row where the flag and the gates disagree. A gold row that
     disagreed would be a target the model can never hit - counted as a miss no
     matter what it answered.

Re-running is safe: one row per (report_id, annotator), updated in place.
"""

import argparse
import csv
import io
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(dotenv_path=Path(__file__).resolve().parent / "backend" / ".env")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import db  # noqa: E402

SOURCES = [
    ("data/global_labels_akanksha2M6.csv", "akanksha"),
    ("data/global_labels_sukanya2M6.csv", "sukanya"),
    ("data/gold_labels.csv", "agreed"),
]

VALID_RULES = {"energy_isolation", "hot_work", "confined_space", "line_of_fire",
               "work_at_height", "lifting", "driving", "permit_to_work", "none"}
VALID_HAZARD = {"yes", "no", "insufficient_information"}
VALID_CONTROL = {"absent", "failed", "present", "unclear"}

UPSERT = """
INSERT INTO gold_labels (
    report_id, annotator, is_tiebreak, hazard_assessment, lsr_rule,
    control_status, severity, is_sif_precursor, notes, rubric_version
) VALUES (
    %(report_id)s, %(annotator)s, %(is_tiebreak)s, %(hazard_assessment)s, %(lsr_rule)s,
    %(control_status)s, %(severity)s, %(is_sif_precursor)s, %(notes)s, %(rubric_version)s
)
ON CONFLICT (report_id, annotator) DO UPDATE SET
    hazard_assessment = EXCLUDED.hazard_assessment,
    lsr_rule          = EXCLUDED.lsr_rule,
    control_status    = EXCLUDED.control_status,
    severity          = EXCLUDED.severity,
    is_sif_precursor  = EXCLUDED.is_sif_precursor,
    notes             = EXCLUDED.notes,
    rubric_version    = EXCLUDED.rubric_version
"""


def derive_precursor(hazard, control, severity):
    """The one definition of the label, in one place. Rubric section 6."""
    return hazard == "yes" and control in ("absent", "failed") and severity >= 4


def normalise(row, annotator, corrections, rejects):
    rid = str(row["report_id"]).strip()

    hazard = (row.get("hazard_assessment") or "").strip().lower()
    rule_raw = (row.get("lsr_rule") or "").strip().lower()
    control = (row.get("control_status") or "").strip().lower() or None
    sev_raw = (row.get("severity") or "").strip()

    # 1. lsr_rule spelling
    rule = rule_raw.replace(" ", "_").replace("-", "_")
    if rule != rule_raw:
        corrections.append((annotator, rid, "lsr_rule", repr(rule_raw) + " -> " + repr(rule)))

    try:
        severity = int(float(sev_raw))
    except (TypeError, ValueError):
        rejects.append((annotator, rid, "severity " + repr(sev_raw) + " is not a number"))
        return None

    if hazard not in VALID_HAZARD:
        rejects.append((annotator, rid, "hazard_assessment " + repr(hazard) + " not in vocabulary"))
        return None
    if rule not in VALID_RULES:
        rejects.append((annotator, rid, "lsr_rule " + repr(rule) + " not in vocabulary"))
        return None
    if control and control not in VALID_CONTROL:
        rejects.append((annotator, rid, "control_status " + repr(control) + " not in vocabulary"))
        return None
    if not 1 <= severity <= 5:
        rejects.append((annotator, rid, "severity " + str(severity) + " outside 1-5"))
        return None

    # 2. control_status only means something when a hazard was named
    if hazard != "yes" and control is not None:
        corrections.append((annotator, rid, "control_status",
                            repr(control) + " -> NULL (hazard_assessment is " + repr(hazard) + ")"))
        control = None

    # 3. is_sif_precursor is derived, never typed
    derived = derive_precursor(hazard, control, severity)
    typed_raw = (row.get("is_sif_precursor") or "").strip().lower()
    typed = typed_raw in ("true", "1", "yes", "t")
    if typed_raw and typed != derived:
        corrections.append((annotator, rid, "is_sif_precursor",
                            "typed " + str(typed) + " -> derived " + str(derived) +
                            "  (hazard=" + hazard + ", control=" + str(control) +
                            ", severity=" + str(severity) + ")"))

    return {
        "report_id": rid,
        "annotator": annotator,
        "is_tiebreak": False,
        "hazard_assessment": hazard,
        "lsr_rule": rule,
        "control_status": control,
        "severity": severity,
        "is_sif_precursor": derived,
        "notes": (row.get("notes") or "").strip() or None,
        "rubric_version": (row.get("rubric_version") or "").strip() or "2.1",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="audit and print corrections, write nothing")
    args = ap.parse_args()

    if not db.is_live():
        sys.exit("[!] Database not connected. Check backend/.env and /health first.")

    known = {r["report_id"] for r in db.query("SELECT report_id FROM reports")}
    print(str(len(known)) + " reports in the database.\n")

    corrections, rejects, all_rows = [], [], []

    for path, annotator in SOURCES:
        if not os.path.exists(path):
            print("[!] " + path + " not found, skipping.")
            continue
        with open(path, encoding="utf-8-sig", newline="") as fh:
            raw = list(csv.DictReader(fh))

        rows, missing = [], []
        for r in raw:
            norm = normalise(r, annotator, corrections, rejects)
            if norm is None:
                continue
            # gold_labels has a foreign key to reports. A label for a report we
            # never loaded is not worth stopping for, but it has to be counted
            # out loud rather than dropped quietly.
            if norm["report_id"] not in known:
                missing.append(norm["report_id"])
                continue
            rows.append(norm)

        all_rows.extend(rows)
        note = ", " + str(len(missing)) + " for unknown report_ids" if missing else ""
        print("  " + path.ljust(42) + str(len(raw)).rjust(5) + " read -> " +
              str(len(rows)).rjust(4) + " loadable (annotator " + repr(annotator) + note + ")")
        if missing:
            print("      unknown report_ids: " + str(sorted(missing)[:10]))

    print("\n" + "=" * 76)
    print("CORRECTIONS APPLIED  (" + str(len(corrections)) + ")")
    print("=" * 76)
    if not corrections:
        print("  none - every row already matched the rubric")
    else:
        print("  Each is a rubric rule applied mechanically, not a re-judgement.\n")
        for annotator, rid, field, change in sorted(corrections, key=lambda c: (c[2], c[0], c[1])):
            print("  " + annotator.ljust(10) + " report " + rid.ljust(5) + " " +
                  field.ljust(18) + " " + change)

    if rejects:
        print("\n" + "=" * 76)
        print("ROWS REJECTED  (" + str(len(rejects)) + ")")
        print("=" * 76)
        for annotator, rid, why in rejects:
            print("  " + annotator.ljust(10) + " report " + rid.ljust(5) + " " + why)

    if args.dry_run:
        print("\n--dry-run: nothing written. " + str(len(all_rows)) + " rows would be loaded.")
        return

    written = db.executemany(UPSERT, all_rows)
    print("\n" + str(len(all_rows)) + " rows upserted into gold_labels (" +
          str(written) + " affected).")

    # Withdraw rows the source file no longer claims.
    #
    # An upsert alone cannot express "this label was retracted", and retraction happens: the
    # merge used to compare the typed is_sif_precursor column, so two reports where the
    # annotators actually differ were written into the adjudicated set with annotator A's
    # answer copied in. Fixing the merge removed them from gold_labels.csv, but the database
    # would have kept serving them - a consensus that no longer exists anywhere on disk.
    #
    # Scoped per annotator, so this only ever removes rows this run was responsible for.
    for path, annotator in SOURCES:
        if not os.path.exists(path):
            continue
        keep = [r["report_id"] for r in all_rows if r["annotator"] == annotator]
        if not keep:
            continue
        removed = db.execute(
            "DELETE FROM gold_labels WHERE annotator = %(annotator)s "
            "AND NOT (report_id = ANY(%(keep)s))",
            {"annotator": annotator, "keep": keep},
        )
        if removed:
            print("  withdrew " + str(removed) + " stale " + repr(annotator) +
                  " row(s) no longer present in " + path)

    for r in db.query("""
        SELECT annotator,
               count(*)                                      AS n,
               count(*) FILTER (WHERE is_sif_precursor)      AS precursors,
               round(avg(is_sif_precursor::int)::numeric, 3) AS rate
        FROM gold_labels GROUP BY annotator ORDER BY annotator
    """):
        print("  " + r["annotator"].ljust(10) + str(r["n"]).rjust(4) + " labels, " +
              str(r["precursors"]).rjust(3) + " precursors (rate " + str(r["rate"]) + ")")


if __name__ == "__main__":
    main()
