"""
prepare_osha_batch.py

Turn a pile of unlabelled OSHA reports into two annotator worksheets that
actually measure something.

    python prepare_osha_batch.py --a annotate_sukanya_1000.csv \
                                 --b annotate_akanksha_1000.csv \
                                 --overlap 300

WHY THIS EXISTS

The batch as delivered is split DISJOINTLY - one annotator has reports
181-680, the other 681-1180, with zero overlap. That produces a thousand
labels and no Cohen's kappa, because agreement can only be measured on
reports both people judged. We have no independent kappa to quote yet: round
one was independent and scored 52.2% agreement, kappa 0.083. Round two scored
96.1% / kappa 0.922 but was NOT run independently - it is evidence the v2.1 ->
v2.2 severity revision worked, not a ceiling, and must not be quoted as one.
"Two of us labelled independently and agreed X% of the time" is the answer to
"you wrote the reports and graded yourself", and only a genuinely independent
pass can produce it. A disjoint split cannot support one at any volume.

THE DESIGN THIS PRODUCES

  OVERLAP core     both annotators label the SAME reports, independently
                   -> Cohen's kappa, on real text nobody on the team wrote
  UNIQUE remainder split between them, single-annotated
                   -> labelling volume for training and evaluation

That is the standard arrangement: double-annotate a subset to measure
agreement, single-annotate the rest for volume. Provided the shared core is
genuinely labelled independently, you get a quotable kappa AND a large gold
set, rather than trading one for the other.

If a quotable kappa is all you need, prepare_independent_recheck.py is the
cheaper path: it samples 40 of the existing 180 reports for a fresh
independent re-label, and the worksheets already exist at
data/recheck_akanksha.csv and data/recheck_sukanya.csv. This batch is still
worth running, for the labelling volume and the base rate below.

The shared reports are interleaved and shuffled independently in each
worksheet, so neither annotator can tell which rows are the measured ones.
Knowing would change how carefully they are judged, and that would flatter
the kappa.

WHY THIS BATCH MATTERS BEYOND VOLUME

Our 150 synthetic reports were each generated centred on a hazard category,
so 92% clear Gate 1 and the precursor rate is 59% - against the 20-25% the
problem statement cites. These OSHA narratives are a real population: heart
attacks, heat exhaustion, hernias, back strains, same-level slips. Many are
Gate 1 `no`, which is exactly what the synthetic set lacks. This batch can
give us an honest base rate. See docs/eval-diagnosis.md.
"""

import argparse
import csv
import io
import os
import random
import re
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DATA_DIR = "data"

WORKSHEET_COLUMNS = ["report_id", "source", "text", "hazard_assessment", "lsr_rule",
                     "control_status", "severity", "is_sif_precursor", "notes",
                     "rubric_version", "annotator"]

# Narratives whose hazard is almost certainly outside the eight IOGP categories.
# Used ONLY to estimate the base rate before labelling - never written into a
# worksheet, never shown to an annotator. The rubric decides; this just tells us
# roughly what population we are about to spend hours on.
LIKELY_NOT_LSR = [
    r"heart attack", r"cardiac", r"heat exhaustion", r"heat stress", r"heat[- ]related",
    r"heat stroke", r"heat illness", r"heat injury", r"dehydrat", r"rhabdomyolysis",
    r"hernia", r"back (strain|injury|spasm)", r"strain(ed)? (his|her|their)? ?back",
    r"pinched nerve", r"bulging disc", r"herniated", r"muscle (injury|strain|cramp)",
    r"slipped (and|on)", r"tripped (over|on)", r"lost (his|her|their) balance",
    r"frostnip", r"blood clot", r"seizure", r"aneurysm", r"stroke",
    r"bit(ten)? (his|her|the)? ?\w* ?(thumb|hand|arm|forearm)",  # animal bites
    r"physical (fitness|training)", r"obstacle course", r"kickball", r"volleyball",
    r"altercation", r"punched", r"shot", r"bullet",
]

LIKELY_LSR = [
    r"fell (approximately )?\d+", r"fell from", r"fall(ing)? from", r"scaffold", r"ladder",
    r"roof", r"skylight", r"aerial lift", r"scissor lift", r"trench", r"excavat",
    r"lock(ed)? ?out", r"not locked out", r"energized", r"arc flash", r"electrical shock",
    r"electrocut", r"power ?line", r"volt", r"forklift", r"struck by", r"pinned",
    r"crane", r"hoist", r"rigging", r"confined space", r"manhole", r"caustic",
    r"sodium hydroxide", r"sulfuric", r"hydrofluoric", r"chemical burn", r"amputat",
]


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def looks_like(text, patterns):
    low = text.lower()
    return any(re.search(p, low) for p in patterns)


def estimate_base_rate(rows):
    """Rough population sketch. NOT labels - a sanity check on what we are about to label."""
    not_lsr = sum(1 for r in rows if looks_like(r["text"], LIKELY_NOT_LSR)
                  and not looks_like(r["text"], LIKELY_LSR))
    likely = sum(1 for r in rows if looks_like(r["text"], LIKELY_LSR))
    unclear = len(rows) - not_lsr - likely

    print(f"\n  POPULATION SKETCH (keyword heuristic, not labels)")
    print("  " + "-" * 68)
    print(f"  likely Gate 1 = no      {not_lsr:>5}  ({not_lsr/len(rows):.0%})   "
          "heart attacks, heat, hernias, strains, same-level slips")
    print(f"  likely Gate 1 = yes     {likely:>5}  ({likely/len(rows):.0%})   "
          "falls, isolation, electrical, struck-by, chemical")
    print(f"  neither pattern         {unclear:>5}  ({unclear/len(rows):.0%})")
    print("\n  Our 150 synthetic reports are 92% Gate 1 = yes, because each was")
    print("  generated centred on a hazard. This batch is a real population, which")
    print("  is why it can give us an honest base rate. The rubric decides every")
    print("  individual label - the above is only a sketch of what we are labelling.")


def write_worksheet(path, rows, annotator, rng):
    """One worksheet, shuffled so the shared reports are not identifiable."""
    out = []
    for r in rows:
        out.append({
            "report_id": r["report_id"],
            "source": "osha",
            "text": r["text"],
            "hazard_assessment": "", "lsr_rule": "", "control_status": "",
            "severity": "", "is_sif_precursor": "", "notes": "",
            "rubric_version": "2.2", "annotator": annotator,
        })
    rng.shuffle(out)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=WORKSHEET_COLUMNS)
        w.writeheader()
        w.writerows(out)
    return len(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True, help="first unlabelled batch CSV")
    ap.add_argument("--b", required=True, help="second unlabelled batch CSV")
    ap.add_argument("--name-a", default="sukanya")
    ap.add_argument("--name-b", default="akanksha")
    ap.add_argument("--overlap", type=int, default=300,
                    help="reports BOTH annotators label, for kappa (default 300)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows = read(args.a) + read(args.b)
    seen, unique = set(), []
    for r in rows:
        rid = str(r["report_id"]).strip()
        if rid in seen:
            continue
        seen.add(rid)
        unique.append({"report_id": rid, "text": (r.get("text") or "").strip()})

    print("=" * 72)
    print("  OSHA BATCH — PREPARING TWO WORKSHEETS THAT MEASURE SOMETHING")
    print("=" * 72)
    print(f"\n  {len(rows)} rows in, {len(unique)} unique report_ids "
          f"({len(rows) - len(unique)} duplicates dropped)")

    # Warn about collisions with reports already in the project.
    existing = os.path.join(DATA_DIR, "osha", "osha_real_reports.csv")
    if os.path.exists(existing):
        old = {str(r["report_id"]).strip() for r in read(existing)}
        clash = old & seen
        if clash:
            print(f"  [!] {len(clash)} report_ids collide with the existing OSHA set: "
                  f"{sorted(clash)[:6]}...")
            print("      Renumber before loading, or the join in run_eval will be wrong.")
        else:
            print(f"  no id collisions with the existing {len(old)}-report OSHA set")

    estimate_base_rate(unique)

    if args.overlap > len(unique):
        raise SystemExit(f"\n[!] --overlap {args.overlap} exceeds {len(unique)} available reports")

    rng = random.Random(args.seed)
    pool = list(unique)
    rng.shuffle(pool)

    shared = pool[:args.overlap]
    rest = pool[args.overlap:]
    half = len(rest) // 2
    only_a, only_b = rest[:half], rest[half:]

    path_a = os.path.join(DATA_DIR, f"gold_labels_{args.name_a}_osha.csv")
    path_b = os.path.join(DATA_DIR, f"gold_labels_{args.name_b}_osha.csv")
    n_a = write_worksheet(path_a, shared + only_a, args.name_a, random.Random(args.seed + 1))
    n_b = write_worksheet(path_b, shared + only_b, args.name_b, random.Random(args.seed + 2))

    print(f"\n  DESIGN")
    print("  " + "-" * 68)
    print(f"  shared (both label, gives kappa)   {len(shared):>5}")
    print(f"  {args.name_a} only                 {len(only_a):>5}")
    print(f"  {args.name_b} only                 {len(only_b):>5}")
    print(f"\n  {path_a}  {n_a} rows")
    print(f"  {path_b}  {n_b} rows")
    print("\n  Shared reports are interleaved and shuffled differently in each file, so")
    print("  neither annotator can tell which rows are the measured ones. Knowing would")
    print("  change how carefully they are judged and flatter the kappa.")

    print(f"\n  NEXT")
    print("  " + "-" * 68)
    print(f"  Each annotator, independently, no discussion until BOTH finish:")
    print(f"    python label_reports.py --annotator {args.name_a}_osha")
    print(f"    python label_reports.py --annotator {args.name_b}_osha")
    print(f"\n  Then, on the shared core only:")
    print(f"    python check_independence.py --a {path_a} --b {path_b}")
    print("  It reports agreement over the report_ids present in both, which is exactly")
    print("  the shared core. If this pass is genuinely kept independent, that number")
    print("  is a real ceiling — on real text nobody wrote, and the first one we have.")
    print("  Round one was independent and scored kappa 0.083; round two scored 0.922")
    print("  but was not independent, so it is not a ceiling and does not set a bar.")
    print("")
    print("  Cheaper path to the same number, if you want it before this batch lands:")
    print("    python prepare_independent_recheck.py")
    print("  40 of the existing 180 reports, re-labelled independently.\n")


if __name__ == "__main__":
    main()
