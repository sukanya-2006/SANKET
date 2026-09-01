"""
label_reports.py

A terminal labelling tool for the two annotators. One report at a time, one
gate at a time, saving after every single report so a crash or a Ctrl+C never
costs more than the row you were on.

    python label_reports.py --annotator vishnu
    python label_reports.py --annotator vishnu --stats
    python label_reports.py --annotator vishnu --review 47

WHAT THIS TOOL DOES NOT DO: it never suggests, predicts, or hints at a label.
Not once. Two annotators labelling independently is the only reason Cohen's
kappa means anything, and it is our answer to "you wrote the reports and graded
yourself" - a tool that nudged you toward an answer would quietly destroy the
number the whole pitch rests on. This is a data-entry accelerator and a
validator. The judgement is yours.

What it DOES do, beyond saving you from Excel:

  * Enforces the enums, so no typo silently becomes an invalid label that
    merge_labels.py then treats as a disagreement.
  * Skips Gate 2 when Gate 1 is not `yes`, per rubric v2.1 section 2 - the
    database rejects a control_status without a hazard anyway.
  * DERIVES is_sif_precursor from the section 6 decision table rather than
    asking you. The rubric says this field is "never set by feel", and the
    fastest way to break a label set is to let a tired annotator eyeball it
    at report 140.
  * Refuses to move on without notes where the rubric makes them mandatory.
  * Resumes exactly where you stopped.

Rubric v2.1 lives in docs/rubric.md. Keep it open. Press ? at any prompt for
the condensed gate reference.
"""

import argparse
import csv
import io
import os
import shutil
import sys
import textwrap

# The reports contain typographic characters — non-breaking hyphens, en dashes, curly quotes —
# and the default Windows console codepage cannot encode them. Without this the tool crashes
# partway through the set, on whichever report happens to contain one.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DATA_DIR = "data"

HAZARD = {"y": "yes", "n": "no", "i": "insufficient_information"}

LSR_RULES = [
    "energy_isolation",
    "work_at_height",
    "lifting",
    "line_of_fire",
    "confined_space",
    "hot_work",
    "driving",
    "permit_to_work",
]

CONTROL = {"a": "absent", "f": "failed", "p": "present", "u": "unclear"}

JUDGMENT_COLUMNS = ["hazard_assessment", "lsr_rule", "control_status",
                    "severity", "is_sif_precursor", "notes"]

RUBRIC_HELP = """
  GATE 1 - hazard_assessment
    yes  - a high-energy hazard in one of the eight IOGP categories
    no   - same-level slips, manual handling, hand tools, minor sharps,
           heat stress, housekeeping. Real injuries, not what this is for.
    insufficient_information - the text does not say what happened.
           Target under 10%. Not a soft "no" - these go to a human.

  GATE 2 - control_status   (only asked when Gate 1 is yes)
    absent  - none existed, or it was not used, removed, bypassed, disabled
    failed  - it was in place and did NOT hold
    present - rated, targeted, in place, and it did its job. STOPS the
              assessment. The narrative must say so - you may not infer it.
    unclear - hazard is clear but the text does not say what the control did.
              An injury occurring is NOT evidence the control failed.

    A person intervening counts as `present` only if it happened BEFORE
    anyone was exposed. Self-rescue is never a control.
    A control that stopped the event is `present` even if damaged doing so.

  GATE 3 - severity, scored on the PLAUSIBLE VARIATION, not what happened
    5 - fatality        4 - life-altering (amputation, major burn, spinal,
    3 - lost time           permanent impairment, ICU)
    2 - medical treatment   1 - first aid at most
    An actual fatality/amputation/ICU scores 4-5 by definition - but that
    governs severity ONLY, never Gate 1.

  is_sif_precursor is DERIVED: hazard yes AND control absent/failed AND
  severity >= 4. You do not set it.
"""


def path_for(annotator):
    return os.path.join(DATA_DIR, f"gold_labels_{annotator}.csv")


def load(path):
    if not os.path.exists(path):
        raise SystemExit(
            f"{path} not found.\n"
            f"Generate it first:  python create_labeling_template.py --annotator <name>"
        )
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader), list(reader.fieldnames)


def save(path, rows, fieldnames):
    """Write via a temp file and replace, so Ctrl+C mid-write cannot truncate the file."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    shutil.move(tmp, path)


def is_labelled(row):
    return bool((row.get("hazard_assessment") or "").strip())


def derive_precursor(hazard, control, severity):
    """Rubric v2.1 section 6. Never set by feel."""
    return hazard == "yes" and control in ("absent", "failed") and int(severity) >= 4


def rule():
    print("-" * 72)


def ask(prompt, valid, allow_help=True):
    """Prompt until the answer is in `valid`. Returns lowercase, or a control word."""
    while True:
        try:
            raw = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nStopping. Everything up to the last completed report is saved.")
            sys.exit(0)
        if raw in ("q", "quit"):
            return "__quit__"
        if raw in ("s", "skip"):
            return "__skip__"
        if allow_help and raw == "?":
            print(RUBRIC_HELP)
            continue
        if raw in valid:
            return raw
        print(f"  ! expected one of: {', '.join(sorted(valid))}   (? = rubric, s = skip, q = quit)")


def show_report(row, index, total, done):
    rule()
    print(f"  Report {index + 1} of {total}   |   {done} labelled   |   "
          f"id {row.get('report_id')}   |   source: {row.get('source')}")
    rule()
    text = (row.get("text") or row.get("report_text") or "").strip()
    for line in textwrap.wrap(text, width=72) or ["(no text)"]:
        print(f"  {line}")
    rule()


def label_one(row):
    """Walk the three gates. Returns a dict of judgments, or None if skipped/quit."""
    hazard_key = ask("  Gate 1 - hazard?  [y]es / [n]o / [i]nsufficient : ", set(HAZARD))
    if hazard_key in ("__quit__", "__skip__"):
        return hazard_key
    hazard = HAZARD[hazard_key]

    lsr = "none"
    control = ""

    if hazard == "yes":
        print("\n  Gate 1 - which Life-Saving Rule?")
        for i, name in enumerate(LSR_RULES, start=1):
            print(f"    {i}. {name}")
        print("  (Precedence if several apply: confined_space > work_at_height >")
        print("   energy_isolation > line_of_fire > lifting > driving > hot_work > permit_to_work)")
        choice = ask("  rule number : ", {str(i) for i in range(1, len(LSR_RULES) + 1)})
        if choice in ("__quit__", "__skip__"):
            return choice
        lsr = LSR_RULES[int(choice) - 1]

        control_key = ask(
            "\n  Gate 2 - control?  [a]bsent / [f]ailed / [p]resent / [u]nclear : ", set(CONTROL)
        )
        if control_key in ("__quit__", "__skip__"):
            return control_key
        control = CONTROL[control_key]

    sev = ask(
        "\n  Gate 3 - severity of the PLAUSIBLE VARIATION  [1-5] : ",
        {"1", "2", "3", "4", "5"},
    )
    if sev in ("__quit__", "__skip__"):
        return sev

    precursor = derive_precursor(hazard, control, sev)

    notes_required = hazard == "insufficient_information" or control == "unclear"
    while True:
        try:
            note = input(
                f"\n  notes{' (REQUIRED)' if notes_required else ' (optional)'} : "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStopping. Everything up to the last completed report is saved.")
            sys.exit(0)
        if note or not notes_required:
            break
        print("  ! rubric section 2: notes are mandatory for insufficient_information and unclear.")

    verdict = "SIF PRECURSOR" if precursor else "not a precursor"
    derivation = (
        f"hazard={hazard}"
        + (f", control={control}" if control else "")
        + f", severity={sev}"
    )
    print(f"\n  -> {verdict}   ({derivation})")

    return {
        "hazard_assessment": hazard,
        "lsr_rule": lsr,
        "control_status": control,
        "severity": sev,
        "is_sif_precursor": "TRUE" if precursor else "FALSE",
        "notes": note,
    }


def print_stats(rows):
    total = len(rows)
    done = [r for r in rows if is_labelled(r)]
    print(f"\n  Labelled: {len(done)} of {total}  ({len(done) / total:.0%})")
    if not done:
        print("  Nothing labelled yet.\n")
        return

    def tally(col):
        out = {}
        for r in done:
            key = (r.get(col) or "(blank)").strip() or "(blank)"
            out[key] = out.get(key, 0) + 1
        return sorted(out.items(), key=lambda kv: -kv[1])

    precursors = sum(1 for r in done if (r.get("is_sif_precursor") or "").upper() == "TRUE")
    print(f"  Precursors: {precursors} of {len(done)}  ({precursors / len(done):.0%})")
    print("    plan expects 20-25% across the finished set; drifting far outside")
    print("    that is worth noticing early, not at report 180.")

    insufficient = sum(
        1 for r in done if r.get("hazard_assessment") == "insufficient_information"
    )
    print(f"  insufficient_information: {insufficient} ({insufficient / len(done):.0%})"
          f"   - rubric section 3 targets under 10%")

    for col in ("hazard_assessment", "control_status", "lsr_rule"):
        print(f"\n  {col}:")
        for key, count in tally(col):
            print(f"    {key:28s} {count}")
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--annotator", required=True, help="your name, matching the CSV filename")
    parser.add_argument("--stats", action="store_true", help="show progress and stop")
    parser.add_argument("--review", type=int, metavar="N",
                        help="re-label report at position N (1-based), overwriting it")
    args = parser.parse_args()

    path = path_for(args.annotator)
    rows, fieldnames = load(path)

    for col in JUDGMENT_COLUMNS:
        if col not in fieldnames:
            raise SystemExit(f"{path} has no '{col}' column - regenerate the template.")

    if args.stats:
        print_stats(rows)
        return

    if args.review:
        targets = [args.review - 1]
        if not 0 <= targets[0] < len(rows):
            raise SystemExit(f"--review must be between 1 and {len(rows)}")
    else:
        targets = [i for i, r in enumerate(rows) if not is_labelled(r)]

    if not targets:
        print("\n  All 180 reports are labelled.")
        print_stats(rows)
        print("  Next, once the OTHER annotator is also finished:")
        print(f"    python merge_labels.py --a {path} --b data/gold_labels_<other>.csv\n")
        return

    total = len(rows)
    print(__doc__.split("Rubric v2.1")[0].strip())
    print(f"\n  {len(targets)} reports left. Press ? for the gate reference, "
          f"s to skip, q to stop.\n")

    for position in targets:
        row = rows[position]
        done = sum(1 for r in rows if is_labelled(r))
        show_report(row, position, total, done)

        result = label_one(row)
        if result == "__quit__":
            break
        if result == "__skip__":
            print("  (skipped)")
            continue

        row.update(result)
        row["rubric_version"] = "2.1"
        row["annotator"] = args.annotator
        save(path, rows, fieldnames)  # after every report, not at the end

    save(path, rows, fieldnames)
    print()
    print_stats(rows)
    print(f"  Saved to {path}.")
    print("  Remember: no discussing any case with the other annotator until you are BOTH")
    print("  completely finished. That independence is what makes the kappa mean anything.\n")


if __name__ == "__main__":
    main()
