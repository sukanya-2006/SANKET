"""
generate_synthetic_reports_free.py

Generates 150 synthetic industrial safety incident reports using Groq's
FREE API (Llama 3.3 70B model), with randomly (but weighted) selected
site / shift / contractor_flag metadata baked into the prompt.

Groq offers a genuinely free tier - no credit card needed.
Get a free API key at: https://console.groq.com

Output: data/synthetic/synthetic_reports.csv
Columns: report_id, text, site, shift, contractor_flag, hazard_type_hint
"""

import os
import csv
import random
import time
from groq import Groq

# ---------------------------------------------------------------------------
# 1. CONFIG - edit these if your team wants different sites/weights
# ---------------------------------------------------------------------------

NUM_REPORTS = 150

# (site_name, weight) - weight controls how many reports land at that site.
# These add up to 150 exactly, matching the "uneven distribution" plan.
SITES_WITH_WEIGHTS = [
    ("Rig 4", 40),
    ("Refinery B", 30),
    ("Terminal C", 25),
    ("Pipeline Yard D", 20),
    ("Storage Site E", 15),
    ("Drilling Unit F", 10),
    ("Loading Bay G", 6),
    ("Maintenance Shop H", 4),
]

SHIFTS = ["Day", "Night"]

# Roughly 30% of reports involve a contractor rather than a direct employee
CONTRACTOR_PROBABILITY = 0.30

HAZARD_TYPES = [
    "fall_from_height",
    "energy_isolation_failure",
    "vehicle_pedestrian_interaction",
    "confined_space_entry",
    "ppe_noncompliance",
    "equipment_machinery_hazard",
    "fire_or_gas_leak_near_miss",
    "slip_trip_hazard",
]

OUTPUT_DIR = "data/synthetic"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "synthetic_reports.csv")

# Groq model - Llama models moved to Enterprise/Contact Sales tier.
# Using GPT OSS 20B instead - available on free/self-serve tier.
MODEL_NAME = "openai/gpt-oss-20b"

# ---------------------------------------------------------------------------
# 2. Build the exact list of (site, shift, contractor_flag, hazard_type)
#    combinations we'll generate, honoring the weights.
# ---------------------------------------------------------------------------

def build_report_plan():
    plan = []
    for site_name, weight in SITES_WITH_WEIGHTS:
        for _ in range(weight):
            plan.append({
                "site": site_name,
                "shift": random.choice(SHIFTS),
                "contractor_flag": random.random() < CONTRACTOR_PROBABILITY,
                "hazard_type_hint": random.choice(HAZARD_TYPES),
            })

    assert len(plan) == NUM_REPORTS, (
        f"Site weights sum to {len(plan)}, expected {NUM_REPORTS}. "
        f"Fix SITES_WITH_WEIGHTS."
    )

    random.shuffle(plan)
    return plan


# ---------------------------------------------------------------------------
# 3. Call Groq to generate one report's text given its metadata context
# ---------------------------------------------------------------------------

client = Groq()  # reads GROQ_API_KEY from environment variable

SYSTEM_PROMPT = """You write realistic industrial safety incident reports for an \
oilfield/refinery operations context (similar to Oil India Limited's operations). \
Each report should read the way a field worker or safety officer would actually \
write it: 2-4 sentences, plain language, sometimes slightly informal, describing \
what happened and the immediate hazard. Do not include any labels, headers, or \
metadata in your output - just the incident narrative text itself. Do not \
mention severity ratings or classifications - just describe what occurred."""


def generate_one_report(site, shift, contractor_flag, hazard_type_hint):
    contractor_text = "a contractor" if contractor_flag else "a company employee"

    user_prompt = f"""Write one realistic industrial safety incident report with these \
details worked naturally into the narrative:
- Location: {site}
- Shift: {shift} shift
- Person involved: {contractor_text}
- General hazard category to center the incident on: {hazard_type_hint.replace('_', ' ')}

Vary the severity naturally - some reports should describe near-misses or minor \
issues, others should describe situations where a safety barrier clearly failed \
or was missing. Do not always describe the worst-case outcome. Write only the \
incident narrative, nothing else."""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=800,
        reasoning_effort="low",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    text = response.choices[0].message.content.strip()

    # Some models return empty content or get cut off - treat these as
    # failures so the retry logic in main() kicks in instead of silently
    # saving a blank/broken row.
    if not text or len(text) < 20:
        raise ValueError(f"Response too short or empty: '{text}'")

    return text


# ---------------------------------------------------------------------------
# 4. Main loop: generate all 150, save progressively so a crash doesn't
#    lose everything.
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    plan = build_report_plan()

    print(f"Generating {len(plan)} synthetic reports using Groq ({MODEL_NAME})...")
    print(f"Saving progressively to {OUTPUT_FILE}\n")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["report_id", "text", "site", "shift", "contractor_flag", "hazard_type_hint"])

        for i, item in enumerate(plan, start=1):
            try:
                text = generate_one_report(
                    site=item["site"],
                    shift=item["shift"],
                    contractor_flag=item["contractor_flag"],
                    hazard_type_hint=item["hazard_type_hint"],
                )
            except Exception as e:
                print(f"  [!] Report {i} failed: {e}. Waiting 5s and retrying once...")
                time.sleep(5)
                try:
                    text = generate_one_report(
                        site=item["site"],
                        shift=item["shift"],
                        contractor_flag=item["contractor_flag"],
                        hazard_type_hint=item["hazard_type_hint"],
                    )
                except Exception as e2:
                    print(f"  [!!] Report {i} failed again: {e2}. Skipping, filling placeholder.")
                    text = "[GENERATION FAILED - fill in manually]"

            writer.writerow([
                i,
                text,
                item["site"],
                item["shift"],
                item["contractor_flag"],
                item["hazard_type_hint"],
            ])
            f.flush()

            print(f"  [{i}/{len(plan)}] {item['site']} | {item['shift']} | "
                  f"contractor={item['contractor_flag']} | {item['hazard_type_hint']}")

            # Groq's free tier has rate limits - this delay keeps you safely under them
            time.sleep(1.2)

    print(f"\nDone. Saved {len(plan)} reports to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()