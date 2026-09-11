"""
score_stored_predictions.py

Score the predictions already sitting in Supabase against the human gold labels.

    python score_stored_predictions.py
    python score_stored_predictions.py --model-version <exact version string>
    python score_stored_predictions.py --include-dev   # debugging only, never quotable

WHY THIS EXISTS

`eval/run_eval.py` calls the model. On Groq's free tier that costs ~3,150 tokens a report
against a 200,000-token daily cap, so a full cross-validated LLM run is roughly two days of
budget and cannot be done on demand before a deadline.

But every report has already been classified, and `predictions` keeps every judgement. Scoring
what is stored costs nothing and answers the question that actually matters before a
submission: what do the numbers look like under the prompt we ship TODAY, rather than under a
prompt from a week ago.

WHAT THIS IS, AND WHAT IT IS NOT

This is an honest held-out score for the LLM. The model never saw the gold labels, so there is
no leakage and no cross-validation needed - prompting is not fitting. The dev reports listed in
`eval/split.json` are excluded, because the prompt WAS tuned on those: scoring them is marking
the model on its own worked examples. `eval/run_eval.py` has always excluded them; this script
did not, and every figure it printed before that fix was inflated by however many of them the
pool happened to contain.

It is NOT a fair score for the TF-IDF baseline, and this script does not pretend to give one.
`train_baseline.py` deliberately refits on every label so the shipped fallback is as strong as
possible, which means every report it would be scored on was in its training set. Use
`eval/run_eval.py --skip-llm` for the baseline: it refits inside cross-validation folds, which
is the only way that number means anything.

Severity and gate-level agreement are reported alongside the headline, because a single F1
hides which gate is doing the damage - and on this project it has always been Gate 3.
"""

import argparse
import csv
import io
import json
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

GOLD_PATH = "data/gold_labels.csv"
SPLIT_PATH = "eval/split.json"

LATEST_FOR_VERSION = """
SELECT DISTINCT ON (p.report_id)
       p.report_id, p.hazard_assessment, p.lsr_rule, p.control_status,
       p.severity, p.is_sif_precursor, p.is_fallback, p.confidence,
       r.source
FROM predictions p
JOIN reports r ON r.report_id = p.report_id
WHERE p.model_version = %(model_version)s
ORDER BY p.report_id, p.created_at DESC
"""

VERSIONS = """
SELECT model_version, count(DISTINCT report_id) AS n, max(created_at) AS newest
FROM predictions GROUP BY 1 ORDER BY 3 DESC
"""


def prf(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def load_gold():
    with open(GOLD_PATH, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    gold = {}
    for r in rows:
        try:
            severity = int(float(r["severity"]))
        except (TypeError, ValueError):
            continue
        hazard = (r["hazard_assessment"] or "").strip().lower()
        control = (r.get("control_status") or "").strip().lower() or None
        if hazard != "yes":
            control = None
        gold[str(r["report_id"]).strip()] = {
            "hazard_assessment": hazard,
            "lsr_rule": (r["lsr_rule"] or "").strip().lower().replace(" ", "_"),
            "control_status": control,
            "severity": severity,
            # Derived, never read from the column. Rubric sections 2 and 6.
            "is_sif_precursor": hazard == "yes"
            and control in ("absent", "failed")
            and severity >= 4,
        }
    return gold


def load_dev_ids():
    """The prompt-tuning ids recorded in eval/split.json.

    Refusing to run without the file is deliberate: a missing split must not silently
    degrade into scoring the dev set, which is the exact failure this guards against.
    """
    if not os.path.exists(SPLIT_PATH):
        sys.exit("[!] %s not found - cannot tell which reports the prompt was tuned on.\n"
                 "    Run eval/run_eval.py once to record the split." % SPLIT_PATH)
    with open(SPLIT_PATH, encoding="utf-8") as fh:
        return {str(i).strip() for i in json.load(fh)["dev"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-version", default=None,
                    help="defaults to the version the API currently ships")
    ap.add_argument("--include-dev", action="store_true",
                    help="debugging only: keep the prompt-tuning reports in the pool")
    args = ap.parse_args()

    if not db.is_live():
        sys.exit("[!] Database not connected. Check backend/.env.")

    if args.model_version:
        version = args.model_version
    else:
        from app import classifier, classifier_llm

        classifier.register_primary(classifier_llm.classify)
        version = classifier.active_versions()["primary"]

    gold = load_gold()
    preds = {r["report_id"]: r for r in db.query(LATEST_FOR_VERSION,
                                                 {"model_version": version})}

    print("=" * 78)
    print("  STORED PREDICTIONS vs HUMAN GOLD LABELS")
    print("=" * 78)
    print("\n  model_version : %s" % version)
    print("  gold labels   : %d" % len(gold))
    print("  predictions   : %d" % len(preds))

    if not preds:
        print("\n  [!] Nothing stored under that version. What is in the table:\n")
        for r in db.query(VERSIONS):
            print("    %-50s %4d reports  %s"
                  % (r["model_version"][:50], r["n"], r["newest"].strftime("%Y-%m-%d")))
        return

    shared = sorted(set(gold) & set(preds), key=lambda x: int(x) if x.isdigit() else 0)
    print("  scored on     : %d reports both labelled and classified" % len(shared))

    dev = load_dev_ids()
    in_pool = [i for i in shared if i in dev]
    if args.include_dev:
        print("\n  [!] --include-dev: %d prompt-tuning reports LEFT IN the pool of %d."
              % (len(in_pool), len(shared)))
        print("      The prompt was written against those reports, so anything printed below")
        print("      is the model being marked on its own worked examples. DO NOT QUOTE IT -")
        print("      it is not comparable to eval/run_eval.py and not a held-out number.")
    else:
        kept = [i for i in shared if i not in dev]
        print("  dev excluded  : pool %d -> %d  (%d prompt-tuning reports, %s)"
              % (len(shared), len(kept), len(in_pool), SPLIT_PATH))
        shared = kept

    fallbacks = [i for i in shared if preds[i]["is_fallback"]]
    if fallbacks:
        # A fallback is the baseline answering, not the model. Scoring it as an LLM
        # prediction inflates or deflates the LLM's number with someone else's answer.
        print("\n  [!] %d of these are FALLBACK rows (the baseline answered, not the model)."
              % len(fallbacks))
        print("      Excluding them. Re-run batch_classify.py to fill them properly.")
        shared = [i for i in shared if not preds[i]["is_fallback"]]
        print("      Scoring %d genuine model answers." % len(shared))

    if not shared:
        print("\n  [!] Nothing left to score.")
        return

    synthetic = [i for i in shared if preds[i]["source"] == "synthetic"]
    osha = [i for i in shared if preds[i]["source"] == "osha"]

    for label, ids in (("SYNTHETIC", synthetic), ("OSHA (real narratives)", osha)):
        if not ids:
            continue
        tp = sum(1 for i in ids if preds[i]["is_sif_precursor"] and gold[i]["is_sif_precursor"])
        fp = sum(1 for i in ids if preds[i]["is_sif_precursor"] and not gold[i]["is_sif_precursor"])
        fn = sum(1 for i in ids if not preds[i]["is_sif_precursor"] and gold[i]["is_sif_precursor"])
        tn = len(ids) - tp - fp - fn
        precision, recall, f1 = prf(tp, fp, fn)

        print("\n  " + "-" * 74)
        print("  %s  (n=%d)" % (label, len(ids)))
        print("  " + "-" * 74)
        print("    TP %-4d FP %-4d FN %-4d TN %-4d" % (tp, fp, fn, tn))
        print("    precision %.3f   recall %.3f   F1 %.3f" % (precision, recall, f1))
        print("    gold precursor rate  %.1f%%   model precursor rate  %.1f%%"
              % (100 * sum(gold[i]["is_sif_precursor"] for i in ids) / len(ids),
                 100 * sum(preds[i]["is_sif_precursor"] for i in ids) / len(ids)))

        if len(ids) < 40:
            print("    [!] n=%d is too small to conclude from in either direction." % len(ids))

        # Which gate is doing the damage. A single F1 hides this entirely.
        g1 = sum(1 for i in ids if preds[i]["hazard_assessment"] == gold[i]["hazard_assessment"])
        g2ids = [i for i in ids if gold[i]["hazard_assessment"] == "yes"
                 and preds[i]["hazard_assessment"] == "yes"]
        g2 = sum(1 for i in g2ids if preds[i]["control_status"] == gold[i]["control_status"])
        g3 = sum(1 for i in ids if preds[i]["severity"] == gold[i]["severity"])
        g3near = sum(1 for i in ids if abs(preds[i]["severity"] - gold[i]["severity"]) <= 1)
        rule = sum(1 for i in ids if preds[i]["lsr_rule"] == gold[i]["lsr_rule"])

        print("\n    per-gate agreement with the humans")
        print("      gate 1 hazard        %3d/%-3d  %5.1f%%" % (g1, len(ids), 100 * g1 / len(ids)))
        print("      lsr_rule             %3d/%-3d  %5.1f%%" % (rule, len(ids), 100 * rule / len(ids)))
        if g2ids:
            print("      gate 2 control       %3d/%-3d  %5.1f%%   (where both said hazard=yes)"
                  % (g2, len(g2ids), 100 * g2 / len(g2ids)))
        print("      gate 3 severity      %3d/%-3d  %5.1f%%" % (g3, len(ids), 100 * g3 / len(ids)))
        print("      gate 3 within 1 band %3d/%-3d  %5.1f%%" % (g3near, len(ids), 100 * g3near / len(ids)))

        misses = [i for i in ids if gold[i]["is_sif_precursor"] and not preds[i]["is_sif_precursor"]]
        if misses:
            by_gate = Counter()
            for i in misses:
                if preds[i]["hazard_assessment"] != "yes":
                    by_gate["gate 1 - called it no hazard"] += 1
                elif preds[i]["control_status"] not in ("absent", "failed"):
                    by_gate["gate 2 - called the control present/unclear"] += 1
                else:
                    by_gate["gate 3 - scored severity below 4"] += 1
            print("\n    why it missed %d real precursors" % len(misses))
            for gate, n in by_gate.most_common():
                print("      %-46s %3d  (%.0f%%)" % (gate, n, 100 * n / len(misses)))

        shift = Counter(preds[i]["severity"] - gold[i]["severity"] for i in ids)
        mean = sum(preds[i]["severity"] - gold[i]["severity"] for i in ids) / len(ids)
        print("\n    severity shift (model minus human): "
              + "  ".join("%+d:%d" % (d, shift[d]) for d in sorted(shift)))
        print("      mean %+.2f" % mean)

    print("\n  " + "-" * 74)
    print("  This is a fair held-out score for the LLM - it never saw the gold labels, and")
    print("  prompting is not fitting, so there is nothing to cross-validate away.")
    print("  It is NOT a fair score for the TF-IDF baseline, which is refit on every label.")
    print("  For that, run:  python eval/run_eval.py --skip-llm\n")


if __name__ == "__main__":
    main()
