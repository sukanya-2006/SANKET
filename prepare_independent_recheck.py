"""
prepare_independent_recheck.py

Produce a real inter-annotator ceiling, in about two hours of two people's time.

    python prepare_independent_recheck.py              # 40 reports, the default
    python prepare_independent_recheck.py --n 60

Writes:
    data/recheck_akanksha.csv
    data/recheck_sukanya.csv

WHY THIS EXISTS

Our second labelling round scored 96.1% agreement, Cohen's kappa 0.922. It was not run
independently, so it is not a ceiling and we do not quote it as one. Round one WAS independent
and scored 52.2% (kappa 0.083) - but that was under rubric v2.1, whose severity gate we have
since rewritten, so it does not describe the rubric we ship either.

That leaves us with no defensible agreement number. This script is the cheapest way to get one.

WHY A SUBSET IS ENOUGH

Cohen's kappa on 40 reports has a wide confidence interval, and that is fine: the claim is
"two people applying this rubric to the same reports disagree about this often", not a precise
population estimate. 40 double-labelled reports support that claim. 180 would support it more
precisely at four and a half times the cost, and nobody is going to challenge the sample size
before they challenge the independence.

Report it as "n=40, independently re-labelled" and the number is defensible. That is the whole
point - a smaller honest number beats a larger one you have to qualify away.

THE SAMPLE

Stratified across the label and across severity, so the subset is not accidentally all easy
cases. A sample drawn only from clear precursors would flatter the agreement, and a sample
drawn only from the 3/4 boundary would crush it. Both would be worthless.

Reports are ordered differently in each file, so neither annotator can tell which report the
other is on, and neither can infer anything from position.

THE RULE THAT MAKES THE NUMBER REAL

No contact until both files are finished. Not "we mostly didn't discuss it" - none. No checking
each other's answers on a hard one, no "what did you put for 47", no adjudicating into both
files afterwards. If that rule is broken the number is worth nothing again, and the only person
who can enforce it is each annotator.

When both are done:

    python check_independence.py --a data/recheck_akanksha.csv --b data/recheck_sukanya.csv
"""

import argparse
import csv
import io
import os
import random
import sys
from collections import defaultdict

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GOLD = "data/gold_labels.csv"
REPORTS = "data/synthetic/synthetic_reports_for_labeling.csv"

COLUMNS = ["report_id", "text", "hazard_assessment", "lsr_rule", "control_status",
           "severity", "notes", "rubric_version", "annotator"]

# is_sif_precursor is deliberately NOT a column here.
#
# It is derived from the three gates (rubric sections 2 and 6), and every time it has been
# offered as something to type, someone has typed a value contradicting their own gates - which
# then silently decided whether two people "agreed". Leaving it out makes that impossible.


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def stratum(row):
    """Bucket a report so the sample spans easy and hard cases, not just one or the other."""
    try:
        severity = int(float(row["severity"]))
    except (TypeError, ValueError):
        return "unknown"

    hazard = (row["hazard_assessment"] or "").strip().lower()
    if hazard != "yes":
        return "no hazard"
    if severity >= 4:
        return "precursor (sev %d)" % severity
    if severity == 3:
        return "boundary (sev 3)"      # the 3/4 line, where the disagreements live
    return "hazard, low severity"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40, help="reports to double-label (default 40)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--name-a", default="akanksha")
    ap.add_argument("--name-b", default="sukanya")
    args = ap.parse_args()

    if not os.path.exists(GOLD):
        raise SystemExit("[!] %s not found - run merge_labels.py first." % GOLD)

    gold = read(GOLD)
    texts = {str(r["report_id"]).strip(): r["text"] for r in read(REPORTS)}

    buckets = defaultdict(list)
    for r in gold:
        rid = str(r["report_id"]).strip()
        if rid in texts:
            buckets[stratum(r)].append(rid)

    print("=" * 74)
    print("  INDEPENDENT RE-CHECK — sampling %d of %d labelled reports" % (args.n, len(gold)))
    print("=" * 74)
    print("\n  strata available")
    print("  " + "-" * 70)
    for name in sorted(buckets):
        print("    %-26s %3d reports" % (name, len(buckets[name])))

    # Proportional allocation, at least one from every stratum that exists.
    rng = random.Random(args.seed)
    total = sum(len(v) for v in buckets.values())
    picked = []
    for name in sorted(buckets):
        ids = sorted(buckets[name])
        rng.shuffle(ids)
        want = max(1, round(args.n * len(ids) / total))
        picked.extend(ids[:want])

    picked = sorted(set(picked))
    rng.shuffle(picked)
    picked = picked[:args.n]

    print("\n  sampled")
    print("  " + "-" * 70)
    chosen = defaultdict(int)
    by_id = {str(r["report_id"]).strip(): r for r in gold}
    for rid in picked:
        chosen[stratum(by_id[rid])] += 1
    for name in sorted(chosen):
        print("    %-26s %3d" % (name, chosen[name]))
    print("    %-26s %3d" % ("TOTAL", len(picked)))

    for name, seed_offset in ((args.name_a, 1), (args.name_b, 2)):
        rows = [{
            "report_id": rid,
            "text": texts[rid],
            "hazard_assessment": "", "lsr_rule": "", "control_status": "",
            "severity": "", "notes": "",
            "rubric_version": "2.2", "annotator": name,
        } for rid in picked]
        # Shuffled differently per annotator so neither can infer anything from position.
        random.Random(args.seed + seed_offset).shuffle(rows)

        path = "data/recheck_%s.csv" % name
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(rows)
        print("\n  %s   %d rows" % (path, len(rows)))

    print("\n  " + "-" * 70)
    print("  THE RULE. No contact until BOTH files are finished. Not 'we mostly did not")
    print("  discuss it' - none. No checking a hard one against the other, no adjudicating")
    print("  into both files afterwards. Break it and the number is worth nothing again.")
    print("\n  is_sif_precursor is not a column. It is derived from the three gates, and")
    print("  every time it has been offered as something to type, someone has typed a value")
    print("  that contradicted their own gates.")
    print("\n  Then:")
    print("    python check_independence.py --a data/recheck_%s.csv --b data/recheck_%s.csv"
          % (args.name_a, args.name_b))
    print()


if __name__ == "__main__":
    main()
