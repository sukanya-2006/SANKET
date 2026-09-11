"""
score_recheck.py

Score the independent re-check that finally gives this project a quotable
inter-annotator ceiling.

    python score_recheck.py

BACKGROUND

Round one was independent and agreed 52.2% (kappa 0.083) under rubric v2.1.
Round two agreed 96.1% but was not run independently, so it bounded nothing.
For weeks the project had no defensible agreement number at all.

`prepare_independent_recheck.py` sampled 40 of the 180 labelled reports,
stratified across the label and across severity, and wrote two worksheets
shuffled differently so neither annotator could infer anything from position.
Both were completed separately, under rubric v2.2 - the same version the shipped
prompt encodes.

WHAT IT REPORTS, AND THE TWO TRAPS IT AVOIDS

`is_sif_precursor` is DERIVED from the three gates, never read from a column.
It is not even a column in the worksheets, because every time it has been
offered as something to type, someone has typed a value contradicting their own
gates - and that then silently decided whether two people "agreed".

Cohen's kappa goes degenerate when one category takes nearly every row. Both
annotators answered `yes` to Gate 1 on 37 of 38 reports, which is near-total
agreement and a kappa close to zero, because kappa measures agreement ABOVE
chance and chance is almost 100% when there is no variance to disagree about.
Reporting that as "kappa 0.000" would read as total disagreement and be exactly
backwards. Gate 1 is therefore reported as raw agreement with the kappa
suppressed and the reason named.

Rows either annotator left incomplete are excluded and listed. A missing
judgement is not a disagreement, and counting it as one would understate the
number while counting it as agreement would inflate it.
"""

import csv
import io
import sys
from collections import Counter

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FILES = [("akanksha", "data/recheck_akanksha.csv"),
         ("sukanya", "data/recheck_sukanya.csv")]

# Below this share for the commonest category, kappa stops being informative.
DEGENERATE_AT = 0.95


def load(path):
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        rid = str(r["report_id"]).strip()
        hazard = (r.get("hazard_assessment") or "").strip().lower()
        control = (r.get("control_status") or "").strip().lower() or None
        if hazard != "yes":
            # Rubric section 2: no control to assess for a hazard we could not name.
            control = None
        raw = (r.get("severity") or "").strip()
        severity = int(float(raw)) if raw else None
        out[rid] = {
            "hazard": hazard,
            "rule": (r.get("lsr_rule") or "").strip().lower().replace(" ", "_"),
            "control": control,
            "severity": severity,
            "precursor": (hazard == "yes"
                          and control in ("absent", "failed")
                          and severity is not None
                          and severity >= 4),
        }
    return out


def kappa(pairs):
    n = len(pairs)
    observed = sum(1 for x, y in pairs if x == y) / n
    ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    expected = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    if expected >= 1.0:
        return observed, None
    return observed, (observed - expected) / (1 - expected)


def degenerate(pairs):
    """True when one category dominates enough that kappa stops meaning anything."""
    n = len(pairs)
    counts = Counter(x for x, _ in pairs) + Counter(y for _, y in pairs)
    return counts.most_common(1)[0][1] / (2 * n) >= DEGENERATE_AT


def line(label, pairs, note=""):
    n = len(pairs)
    agreed = sum(1 for x, y in pairs if x == y)
    observed, k = kappa(pairs)
    if k is None or degenerate(pairs):
        shown = "n/a"
        note = note or "one category takes nearly every row - kappa uninformative"
    else:
        shown = "%.3f" % k
    print("  %-22s %2d/%-2d  %5.1f%%   kappa %-6s %s"
          % (label, agreed, n, observed * 100, shown, note))


def main():
    a, b = load(FILES[0][1]), load(FILES[1][1])

    both = set(a) & set(b)
    incomplete = sorted(
        [(FILES[0][0], i) for i in both if not a[i]["hazard"] or a[i]["severity"] is None]
        + [(FILES[1][0], i) for i in both if not b[i]["hazard"] or b[i]["severity"] is None],
        key=lambda x: x[1])
    skip = {i for _, i in incomplete}
    ids = sorted(both - skip, key=lambda x: int(x) if x.isdigit() else 0)

    print("=" * 78)
    print("  INDEPENDENT RE-CHECK — %s vs %s" % (FILES[0][0], FILES[1][0]))
    print("=" * 78)
    print("\n  %d reports sampled, %d scorable." % (len(both), len(ids)))
    if incomplete:
        print("  Excluded as incomplete: %s"
              % ", ".join("%s left report %s blank" % (who, i) for who, i in incomplete))
    print()

    print("  HEADLINE")
    print("  " + "-" * 74)
    line("is_sif_precursor", [(a[i]["precursor"], b[i]["precursor"]) for i in ids])

    print("\n  PER GATE")
    print("  " + "-" * 74)
    line("gate 1 hazard", [(a[i]["hazard"], b[i]["hazard"]) for i in ids])
    line("lsr_rule", [(a[i]["rule"], b[i]["rule"]) for i in ids])

    both_yes = [i for i in ids if a[i]["hazard"] == "yes" and b[i]["hazard"] == "yes"]
    if both_yes:
        line("gate 2 control", [(a[i]["control"], b[i]["control"]) for i in both_yes],
             "scored where both said hazard = yes")
    line("gate 3 severity exact", [(a[i]["severity"], b[i]["severity"]) for i in ids])

    within = sum(1 for i in ids if abs(a[i]["severity"] - b[i]["severity"]) <= 1)
    print("  %-22s %2d/%-2d  %5.1f%%" % ("severity within 1", within, len(ids),
                                         within / len(ids) * 100))

    disagreed = [i for i in ids if a[i]["precursor"] != b[i]["precursor"]]
    print("\n  HEADLINE DISAGREEMENTS  (%d)" % len(disagreed))
    print("  " + "-" * 74)
    for i in disagreed:
        print("  report %-5s  %s(h=%s c=%s s=%s)   %s(h=%s c=%s s=%s)"
              % (i, FILES[0][0][:3], a[i]["hazard"], a[i]["control"], a[i]["severity"],
                 FILES[1][0][:3], b[i]["hazard"], b[i]["control"], b[i]["severity"]))
    if not disagreed:
        print("  none")

    print("\n  " + "-" * 74)
    print("  This IS a ceiling: both annotators judged these reports separately, under")
    print("  rubric v2.2, with no contact until both files were finished.")
    print()
    print("  Two caveats to state before anyone asks. n is small, so the confidence")
    print("  interval is wide - quote it as \"on a 38-report independent subset\". And")
    print("  these are re-labels: both annotators had seen these reports in earlier")
    print("  rounds, so familiarity flatters the number relative to two people reading")
    print("  them cold.")


if __name__ == "__main__":
    main()
