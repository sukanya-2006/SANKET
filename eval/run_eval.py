"""
run_eval.py — the evaluation table. Artifact #1 of the three that matter most.

    python eval/run_eval.py
    python eval/run_eval.py --no-llm          # baseline only, no API calls
    python eval/run_eval.py --folds 10        # more folds, tighter estimate

OWNERSHIP: Member 3 owns evaluation per the master plan. This was written by
Member 1/4 while labelling was the bottleneck, so it would be ready the hour
gold_labels.csv lands rather than started then. M3 should review and take it
over - particularly the split policy in section 2, which is a judgement call
about how honest we are being with ourselves.

------------------------------------------------------------------------------
WHAT THIS PRINTS, AND WHY IT IS SHAPED THIS WAY

Two tables and one line. Never a single merged table.

  Table 1  Synthetic: baseline vs LLM, 5-fold cross-validation.
           The fair, apples-to-apples fight. Every report in the pool is scored
           exactly once, as a member of the one fold its model did not train on,
           and the reported figure is the mean across folds with its spread.
           A single split of this size would swing several F1 points on one
           flipped prediction; averaging five folds does not.

           The pool is the 120 held-out reports. The 30 dev reports are excluded
           from scoring entirely, because the LLM prompt was tuned on them -
           scoring them would be marking the model on its own worked examples.

  Table 2  OSHA set: LLM only.
           A generalisation check on real writing nobody on the team produced.
           The baseline is trained on synthetic reports, so testing it here
           would measure domain transfer rather than model quality - an unfair
           fight we would win for the wrong reason. We do not stage it.

  Line     Severity MAE on precursor cases, against adjudicated human severity.
           Being wrong by one level and by three are different mistakes; a
           classification metric would treat them identically.

  Round 2  Annotator agreement % and Cohen's kappa — not a ceiling.
           Round two was NOT run independently — the annotators worked
           differently the second time. It is evidence that the v2.1 -> v2.2
           rubric revision helped; it is not a ceiling, and not a bound on
           anything scored against these labels. The independent number is
           round one: 52.2% agreement, Cohen's kappa 0.083.
           prepare_independent_recheck.py samples 40 reports for a fresh
           independent re-label, which would yield a quotable kappa.

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


def canonical_synthetic_ids():
    """Every synthetic report id, from the source file.

    The split is a property of the DATASET, not of labelling progress. Building it from
    gold_labels.csv instead would make it move: reports held back for tiebreak are absent
    from the gold file, so the partition would change every time an adjudication landed —
    and a held-out set that moves is not a held-out set.
    """
    return [str(r["report_id"]).strip() for r in read_csv(SYNTHETIC)]


def get_split():
    ids_now = set(canonical_synthetic_ids())

    if SPLIT_FILE.exists():
        split = json.loads(SPLIT_FILE.read_text(encoding="utf-8"))
        known = set(split["dev"]) | set(split["held_out"])
        if ids_now != known:
            missing, extra = known - ids_now, ids_now - known
            raise SystemExit(
                f"\n[!] {SPLIT_FILE.name} does not match the synthetic report set.\n"
                f"    {len(missing)} id(s) in the split are no longer in the dataset;\n"
                f"    {len(extra)} new id(s) are not in the split.\n"
                "    That means the reports themselves changed, which is a real problem —\n"
                "    it is not caused by labelling progress or tiebreaks.\n"
                "    Delete it to regenerate, but reshuffling after seeing results is how a\n"
                "    held-out set stops meaning anything.\n"
            )
        return split

    ids = sorted(ids_now, key=int)
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


def annotator_agreement(path_a, path_b):
    """Raw agreement and Cohen's kappa on is_sif_precursor.

    Round two — not independent, not a ceiling. The annotators worked differently the
    second time, so this measures whether the v2.2 severity gate is followable, not how
    consistent two independent humans are. Nothing here bounds a model's score.
    """
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


def cross_validate_baseline(rows, n_folds):
    """Fit the baseline inside each fold. Never uses the shipped model.

    backend/app/baseline_model.joblib is trained on every label so the live fallback is
    as strong as possible. Scoring that model here would be marking it on its own
    training data. So the pipeline is refitted per fold instead, using the same builder
    train_baseline.py ships, so the evaluated model and the shipped model cannot drift
    apart in their hyperparameters.
    """
    try:
        import numpy as np
        from sklearn.model_selection import StratifiedKFold

        sys.path.insert(0, str(ROOT))
        from train_baseline import build_pipeline
    except Exception as exc:  # noqa: BLE001
        print(f"  [!] Baseline unavailable ({type(exc).__name__}): {exc}\n")
        return None

    X = np.array([r["text"] for r in rows])
    y = np.array([r["is_sif_precursor"] for r in rows])

    if len(set(y)) < 2:
        print("  [!] Only one class present; cross-validation is meaningless here.\n")
        return None

    folds = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=SEED)
    scores = []
    for train_idx, test_idx in folds.split(X, y):
        pipeline = build_pipeline()
        pipeline.fit(X[train_idx], y[train_idx])
        y_pred = pipeline.predict(X[test_idx])
        y_score = pipeline.predict_proba(X[test_idx])[:, 1]
        scores.append(metrics(list(y[test_idx]), list(y_pred), list(y_score)))
    return scores


def cross_validate_llm(rows, n_folds):
    """Score the LLM over the same folds.

    The LLM is not refitted - it has no training step - so its predictions are
    fold-independent. Scoring it fold-wise anyway is what makes the two rows
    comparable: both report a mean and a spread over the same partitions, rather
    than one exact figure beside one averaged one.
    """
    import numpy as np
    from sklearn.model_selection import StratifiedKFold

    predicted = predict_llm(rows)
    if predicted is None:
        return None, None
    preds, confidences, severities = predicted

    y = np.array([r["is_sif_precursor"] for r in rows])
    preds, confidences = np.array(preds), np.array(confidences)

    folds = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=SEED)
    scores = [
        metrics(list(y[idx]), list(preds[idx]), list(confidences[idx]))
        for _, idx in folds.split(np.zeros(len(y)), y)
    ]
    return scores, severities


def summarise(scores):
    """Mean and standard deviation across folds."""
    import statistics

    def agg(key):
        vals = [s[key] for s in scores if s[key] is not None]
        if not vals:
            return None, None
        return statistics.mean(vals), (statistics.stdev(vals) if len(vals) > 1 else 0.0)

    f1_m, f1_sd = agg("f1")
    pr_m, pr_sd = agg("pr_auc")
    p_m, _ = agg("precision")
    r_m, _ = agg("recall")
    return {"f1": f1_m, "f1_sd": f1_sd, "pr_auc": pr_m, "pr_auc_sd": pr_sd,
            "precision": p_m, "recall": r_m, "n": sum(s["n"] for s in scores)}


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


def cv_row(name, agg):
    if agg is None:
        return f"  {name:<20} {'unavailable':>50}"
    f1 = f"{agg['f1']:.3f} ± {agg['f1_sd']:.3f}"
    pr = f"{agg['pr_auc']:.3f} ± {agg['pr_auc_sd']:.3f}" if agg["pr_auc"] is not None else "-"
    return (f"  {name:<20} {f1:>15} {pr:>17} "
            f"{agg['precision']:>10.3f} {agg['recall']:>8.3f} {agg['n']:>6}")


def cv_header(title):
    print(f"\n{title}")
    print("  " + "-" * 76)
    print(f"  {'':<20} {'F1 (mean ± sd)':>15} {'PR-AUC (mean ± sd)':>17} "
          f"{'prec':>10} {'recall':>8} {'n':>6}")


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
    parser.add_argument("--folds", type=int, default=5,
                        help="cross-validation folds over the scoring pool (default 5)")
    parser.add_argument("--annotators", nargs=2, metavar=("A", "B"),
                        help="the two annotator CSVs, for the round-two agreement check")
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

    # --- annotator agreement, first ---
    if args.annotators:
        agreement = annotator_agreement(*args.annotators)
        if agreement:
            print("\n  ANNOTATOR AGREEMENT — round two: not independent, not a ceiling")
            print("  " + "-" * 70)
            print(f"  Raw agreement   {agreement['raw']:.1%}   on {agreement['n']} reports")
            print(f"  Cohen's kappa   {agreement['kappa']:.3f}")
            print("  Round two was not run independently — the annotators worked")
            print("  differently the second time. Read this as evidence the v2.2 rubric")
            print("  revision helped, not as a bound on anything scored against these")
            print("  labels. The independent round one agreed 52.2%, kappa 0.083.")
            print("\n  Per-field agreement (which gate splits):")
            for col, val in agreement["per_gate"].items():
                print(f"    {col:<22} {val:.1%}")
            if agreement["raw"] < 0.70:
                print("\n  [!] Below 70%. Rubric section 10: revise the splitting gate and")
                print("      re-label only the reports that turned on it.")

    split = get_split() if synthetic else None
    test = []
    if split:
        pool = set(split["held_out"])
        test = [r for r in synthetic if r["report_id"] in pool]

        # Reports still awaiting tiebreak have no gold label yet, so they are not scored.
        # Say how many, rather than quietly reporting a metric over a smaller set than
        # the reader assumes.
        missing = len(pool) - len(test)
        if missing:
            print(f"\n  [!] {missing} of the {len(pool)} scoring-pool reports have no gold")
            print("      label yet (awaiting tiebreak). Scoring the remainder.")
        print(f"\n  Scoring pool: {len(test)} reports. The {len(split['dev'])} dev reports are")
        print("  excluded — the LLM prompt was tuned on them.")

    # --- Table 1: synthetic, baseline vs LLM, cross-validated ---
    if test:
        if len(test) < args.folds * 2:
            print(f"\n  [!] Only {len(test)} reports; {args.folds} folds is too many. Skipping.")
        else:
            cv_header(f"  TABLE 1 — Synthetic, {args.folds}-fold CV  (the fair fight)")

            base_scores = cross_validate_baseline(test, args.folds)
            if base_scores:
                print(cv_row("TF-IDF baseline", summarise(base_scores)))

            if not args.no_llm:
                llm_scores, severities = cross_validate_llm(test, args.folds)
                if llm_scores:
                    print(cv_row("LLM classifier", summarise(llm_scores)))

                    y_true = [r["is_sif_precursor"] for r in test]
                    gold_sev = [r["severity"] for r in test]
                    pairs = [(g, p) for g, p, t in zip(gold_sev, severities, y_true) if t]
                    mae = severity_mae(pairs)
                    if mae is not None:
                        print(f"\n  Severity MAE (LLM, precursor cases only): {mae:.2f}  "
                              f"on {len(pairs)} reports")

    # --- Table 2: OSHA, LLM only ---
    if osha and not args.no_llm:
        print("\n  TABLE 2 — OSHA set, LLM only  (generalisation check)")
        print("  " + "-" * 76)
        print("  Real writing nobody on the team produced. The baseline is trained on")
        print("  synthetic reports, so scoring it here would measure domain transfer")
        print("  rather than model quality — an unfair fight we do not stage.")
        print()
        llm_osha = predict_llm(osha)
        if llm_osha:
            y_true = [r["is_sif_precursor"] for r in osha]
            m = metrics(y_true, llm_osha[0], llm_osha[1])
            pr = f"{m['pr_auc']:.3f}" if m["pr_auc"] is not None else "-"
            print(f"  {'LLM classifier':<20} F1 {m['f1']:.3f}   PR-AUC {pr}   "
                  f"prec {m['precision']:.3f}   recall {m['recall']:.3f}   n {m['n']}")

    print("\n" + "=" * 72)
    print("  Accuracy is deliberately absent. At ~22% positives, answering 'no' to")
    print("  everything scores 78%. Report F1 and PR-AUC. There is no human ceiling")
    print("  to quote: the only independent round agreed 52.2%, kappa 0.083.")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
