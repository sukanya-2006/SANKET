"""
run_eval.py — the evaluation table. Artifact #1 of the three that matter most.

    python eval/run_eval.py
    python eval/run_eval.py --no-llm          # baseline only, no API calls
    python eval/run_eval.py --open-held-out   # the one run that counts

OWNERSHIP: Member 3 owns evaluation per the master plan. This was written by
Member 1/4 while labelling was the bottleneck, so it would be ready the hour
gold_labels.csv lands rather than started then. M3 should review and take it
over - particularly the split policy in section 2, which is a judgement call
about how honest we are being with ourselves.

------------------------------------------------------------------------------
WHAT THIS PRINTS, AND WHY IT IS SHAPED THIS WAY

Two tables and one line. Never a single merged table.

  Table 1  Synthetic held-out split: baseline vs LLM.
           The fair, apples-to-apples fight. Both models trained/tuned on the
           same population they are tested on.

  Table 2  OSHA set: LLM only.
           A generalisation check on real writing nobody on the team produced.
           The baseline is trained on synthetic reports, so testing it here
           would measure domain transfer rather than model quality - an unfair
           fight we would win for the wrong reason. We do not stage it.

  Line     Severity MAE on precursor cases, against adjudicated human severity.
           Being wrong by one level and by three are different mistakes; a
           classification metric would treat them identically.

  Ceiling  Annotator agreement % and Cohen's kappa.
           Quoted first, deliberately. If two humans applying the same written
           rubric agree 88% of the time, nothing scored against those labels
           can honestly claim 95%.

ACCURACY IS NEVER REPORTED. At ~22% positives, "always say no" scores 78%.
This script will refuse to compute it.
------------------------------------------------------------------------------
"""

import argparse
import csv
import io
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GOLD = ROOT / "data" / "gold_labels.csv"
SYNTHETIC = ROOT / "data" / "synthetic" / "synthetic_reports_for_labeling.csv"
OSHA = ROOT / "data" / "osha" / "osha_real_reports.csv"
SPLIT_FILE = ROOT / "eval" / "split.json"

DEV_SIZE = 30
SEED = 42


# ---------------------------------------------------------------------------
# 1. Loading
# ---------------------------------------------------------------------------


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_dataset():
    """Gold labels joined to report text. Fails loudly about what is missing."""
    if not GOLD.exists():
        raise SystemExit(
            f"\n[!] {GOLD} does not exist yet.\n\n"
            "    Evaluation runs on human labels. Both annotators finish, then:\n"
            "      python merge_labels.py --a data/gold_labels_<a>.csv "
            "--b data/gold_labels_<b>.csv\n"
        )

    text_by_id, source_by_id = {}, {}
    for path in (SYNTHETIC, OSHA):
        if not path.exists():
            raise SystemExit(f"[!] {path} not found.")
        for row in read_csv(path):
            rid = str(row["report_id"]).strip()
            text_by_id[rid] = (row.get("text") or row.get("report_text") or "").strip()
            source_by_id[rid] = (row.get("source") or "osha").strip()

    rows, orphans = [], 0
    for row in read_csv(GOLD):
        rid = str(row["report_id"]).strip()
        if rid not in text_by_id:
            orphans += 1
            continue
        rows.append(
            {
                "report_id": rid,
                "text": text_by_id[rid],
                "source": source_by_id[rid],
                "is_sif_precursor": str(row["is_sif_precursor"]).strip().upper() == "TRUE",
                "severity": int(row["severity"]),
            }
        )

    if orphans:
        print(f"  [!] {orphans} gold labels had no matching report text and were dropped.")
    if not rows:
        raise SystemExit("[!] No gold labels matched any report text. Check report_id values.")
    return rows


# ---------------------------------------------------------------------------
# 2. The split, fixed once and recorded
# ---------------------------------------------------------------------------
# The held-out set is opened exactly once, at the end. That is a discipline, not
# something the code can enforce - but recording the split makes it auditable,
# and re-running cannot quietly reshuffle it into a friendlier partition.


def get_split(synthetic_ids):
    if SPLIT_FILE.exists():
        split = json.loads(SPLIT_FILE.read_text(encoding="utf-8"))
        known = set(split["dev"]) | set(split["held_out"])
        if set(synthetic_ids) != known:
            raise SystemExit(
                f"\n[!] {SPLIT_FILE.name} was made for a different set of report ids.\n"
                "    Delete it to regenerate - but be aware that reshuffling the split\n"
                "    after seeing results is how a held-out set stops meaning anything.\n"
            )
        return split

    ids = sorted(synthetic_ids, key=int)
    random.Random(SEED).shuffle(ids)
    split = {
        "seed": SEED,
        "dev": sorted(ids[:DEV_SIZE], key=int),
        "held_out": sorted(ids[DEV_SIZE:], key=int),
        "note": "Fixed at first run. Dev is for prompt tuning; held_out is opened once.",
    }
    SPLIT_FILE.write_text(json.dumps(split, indent=2), encoding="utf-8")
    print(f"  Split created and recorded in {SPLIT_FILE.name} "
          f"({len(split['dev'])} dev / {len(split['held_out'])} held out).")
    return split


# ---------------------------------------------------------------------------
# 3. Metrics
# ---------------------------------------------------------------------------


def metrics(y_true, y_pred, y_score=None):
    """F1 and PR-AUC. Deliberately no accuracy - see the module docstring."""
    from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

    out = {
        "n": len(y_true),
        "positives": sum(y_true),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "pr_auc": None,
    }
    if y_score is not None and len(set(y_true)) > 1:
        out["pr_auc"] = average_precision_score(y_true, y_score)
    return out


def severity_mae(pairs):
    """Mean absolute error on precursor cases only, per TECH_STACK."""
    if not pairs:
        return None
    return sum(abs(a - b) for a, b in pairs) / len(pairs)


def agreement_ceiling(path_a, path_b):
    """Raw agreement and Cohen's kappa on is_sif_precursor. This is the ceiling."""
    from sklearn.metrics import cohen_kappa_score

    a = {r["report_id"]: r for r in read_csv(path_a)}
    b = {r["report_id"]: r for r in read_csv(path_b)}
    shared = [k for k in a if k in b and (a[k].get("hazard_assessment") or "").strip()
              and (b[k].get("hazard_assessment") or "").strip()]
    if not shared:
        return None

    ya = [str(a[k]["is_sif_precursor"]).strip().upper() == "TRUE" for k in shared]
    yb = [str(b[k]["is_sif_precursor"]).strip().upper() == "TRUE" for k in shared]
    raw = sum(x == y for x, y in zip(ya, yb)) / len(shared)
    kappa = cohen_kappa_score(ya, yb) if len(set(ya + yb)) > 1 else float("nan")

    per_gate = {}
    for col in ("hazard_assessment", "lsr_rule", "control_status", "severity"):
        per_gate[col] = sum(
            (a[k].get(col) or "").strip() == (b[k].get(col) or "").strip() for k in shared
        ) / len(shared)

    return {"n": len(shared), "raw": raw, "kappa": kappa, "per_gate": per_gate}


# ---------------------------------------------------------------------------
# 4. Predictors
# ---------------------------------------------------------------------------


BASELINE_SPLIT_RECORD = ROOT / "backend" / "app" / "baseline_train_ids.json"


def warn_if_baseline_leaks(test_ids):
    """The baseline must not be scored on reports it was trained on.

    train_baseline.py currently makes its OWN train_test_split over all 180 reports,
    with no knowledge of eval/split.json. So unless it is changed, roughly 80% of the
    reports scored here were in its training set — which inflates the baseline and
    therefore SHRINKS the baseline-vs-LLM gap, the team's stated strongest
    differentiator. It is also the first thing an ML judge probes.

    The fix belongs in train_baseline.py: read eval/split.json, train on `held_out`
    minus whatever is being scored, and write the ids it actually trained on to
    baseline_train_ids.json. Until that exists, say so loudly rather than quietly
    reporting a contaminated number.
    """
    if not BASELINE_SPLIT_RECORD.exists():
        print("  [!] LEAKAGE RISK — the baseline's training ids are unknown.")
        print("      train_baseline.py splits independently of eval/split.json, so the")
        print("      reports scored below were probably in its training set. That inflates")
        print("      the baseline and understates the gap to the LLM.")
        print("      Fix: have train_baseline.py read eval/split.json and record the ids it")
        print("      trained on. Do not quote this row until then.\n")
        return

    trained = set(json.loads(BASELINE_SPLIT_RECORD.read_text(encoding="utf-8")))
    overlap = trained & set(test_ids)
    if overlap:
        print(f"  [!] LEAKAGE — {len(overlap)}/{len(test_ids)} scored reports were in the")
        print("      baseline's training set. This row is not a fair comparison.\n")
    else:
        print("  Baseline train/test separation verified against eval/split.json.\n")


def predict_baseline(rows):
    warn_if_baseline_leaks([r["report_id"] for r in rows])
    try:
        from app import classifier_base
    except Exception as exc:  # noqa: BLE001
        print(f"  [!] Baseline unavailable ({type(exc).__name__}): {exc}")
        print("      Run `python train_baseline.py` first.\n")
        return None

    preds, scores, severities = [], [], []
    for row in rows:
        result = classifier_base.classify(row["text"])
        result = result if isinstance(result, dict) else result.model_dump()
        preds.append(bool(result["is_sif_precursor"]))
        scores.append(float(result.get("confidence", 0.5)))
        severities.append(int(result["severity"]))
    return preds, scores, severities


def predict_llm(rows):
    """Goes through classifier.classify, so the SQLite cache makes re-runs free.

    That is the point of the cache: an eval you cannot reproduce without paying
    for it again is an eval nobody re-runs after changing something.
    """
    try:
        from app import classifier, classifier_llm

        classifier.register_primary(classifier_llm.classify)
    except Exception as exc:  # noqa: BLE001
        print(f"  [!] LLM classifier unavailable ({type(exc).__name__}): {exc}")
        print("      Check GROQ_API_KEY.\n")
        return None

    preds, scores, severities, fallbacks = [], [], [], 0
    for i, row in enumerate(rows, start=1):
        outcome = classifier.classify(row["text"])
        preds.append(outcome.result.is_sif_precursor)
        scores.append(outcome.result.confidence)
        severities.append(outcome.result.severity)
        fallbacks += int(outcome.is_fallback)
        if i % 25 == 0:
            print(f"      classified {i}/{len(rows)}")

    if fallbacks:
        print(f"  [!] {fallbacks}/{len(rows)} answers came from the FALLBACK, not the LLM.")
        print("      Those are baseline answers wearing the LLM's label. Fix before quoting.\n")
    return preds, scores, severities


# ---------------------------------------------------------------------------
# 5. Reporting
# ---------------------------------------------------------------------------


def row_line(name, m):
    if m is None:
        return f"  {name:<22} {'unavailable':>52}"
    pr = f"{m['pr_auc']:.3f}" if m["pr_auc"] is not None else "  -  "
    return (f"  {name:<22} {m['f1']:>8.3f} {pr:>10} "
            f"{m['precision']:>11.3f} {m['recall']:>9.3f} {m['n']:>7}")


def header(title):
    print(f"\n{title}")
    print("  " + "-" * 70)
    print(f"  {'':<22} {'F1':>8} {'PR-AUC':>10} {'precision':>11} {'recall':>9} {'n':>7}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-llm", action="store_true", help="baseline only, no API calls")
    parser.add_argument("--open-held-out", action="store_true",
                        help="score the held-out split. Do this ONCE, at the end")
    parser.add_argument("--annotators", nargs=2, metavar=("A", "B"),
                        help="the two annotator CSVs, for the agreement ceiling")
    args = parser.parse_args()

    print("=" * 72)
    print("  SIF PRECURSOR DETECTION — EVALUATION")
    print("=" * 72)

    rows = load_dataset()
    synthetic = [r for r in rows if r["source"] == "synthetic"]
    osha = [r for r in rows if r["source"] == "osha"]
    print(f"\n  Gold labels: {len(rows)}  ({len(synthetic)} synthetic, {len(osha)} OSHA)")

    positives = sum(r["is_sif_precursor"] for r in synthetic)
    if synthetic:
        rate = positives / len(synthetic)
        flag = "" if 0.20 <= rate <= 0.25 else "   [!] outside the plan's 20-25% band"
        print(f"  Positive class (synthetic): {positives}/{len(synthetic)} = {rate:.1%}{flag}")

    # --- the ceiling, first ---
    if args.annotators:
        ceiling = agreement_ceiling(*args.annotators)
        if ceiling:
            print("\n  THE CEILING — two annotators, independent, same written rubric")
            print("  " + "-" * 70)
            print(f"  Raw agreement   {ceiling['raw']:.1%}   on {ceiling['n']} reports")
            print(f"  Cohen's kappa   {ceiling['kappa']:.3f}")
            print("  Nothing scored against these labels can honestly claim to be more")
            print("  consistent than the humans who made them.")
            print("\n  Per-field agreement (which gate splits):")
            for col, val in ceiling["per_gate"].items():
                print(f"    {col:<22} {val:.1%}")
            if ceiling["raw"] < 0.70:
                print("\n  [!] Below 70%. Rubric section 10: revise the splitting gate and")
                print("      re-label only the reports that turned on it.")

    split = get_split([r["report_id"] for r in synthetic]) if synthetic else None
    if split:
        chosen = "held_out" if args.open_held_out else "dev"
        keep = set(split[chosen])
        test = [r for r in synthetic if r["report_id"] in keep]
        label = "HELD-OUT" if args.open_held_out else "DEV (tuning split)"
        if not args.open_held_out:
            print("\n  Scoring the DEV split. The held-out set stays closed until the final")
            print("  run — pass --open-held-out then, once.")
    else:
        test, label = [], "none"

    # --- Table 1: synthetic, baseline vs LLM ---
    if test:
        y_true = [r["is_sif_precursor"] for r in test]
        gold_sev = [r["severity"] for r in test]

        header(f"  TABLE 1 — Synthetic {label} split  (the fair fight)")
        base = predict_baseline(test)
        if base:
            print(row_line("TF-IDF baseline", metrics(y_true, base[0], base[1])))

        llm = None if args.no_llm else predict_llm(test)
        if llm:
            print(row_line("LLM classifier", metrics(y_true, llm[0], llm[1])))

            pairs = [(g, p) for g, p, t in zip(gold_sev, llm[2], y_true) if t]
            mae = severity_mae(pairs)
            if mae is not None:
                print(f"\n  Severity MAE (LLM, precursor cases only): {mae:.2f}  "
                      f"on {len(pairs)} reports")

    # --- Table 2: OSHA, LLM only ---
    if osha and not args.no_llm:
        header("  TABLE 2 — OSHA set, LLM only  (generalisation check)")
        print("  Real writing nobody on the team produced. The baseline is trained on")
        print("  synthetic reports, so scoring it here would measure domain transfer")
        print("  rather than model quality — an unfair fight we do not stage.")
        print()
        llm_osha = predict_llm(osha)
        if llm_osha:
            y_true = [r["is_sif_precursor"] for r in osha]
            print(row_line("LLM classifier", metrics(y_true, llm_osha[0], llm_osha[1])))

    print("\n" + "=" * 72)
    print("  Accuracy is deliberately absent. At ~22% positives, answering 'no' to")
    print("  everything scores 78%. Report F1 and PR-AUC, and quote the ceiling.")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
