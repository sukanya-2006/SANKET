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
    python batch_classify.py --limit 20        # costed trial run
    python batch_classify.py --delay 5         # only if the key is not on the free tier

By default a baseline fallback is NOT stored. If the model cannot be reached, the
report is left unclassified for the next run rather than recorded with an answer the
model never gave.

Safe to re-run: skips any report_id that already has a prediction FROM THE
MODEL VERSION WE CURRENTLY SHIP, so you can stop and resume, or re-run after
adding new reports without re-spending API calls on everything.

Because the check is version-aware, this is also the script you run after a
prompt change: the version string moves, every report looks unclassified
again, and one pass refreshes the whole set. predictions is append-only, so
the old judgements stay on the record and latest_predictions picks up the new
ones automatically. That makes reclassify_all.py redundant.

Cost note: one Groq API call per unclassified report. The call itself takes
about 1.5s, but the free tier caps tokens per minute rather than requests and
this prompt is large, so the pacing delay - not the model - sets the runtime.
At the 25s default a full 180-report pass takes roughly 75 minutes. Run it and
leave it; it is resumable, so an interrupted run costs nothing but the reports
it had not reached.
"""

import argparse
import logging
import sys
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / "backend" / ".env")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import db, classifier, classifier_llm  # noqa: E402
from app.config import get_settings  # noqa: E402

# Register the real classifier the same way main.py does - batch_classify.py
# doesn't import main.py (that would also start the web server), so this
# registration has to happen here too.
classifier.register_primary(classifier_llm.classify)

# classifier.py logs WHY the primary failed and then returns a baseline answer, so
# without a handler the script prints "baseline answered" over and over and the reason
# goes nowhere. That is how a run wrote 111 stub rows against a client that could not
# call the model at all: the TypeError was logged on every single call and no one saw it.
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
# httpx logs a line per request at INFO, which buries everything else.
logging.getLogger("httpx").setLevel(logging.WARNING)

# Groq's free tier caps TOKENS per minute, not requests. The system prompt is around
# 3,000 tokens and the ceiling observed on this key is 8,000 TPM, which works out at
# roughly two calls a minute. The old 1.5s pacing issued forty.
#
# The failure mode is not an error. The rate limit raises, classifier.py catches it, the
# baseline stub answers, and the row is written with is_fallback=True - so a run at the
# wrong pace fills the table with stub predictions and reports itself as successful. One
# run did exactly that: ten real answers, then 111 stub rows.
#
# 25 seconds is one token-bucket refill. Override with --delay if the key has a higher
# tier; check x-ratelimit-limit-tokens on any response before lowering it.
DEFAULT_PACING_SECONDS = 25.0

# Per-report deadline for a batch run. Must exceed classifier_llm's retry budget
# (RETRY_BACKOFF_SECONDS, 30 + 45) or a rate-limited call is killed mid-backoff and can never
# recover. The API's own LLM_TIMEOUT_SECONDS stays where it is - see main().
BATCH_TIMEOUT_SECONDS = 120.0

# Version-aware on purpose. The original form was `SELECT DISTINCT report_id FROM
# predictions`, which skipped any report that had EVER been classified - so after a prompt
# change this script reported "nothing to do" while the database still held answers from the
# old prompt. The aggregation filters on the CURRENT model_version, so those stale rows made
# every /aggregate/* endpoint return zero rows, with no error anywhere to explain it.
#
# Asking "classified under the version we ship today?" makes one script correct in both
# situations: it fills gaps, and it refreshes everything after a prompt edit, while staying
# resumable if the run is interrupted or the Groq quota runs out mid-way.
ALREADY_CLASSIFIED = """
SELECT DISTINCT report_id FROM predictions WHERE model_version = %(model_version)s
"""

ALL_REPORTS = """
SELECT report_id, report_text FROM reports ORDER BY report_id
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delay", type=float, default=DEFAULT_PACING_SECONDS,
                    help="seconds between calls (default %(default)s, sized for the free tier)")
    ap.add_argument("--limit", type=int, default=None,
                    help="stop after this many reports; useful for a costed trial run")
    ap.add_argument("--allow-fallback", action="store_true",
                    help="store baseline answers too. Off by default - see below.")
    ap.add_argument("--timeout", type=float, default=BATCH_TIMEOUT_SECONDS,
                    help="per-report deadline in seconds (default %(default)s)")
    args = ap.parse_args()

    # A batch run has nobody waiting on it, so it should not inherit the API's deadline.
    #
    # LLM_TIMEOUT_SECONDS exists to stop a wedged call holding a live request - and a demo -
    # hostage, which is why it is 60s. But classifier_llm retries a rate-limited call with a
    # 30s then 45s backoff, and 75s of backoff under a 60s deadline means the wrapper kills
    # every rate-limited call mid-wait. The report can then never succeed however many times
    # it is retried.
    #
    # Here the honest trade is the opposite way round: wait long enough for the token bucket
    # to refill, because a slow report is better than an unclassified one. The live API keeps
    # its own shorter deadline.
    settings = get_settings()
    object.__setattr__(settings, "llm_timeout_seconds", args.timeout)

    if not db.is_live():
        sys.exit("[!] Database not connected. Check backend/.env and /health first.")

    model_version = classifier.active_versions()["primary"]

    all_reports = db.query(ALL_REPORTS)
    already_done = {
        row["report_id"]
        for row in db.query(ALREADY_CLASSIFIED, {"model_version": model_version})
    }

    todo = [r for r in all_reports if r["report_id"] not in already_done]

    print(f"Model version:  {model_version}")
    print(f"Prompt version: {get_settings().prompt_version}")
    print(f"{len(all_reports)} reports total, {len(already_done)} already classified "
          f"under this version, "
          f"{len(todo)} remaining.\n")

    if not todo:
        print("Nothing to do - every report already has a prediction under this version.")
        return

    if args.limit:
        todo = todo[:args.limit]
        print(f"--limit {args.limit}: classifying {len(todo)} of them this run.\n")

    eta = len(todo) * args.delay / 60
    print(f"Pacing {args.delay:g}s between calls, {args.timeout:g}s deadline per report - "
          f"about {eta:.0f} minutes. Safe to interrupt; re-running resumes.\n")

    succeeded = 0
    failed = 0
    skipped_fallback = 0
    consecutive_fallbacks = 0

    for i, report in enumerate(todo, start=1):
        report_id = report["report_id"]
        text = report["report_text"]

        try:
            # use_cache=False is load-bearing, not an optimisation.
            #
            # The cache is keyed on sha256(text + prompt_version) and returns the answer AND
            # the model_version that produced it. On a hit, this loop would store a prediction
            # stamped with the OLD model version - so a run meant to measure a new prompt
            # silently re-files old answers under the old name, and the new version looks like
            # it covered far fewer reports than the run reported storing.
            #
            # That happened: a 209-report pass reported 173 stored, of which only 74 were
            # actually the new version. The other 99 were cache replays.
            #
            # A batch run exists to produce predictions under the model we ship today. It must
            # call it.
            outcome = classifier.classify(text, use_cache=False)

            # A fallback is the baseline stub answering because the model could not be
            # reached. Storing it under a run meant to measure the model puts an answer
            # the model never gave into the table the dashboard and the eval both read,
            # and nothing downstream distinguishes it. Leaving the report unclassified is
            # recoverable - the next run picks it up. A stub row looks like data forever.
            if outcome.is_fallback and not args.allow_fallback:
                skipped_fallback += 1
                consecutive_fallbacks += 1
                print(f"  [{i}/{len(todo)}] report {report_id}: SKIPPED - model "
                      f"unreachable, baseline answered. Not stored.")

                # Past a handful in a row this is a rate limit or an outage, not a blip.
                # Continuing burns the remaining reports against the same wall.
                if consecutive_fallbacks >= 5:
                    print(f"\n[!] {consecutive_fallbacks} fallbacks in a row - stopping.")
                    print("    The model is unreachable or the key is rate-limited. Check")
                    print("    x-ratelimit-limit-tokens on a manual call, then re-run with")
                    print("    a larger --delay. Nothing has been written for these reports.")
                    break
            else:
                db.insert_prediction(
                    report_id=report_id,
                    result=outcome.result,
                    model_version=outcome.model_version,
                    is_fallback=outcome.is_fallback,
                )
                consecutive_fallbacks = 0
                status = "FALLBACK-STORED" if outcome.is_fallback else "ok"
                precursor = outcome.result.is_sif_precursor
                print(f"  [{i}/{len(todo)}] report {report_id}: "
                      f"precursor={precursor} severity={outcome.result.severity} "
                      f"({status})")
                succeeded += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(todo)}] report {report_id}: FAILED - "
                  f"{type(exc).__name__}: {exc}")
            failed += 1
            consecutive_fallbacks = 0

        time.sleep(args.delay)

    print(f"\nDone. {succeeded} stored, {failed} errored, "
          f"{skipped_fallback} skipped as fallbacks.")
    if failed or skipped_fallback:
        print("Re-run to retry them - reports already classified under this version are")
        print("skipped automatically, so nothing is paid for twice.")


if __name__ == "__main__":
    main()