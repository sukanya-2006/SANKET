"""
reclassify_all.py

Forces a fresh classification of EVERY report in the database, regardless
of whether a prediction already exists - unlike batch_classify.py, which
skips anything already classified. Use this when the classifier's logic
itself changed (like the Gate 3 severity prompt fix) and old predictions
need to be replaced, not just filled in for gaps.

Since predictions is append-only (per db.py's design - old rows are never
deleted, only superseded), this simply inserts a new, newer prediction for
every report. latest_predictions (the view aggregate.py and repository.py
both read from) automatically picks up the newest row per report_id, so
the old 74%-precursor-rate predictions become irrelevant without needing
to be deleted.

Usage (from project root):
    python reclassify_all.py

Cost note: this makes ~150-180 fresh Groq API calls. Same pacing/quota
considerations as batch_classify.py - budget several minutes and be
mindful of daily token limits.
"""

import sys
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / "backend" / ".env")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import db, classifier, classifier_llm  # noqa: E402

classifier.register_primary(classifier_llm.classify)

PACING_DELAY_SECONDS = 1.5

ALL_REPORTS = """
SELECT report_id, report_text FROM reports ORDER BY report_id
"""


def main():
    if not db.is_live():
        sys.exit("[!] Database not connected.")

    all_reports = db.query(ALL_REPORTS)
    print(f"Re-classifying all {len(all_reports)} reports with the updated "
          f"Gate 3 prompt (ignoring any existing predictions).\n")

    succeeded = 0
    failed = 0
    precursor_count = 0

    for i, report in enumerate(all_reports, start=1):
        report_id = report["report_id"]
        text = report["report_text"]

        try:
            # use_cache=False: the old cache entries were produced by the
            # PREVIOUS prompt version, so a cache hit here would silently
            # serve a stale, over-flagged answer instead of a fresh one.
            outcome = classifier.classify(text, use_cache=False)
            db.insert_prediction(
                report_id=report_id,
                result=outcome.result,
                model_version=outcome.model_version,
                is_fallback=outcome.is_fallback,
            )
            status = "FALLBACK" if outcome.is_fallback else "ok"
            precursor = outcome.result.is_sif_precursor
            precursor_count += int(precursor)
            print(f"  [{i}/{len(all_reports)}] report {report_id}: "
                  f"precursor={precursor} severity={outcome.result.severity} ({status})")
            succeeded += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(all_reports)}] report {report_id}: FAILED - "
                  f"{type(exc).__name__}: {exc}")
            failed += 1

        time.sleep(PACING_DELAY_SECONDS)

    print(f"\nDone. {succeeded} classified, {failed} failed.")
    if succeeded:
        print(f"New precursor rate: {precursor_count}/{succeeded} "
              f"({precursor_count / succeeded:.1%}) - target is 20-25%.")
    if failed:
        print("Re-run this script to retry the failed ones.")


if __name__ == "__main__":
    main()