"""
batch_classify.py

Runs every report currently in the live Supabase `reports` table through
the real classifier (classifier_llm.py) and stores each result via
db.insert_prediction() - the same function the live /analyze endpoint uses
to persist results, so this produces data in exactly the same shape.

This is what makes the dashboard's /aggregate/* endpoints show real numbers
instead of empty/null values - right now reports exist but nothing has
classified them yet.

Usage (from project root):
    python batch_classify.py

Safe to re-run: skips any report_id that already has a prediction, so you
can stop and resume, or re-run after adding new reports without
re-classifying (and re-spending API calls on) everything.

Cost note: this makes one Groq API call per unclassified report. At ~1.5s
per call plus a pacing delay, expect this to take several minutes for the
full 180-report set. Free-tier rate limits apply - the pacing delay below
is deliberately conservative.
"""

import sys
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / "backend" / ".env")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import db, classifier, classifier_llm  # noqa: E402

# Register the real classifier the same way main.py does - batch_classify.py
# doesn't import main.py (that would also start the web server), so this
# registration has to happen here too.
classifier.register_primary(classifier_llm.classify)

PACING_DELAY_SECONDS = 1.5  # stay comfortably under Groq's free-tier rate limit

ALREADY_CLASSIFIED = """
SELECT DISTINCT report_id FROM predictions
"""

ALL_REPORTS = """
SELECT report_id, report_text FROM reports ORDER BY report_id
"""


def main():
    if not db.is_live():
        sys.exit("[!] Database not connected. Check backend/.env and /health first.")

    all_reports = db.query(ALL_REPORTS)
    already_done = {row["report_id"] for row in db.query(ALREADY_CLASSIFIED)}

    todo = [r for r in all_reports if r["report_id"] not in already_done]

    print(f"{len(all_reports)} reports total, {len(already_done)} already classified, "
          f"{len(todo)} remaining.\n")

    if not todo:
        print("Nothing to do - every report already has a prediction.")
        return

    succeeded = 0
    failed = 0

    for i, report in enumerate(todo, start=1):
        report_id = report["report_id"]
        text = report["report_text"]

        try:
            outcome = classifier.classify(text)
            db.insert_prediction(
                report_id=report_id,
                result=outcome.result,
                model_version=outcome.model_version,
                is_fallback=outcome.is_fallback,
            )
            status = "FALLBACK" if outcome.is_fallback else "ok"
            precursor = outcome.result.is_sif_precursor
            print(f"  [{i}/{len(todo)}] report {report_id}: "
                  f"precursor={precursor} severity={outcome.result.severity} "
                  f"({status})")
            succeeded += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(todo)}] report {report_id}: FAILED - "
                  f"{type(exc).__name__}: {exc}")
            failed += 1

        time.sleep(PACING_DELAY_SECONDS)

    print(f"\nDone. {succeeded} classified, {failed} failed.")
    if failed:
        print("Re-run this script to retry the failed ones - already-classified "
              "reports are skipped automatically.")


if __name__ == "__main__":
    main()