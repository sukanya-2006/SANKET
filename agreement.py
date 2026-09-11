"""
agreement.py

Inter-annotator agreement, computed from the live `gold_labels` table rather
than from a merged CSV.

    python agreement.py

WHY FROM THE DATABASE

The merged file (data/gold_labels.csv) has already had disagreements resolved,
so agreement cannot be recovered from it. `gold_labels` keeps each annotator's
raw row, which is the only place the two label sets can still be compared.

WHAT IT REPORTS

  - Raw agreement and Cohen's kappa on `is_sif_precursor`, the headline label.
  - The same, per gate, because a single kappa hides which gate is the problem.
    Gate 3 (severity) is where the disagreements have always been, and knowing
    that is what tells us which part of the rubric to revise.
  - Exact agreement on severity, plus agreement within one band, because "4 vs
    5" and "2 vs 5" are not the same kind of disagreement.

WHAT THIS NUMBER IS, AND WHAT IT IS NOT

It is not a ceiling and must not be quoted as one. A ceiling would need the two
annotators to have judged these reports independently, and for the rows now in
`gold_labels` they did not. Those rows are round two, and the team lead
confirmed on 11 September that the annotators did not work separately the second
time. Round two is evidence that the rubric revision helped. It bounds nothing.

Round one was independent and scored 52.2% raw, kappa 0.083, with severity the
broken gate at 14.4% - a 3-vs-4 split on 76 of the 180 reports. That is what
triggered the documented rubric revision, v2.1 -> v2.2, which rewrote the
severity gate to state the one-change rule first and to describe the bands as
observable outcomes rather than adjectives.

For a number that can be quoted, run prepare_independent_recheck.py. It samples
40 reports for a fresh independent re-label; the worksheets already exist at
data/recheck_akanksha.csv and data/recheck_sukanya.csv.
"""

import io
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv(dotenv_path=Path(__file__).resolve().parent / "backend" / ".env")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import db  # noqa: E402

A, B = "akanksha", "sukanya"

PAIRS = """
SELECT a.report_id,
       a.hazard_assessment AS hazard_a, b.hazard_assessment AS hazard_b,
       a.lsr_rule          AS rule_a,   b.lsr_rule          AS rule_b,
       a.control_status    AS control_a, b.control_status   AS control_b,
       a.severity          AS severity_a, b.severity        AS severity_b,
       a.is_sif_precursor  AS precursor_a, b.is_sif_precursor AS precursor_b
FROM gold_labels a
JOIN gold_labels b ON b.report_id = a.report_id
WHERE a.annotator = %(a)s AND b.annotator = %(b)s
ORDER BY a.report_id
"""


def kappa(pairs):
    """Cohen's kappa. pairs is a list of (label_a, label_b)."""
    n = len(pairs)
    if n == 0:
        return None
    observed = sum(1 for x, y in pairs if x == y) / n

    count_a = Counter(x for x, _ in pairs)
    count_b = Counter(y for _, y in pairs)
    categories = set(count_a) | set(count_b)
    expected = sum((count_a[c] / n) * (count_b[c] / n) for c in categories)

    if expected == 1.0:
        # Both annotators used one category for everything. Agreement is total and
        # kappa is undefined - reporting 0.0 here would read as total disagreement.
        return None
    return (observed - expected) / (1 - expected)


def report(title, pairs):
    n = len(pairs)
    raw = sum(1 for x, y in pairs if x == y) / n
    k = kappa(pairs)
    k_text = "undefined (one category)" if k is None else ("%.3f" % k)
    print("  %-26s %3d/%3d  raw %5.1f%%   kappa %s"
          % (title, sum(1 for x, y in pairs if x == y), n, raw * 100, k_text))
    return raw, k


def main():
    if not db.is_live():
        sys.exit("[!] Database not connected. Run load_gold_labels.py first.")

    rows = db.query(PAIRS, {"a": A, "b": B})
    if not rows:
        sys.exit("[!] No overlapping labels between %r and %r in gold_labels." % (A, B))

    print("=" * 78)
    print("  INTER-ANNOTATOR AGREEMENT — %s vs %s" % (A, B))
    print("=" * 78)
    print("\n  %d reports labelled by both.\n" % len(rows))
    print("  Round two - not independent, not a ceiling. See the note at the end.\n")

    print("  HEADLINE")
    print("  " + "-" * 74)
    report("is_sif_precursor",
           [(r["precursor_a"], r["precursor_b"]) for r in rows])

    print("\n  PER GATE")
    print("  " + "-" * 74)
    report("gate 1  hazard_assessment",
           [(r["hazard_a"], r["hazard_b"]) for r in rows])
    report("        lsr_rule",
           [(r["rule_a"], r["rule_b"]) for r in rows])

    # Gate 2 only exists where both called Gate 1 'yes'. Scoring it on rows where
    # one annotator said 'no' would count a NULL against a real judgement.
    both_yes = [r for r in rows if r["hazard_a"] == "yes" and r["hazard_b"] == "yes"]
    if both_yes:
        report("gate 2  control_status",
               [(r["control_a"], r["control_b"]) for r in both_yes])
        print("          (scored on the %d reports where both said hazard = yes)"
              % len(both_yes))

    report("gate 3  severity exact",
           [(r["severity_a"], r["severity_b"]) for r in rows])

    within_one = sum(1 for r in rows if abs(r["severity_a"] - r["severity_b"]) <= 1)
    print("  %-26s %3d/%3d  raw %5.1f%%"
          % ("        severity within 1", within_one, len(rows), within_one / len(rows) * 100))

    print("\n  SEVERITY SHIFT  (%s minus %s)" % (A, B))
    print("  " + "-" * 74)
    shift = Counter(r["severity_a"] - r["severity_b"] for r in rows)
    line = "   ".join("%+d: %d" % (d, shift[d]) for d in sorted(shift))
    print("  " + line)
    mean = sum(r["severity_a"] - r["severity_b"] for r in rows) / len(rows)
    print("  mean %+.2f" % mean)

    disagreed = [r for r in rows if r["precursor_a"] != r["precursor_b"]]
    print("\n  THE %d REPORTS WHERE THE HEADLINE LABEL DIFFERS" % len(disagreed))
    print("  " + "-" * 74)
    if not disagreed:
        print("  none")
    else:
        for r in disagreed:
            # Name the gate that produced the split, which is the thing worth fixing.
            if r["hazard_a"] != r["hazard_b"]:
                gate = "gate 1"
            elif r["control_a"] != r["control_b"]:
                gate = "gate 2"
            elif r["severity_a"] != r["severity_b"]:
                gate = "gate 3"
            else:
                gate = "none"
            print("  report %-5s %s  %s(h=%s c=%s s=%s)  %s(h=%s c=%s s=%s)"
                  % (r["report_id"], gate,
                     A[:3], r["hazard_a"], r["control_a"], r["severity_a"],
                     B[:3], r["hazard_b"], r["control_b"], r["severity_b"]))

    print("\n  " + "-" * 74)
    print("  Round two - not independent, not a ceiling. The annotators did not work")
    print("  separately the second time, so the figures above are evidence that the")
    print("  v2.2 severity rewrite helped, not a bound on what a classifier can do.")
    print("  Do not quote them as a ceiling. For a kappa that can be quoted, run")
    print("  prepare_independent_recheck.py: 40 reports, fresh independent re-label.")


if __name__ == "__main__":
    main()
