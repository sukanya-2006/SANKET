"""
test_calibration_sample.py

Tests the updated classifier_llm.py on a small, fixed sample of reports
before spending API budget re-classifying all 150. Prints the resulting
precursor rate on just this sample so you can sanity-check whether the
Gate 3 prompt fix actually moved the needle, before committing to a full
reclassify_all.py run.

This does NOT touch the database - it's a read-only check against the
live classifier.

Usage (from project root):
    python test_calibration_sample.py
"""

import sys
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / "backend" / ".env")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import classifier_llm  # noqa: E402

# A fixed, deliberately mixed sample - not random each run, so results are
# comparable across prompt iterations. Pulled from your rubric's own
# worked examples (§8) plus a couple of the synthetic reports we've
# already seen, covering a range of expected outcomes.
SAMPLE = [
    {
        "id": "rubric-1",
        "text": "Technician opened a pump starter panel to clear a fault; circuit not "
                 "isolated, no lockout applied.",
        "expected": True,  # rubric worked example: severity 5, precursor
    },
    {
        "id": "rubric-3",
        "text": "Fitter on a 5 m scaffold with no guardrail fitted; harness worn but not "
                 "clipped. Fell, fractured pelvis.",
        "expected": True,  # rubric worked example: severity 4, precursor
    },
    {
        "id": "rubric-7",
        "text": "Fitter slipped on the scaffold; harness was clipped to a rated anchor and "
                 "the fall arrest functioned. Unhurt.",
        "expected": False,  # control held - not a precursor
    },
    {
        "id": "rubric-3-not-sif",
        "text": "Worker slipped on wet floor in break room, fractured wrist.",
        "expected": False,  # no high-energy hazard at all
    },
    {
        "id": "rubric-10",
        "text": "Worker struck thumb with hammer, fracture.",
        "expected": False,  # hand-tool energy, not in scope
    },
    {
        "id": "synthetic-mild-1",
        "text": "During the day shift at Storage Site E, a contractor was operating a "
                 "forklift to move barrels when the rear guard rail collapsed. The "
                 "forklift's rear bumper clipped the guard rail, sending the load slightly "
                 "off balance. The contractor immediately stopped the machine and reported "
                 "the incident; no one was injured, but the guard rail had to be repaired "
                 "before resuming operations.",
        "expected": False,  # marginal exposure, no real path to serious injury
    },
    {
        "id": "synthetic-clear-precursor",
        "text": "Crane load swung over the crew during lift; taglines were not used; load "
                 "set down without contact.",
        "expected": True,  # near-miss but clear, direct fatal-potential exposure
    },
    {
        "id": "synthetic-ambiguous",
        "text": "During the day shift on Rig 4, a company employee slipped while climbing "
                 "a ladder to reach the top of the casing. He lost his footing on a wet "
                 "rung, fell about 5 feet onto the concrete floor, and bruised his wrist. "
                 "The fall was halted by the guardrail that was still in place, but the "
                 "incident shows the ladder's footing was compromised by oil residue.",
        "expected": False,  # control (guardrail) held per the narrative
    },
]


def main():
    print(f"Testing {len(SAMPLE)} reports against the updated Gate 3 prompt.\n")

    correct = 0
    flagged = 0

    for item in SAMPLE:
        try:
            result = classifier_llm.classify(item["text"])
        except Exception as exc:  # noqa: BLE001
            print(f"  [{item['id']}] FAILED - {exc}")
            continue

        is_precursor = result["is_sif_precursor"]
        severity = result["severity"]
        matches = is_precursor == item["expected"]
        correct += int(matches)
        flagged += int(is_precursor)

        mark = "correct" if matches else "MISMATCH"
        print(f"  [{item['id']}] expected={item['expected']!s:5} got={is_precursor!s:5} "
              f"severity={severity} ({mark})")

        time.sleep(2)  # pacing, same reasoning as the other scripts

    print(f"\n{correct}/{len(SAMPLE)} matched expectations.")
    print(f"Flagged as precursor: {flagged}/{len(SAMPLE)} "
          f"({flagged / len(SAMPLE):.0%}) - "
          f"target is roughly 20-25% flagged across a large, representative set "
          f"(this small sample is deliberately mixed, not representative on its own).")


if __name__ == "__main__":
    main()