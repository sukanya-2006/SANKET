"""
reclassify_pending.py

Resumable version of reclassify_all.py. Only re-classifies reports whose
LATEST prediction is not already tagged with the current classifier
version (classifier_llm.classify.version) - so if you get rate-limited
partway through, switch to a fresh API key, or come back tomorrow after
the daily quota resets, running this again picks up exactly where you
left off instead of re-spending calls on reports already done under the
current prompt.

Usage (from project root):
    python reclassify_pending.py

To switch API keys mid-run: stop this script (Ctrl+C), set a new
GROQ_API_KEY (either in backend/.env or via $env:GROQ_API_KEY in the same
terminal), then run this script again.
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

# Reports whose latest prediction is NOT tagged with the current classifier
# version - covers reports never classified, ones stuck on an old prompt
# version, and ones currently sitting on a fallback answer, all in one query.
PENDING_REPORTS = """
SELECT r.report_id, r.report_text
FROM reports r
LEFT JOIN latest_predictions l ON l.report_id = r.report_id
WHERE l.report_id IS NULL OR l.model_version != %(current_version)s
ORDER BY r.report_id
"""


def main():
    if not db.is_live():
        sys.exit("[!] Database not connected.")

    current_version = classifier_llm.classify.version
    todo = db.query(PENDING_REPORTS, {"current_version": current_version})

    print(f"Current classifier version: {current_version}")
    print(f"{len(todo)} reports still need classification under this version.\n")

    if not todo:
        print("Nothing to do - every report is already classified under the "
              "current version.")
        return

    succeeded = 0
    failed = 0
    precursor_count = 0

    for i, report in enumerate(todo, start=1):
        report_id = report["report_id"]
        text = report["report_text"]

        try:
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
            print(f"  [{i}/{len(todo)}] report {report_id}: "
                  f"precursor={precursor} severity={outcome.result.severity} ({status})")
            succeeded += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(todo)}] report {report_id}: FAILED - "
                  f"{type(exc).__name__}: {exc}")
            failed += 1
            # Rate limit errors mean every subsequent call will fail too until
            # quota resets or the key changes - stop instead of burning through
            # the remaining list printing the same error over and over.
            if "rate_limit" in str(exc).lower() or "RateLimitError" in type(exc).__name__:
                print(f"\n[!] Rate limit hit. Stopping early - {len(todo) - i} reports "
                      f"still pending. Switch API keys or wait for reset, then re-run "
                      f"this script to resume.")
                break

        time.sleep(PACING_DELAY_SECONDS)

    print(f"\n{succeeded} classified this run, {failed} failed.")
    if succeeded:
        print(f"Precursor rate this run: {precursor_count}/{succeeded} "
              f"({precursor_count / succeeded:.1%})")


if __name__ == "__main__":
    main()