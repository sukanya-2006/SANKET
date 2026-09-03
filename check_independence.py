"""
check_independence.py

Answers one question: is this agreement number a CEILING we can quote, or a
number produced after someone saw the disagreements?

    python check_independence.py --a data/gold_labels_akanksha.csv \
                                 --b data/global_labels_sukanya2.csv
    python check_independence.py --a data/global_labels_akankshaM6.csv \
                                 --b data/global_labels_sukanyaM6.csv \
                                 --baseline-a data/gold_labels_akanksha.csv \
                                 --baseline-b data/global_labels_sukanya2.csv

WHY THIS EXISTS

"Two of us labelled independently and agreed X% of the time. That's the ceiling."
is the single strongest sentence in the pitch, and the whole answer to "you wrote
the reports and graded yourself". It is only true if neither file was touched
after the two were compared.

Three things silently break it, and all three have already happened once on this
project:

  1. An annotator revises their own file after seeing where they disagreed.
     Agreement goes up, independence is gone, the number means nothing.
  2. A tiebreaker edits BOTH annotators' files rather than writing rulings to a
     separate gold file. Then you are measuring agreement between two files the
     same person edited, which is not agreement at all.
  3. An annotator types is_sif_precursor by hand instead of deriving it from
     their own three gates. Then the headline number measures their typing, not
     the rubric.

A legitimate second round exists: the rubric fails its check, gets revised, and
BOTH annotators re-label from scratch without conferring. That produces a real,
quotable ceiling. This script cannot tell that apart from contamination on its
own - only you know which happened - but it shows you the fingerprints of each,
so you can answer honestly instead of hopefully.
"""

import argparse
import csv
import io
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GATES = ["hazard_assessment", "lsr_rule", "control_status", "severity"]


def load(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {r["report_id"]: r for r in csv.DictReader(fh)}


def truthy(v):
    return str(v or "").strip().upper() == "TRUE"


def derive(row):
    """Rubric v2.1 section 6. This is what is_sif_precursor is DEFINED as."""
    hazard = (row.get("hazard_assessment") or "").strip()
    control = (row.get("control_status") or "").strip()
    try:
        severity = int(row.get("severity") or 0)
    except ValueError:
        return None
    return hazard == "yes" and control in ("absent", "failed") and severity >= 4


def kappa(ya, yb):
    from sklearn.metrics import cohen_kappa_score

    if len(set(ya + yb)) < 2:
        return float("nan")
    return cohen_kappa_score(ya, yb)


def rule(char="-"):
    print("  " + char * 70)


def self_consistency(name, rows):
    """Did this annotator DERIVE the label, or type it by feel?"""
    bad = [k for k, r in rows.items() if derive(r) is not None and derive(r) != truthy(r["is_sif_precursor"])]
    pct = len(bad) / len(rows)
    verdict = "OK" if pct <= 0.05 else "*** BROKEN ***"
    print(f"  {name:<22} {len(bad):>4}/{len(rows)} rows contradict their own gates "
          f"({pct:.0%})  {verdict}")
    return bad


def drift(label, old, new):
    """How much did a file change between two versions?"""
    shared = [k for k in old if k in new]
    changed = {c: 0 for c in GATES + ["is_sif_precursor"]}
    rows_changed = 0
    for k in shared:
        diff = [c for c in changed if (old[k].get(c) or "").strip() != (new[k].get(c) or "").strip()]
        if diff:
            rows_changed += 1
        for c in diff:
            changed[c] += 1
    print(f"  {label}: {rows_changed}/{len(shared)} rows altered ({rows_changed/len(shared):.0%})")
    for c, n in changed.items():
        if n:
            print(f"      {c:<22} {n:>4} changed")
    return rows_changed, len(shared)


def agreement(A, B, use_derived):
    ids = [k for k in A if k in B]
    if use_derived:
        ya = [derive(A[k]) for k in ids]
        yb = [derive(B[k]) for k in ids]
    else:
        ya = [truthy(A[k]["is_sif_precursor"]) for k in ids]
        yb = [truthy(B[k]["is_sif_precursor"]) for k in ids]
    raw = sum(x == y for x, y in zip(ya, yb)) / len(ids)
    return raw, kappa(ya, yb), sum(ya) / len(ya), sum(yb) / len(yb), len(ids)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True, help="annotator A's file")
    ap.add_argument("--b", required=True, help="annotator B's file")
    ap.add_argument("--baseline-a", help="A's ORIGINAL file, to measure drift against")
    ap.add_argument("--baseline-b", help="B's ORIGINAL file, to measure drift against")
    args = ap.parse_args()

    A, B = load(args.a), load(args.b)

    print("\n" + "=" * 74)
    print("  IS THIS A CEILING WE CAN QUOTE?")
    print("=" * 74)

    # --- 1. did each annotator derive the label from their own gates? ---
    print("\n  1. SELF-CONSISTENCY — was is_sif_precursor derived, or typed by feel?")
    rule()
    bad_a = self_consistency("A  " + args.a.split("/")[-1], A)
    bad_b = self_consistency("B  " + args.b.split("/")[-1], B)
    print("\n     The rubric says this field is never set by feel. If either line reads")
    print("     BROKEN, the headline number is measuring typing, not the rubric.")

    # --- 2. agreement, both ways ---
    print("\n  2. AGREEMENT")
    rule()
    print(f"  {'':<22}{'raw':>9}{'kappa':>9}{'pos A':>9}{'pos B':>9}")
    for use_derived, label in [(False, "as typed"), (True, "as DERIVED (true)")]:
        raw, k, pa, pb, n = agreement(A, B, use_derived)
        print(f"  {label:<22}{raw:>8.1%}{k:>9.3f}{pa:>8.0%}{pb:>9.0%}")
    print(f"\n     n = {n}.  Quote the DERIVED row - it is what the rubric defines.")
    print("     Design target for the positive rate is 20-25%.")

    print("\n  3. PER-GATE AGREEMENT — which gate is weakest")
    rule()
    ids = [k for k in A if k in B]
    for col in GATES:
        ag = sum((A[k].get(col) or "").strip() == (B[k].get(col) or "").strip() for k in ids) / len(ids)
        flag = "  <-- weakest" if col == "severity" else ""
        print(f"  {col:<24}{ag:>8.1%}{flag}")

    # --- 4. drift against the originals ---
    if args.baseline_a and args.baseline_b:
        print("\n  4. DRIFT — how much did these files change from the originals?")
        rule()
        ra, na = drift("A", load(args.baseline_a), A)
        rb, nb = drift("B", load(args.baseline_b), B)

        print("\n     HOW TO READ THIS:")
        print("     - Both files barely changed  -> these ARE the originals; number stands.")
        print("     - BOTH files changed a lot   -> either a legitimate full re-label after a")
        print("       rubric revision (quotable), or someone edited both after seeing the")
        print("       disagreements (NOT quotable). Only you know which. If a tiebreaker")
        print("       edited both, this is not agreement - it is one person agreeing with")
        print("       themselves.")
        print("     - Only the disputed rows changed -> these are adjudicated files. Their")
        print("       agreement is high BY CONSTRUCTION and must never be quoted as a")
        print("       ceiling. Adjudicated labels are the gold set; the ceiling comes from")
        print("       the round BEFORE adjudication.")

    print("\n" + "=" * 74)
    print("  The ceiling is measured between two annotators who had not seen each")
    print("  other's answers. Anything measured after that is a gold set, not a ceiling.")
    print("=" * 74 + "\n")


if __name__ == "__main__":
    main()
