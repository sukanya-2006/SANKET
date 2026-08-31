"""
reclassify_fallbacks.py

batch_classify.py skips any report_id that already has a prediction row -
including ones that only got a prediction because the primary classifier
timed out and fell back to the stub. Those are low-quality guesses, not
real answers, and need a real attempt - this script finds exactly those
reports and re-runs classification on them specifically.

Run this AFTER batch_classify.py finishes its first full pass, and after
raising LLM_TIMEOUT_SECONDS in backend/.env to reduce future timeouts.

Usage (from project root):
    python reclassify_fallbacks.py
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

PACING_DELAY_SECONDS = 2.0  # slightly longer than batch_classify.py's, since
                            # timeouts suggest we're pushing the rate limit

# latest_predictions is the view db.py's apply_schema() creates - it gives
# the most recent prediction per report_id, which is what we need here
# since predictions is append-only (never updated in place).
FALLBACK_REPORT_IDS = """
SELECT r.report_id, r.report_text
FROM reports r
JOIN latest_predictions l ON l.report_id = r.report_id
WHERE l.is_fallback = true
ORDER BY r.report_id
"""


def main():
    if not db.is_live():
        sys.exit("[!] Database not connected.")

    todo = db.query(FALLBACK_REPORT_IDS)
    print(f"{len(todo)} reports currently have a fallback (stub) prediction "
          f"and need a real re-attempt.\n")

    if not todo:
        print("Nothing to do - no fallback predictions found.")
        return

    succeeded = 0
    still_fallback = 0

    for i, report in enumerate(todo, start=1):
        report_id = report["report_id"]
        text = report["report_text"]

        try:
            outcome = classifier.classify(text, use_cache=False)  # bypass
            # cache - a cached fallback answer would just repeat the same
            # low-quality result instead of giving Groq a fresh attempt
            db.insert_prediction(
                report_id=report_id,
                result=outcome.result,
                model_version=outcome.model_version,
                is_fallback=outcome.is_fallback,
            )
            if outcome.is_fallback:
                print(f"  [{i}/{len(todo)}] report {report_id}: still timed out")
                still_fallback += 1
            else:
                print(f"  [{i}/{len(todo)}] report {report_id}: "
                      f"real classification succeeded "
                      f"(precursor={outcome.result.is_sif_precursor})")
                succeeded += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(todo)}] report {report_id}: FAILED - {exc}")

        time.sleep(PACING_DELAY_SECONDS)

    print(f"\nDone. {succeeded} now have real classifications, "
          f"{still_fallback} still fell back (re-run again if any remain).")


if __name__ == "__main__":
    main()