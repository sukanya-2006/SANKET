import csv
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OSHA_FILE = ROOT / "data" / "osha" / "osha_real_reports.csv"
GOLD_FILE = ROOT / "data" / "gold_labels.csv"
CACHE_FILE = ROOT / "backend" / "app" / "llm_cache.sqlite"

# Load OSHA reports
with open(OSHA_FILE, newline="", encoding="utf-8-sig") as f:
    osha = list(csv.DictReader(f))

# Load gold labels
with open(GOLD_FILE, newline="", encoding="utf-8-sig") as f:
    gold_rows = list(csv.DictReader(f))

# Find the report ID column safely
if not gold_rows:
    raise RuntimeError("gold_labels.csv appears to be empty.")

print("Gold columns found:", list(gold_rows[0].keys()))

gold = {}
for row in gold_rows:
    rid = row.get("report_id")
    if rid is not None and rid.strip().isdigit():
        report_id = int(rid.strip())
        if 151 <= report_id <= 180:
            gold[str(report_id)] = row

# Read cache
db = sqlite3.connect(CACHE_FILE)

PROMPT_VERSION = "v3"

print("\n" + "=" * 100)
print("OSHA DIAGNOSTIC — GOLD vs LLM")
print("=" * 100)

for report in osha:
    report_id = int(report["report_id"])

    if not 151 <= report_id <= 180:
        continue

    text = report.get("report_text") or report.get("text") or ""

    cache_key = hashlib.sha256(
        (text + PROMPT_VERSION).encode("utf-8")
    ).hexdigest()

    row = db.execute(
        """
        SELECT payload
        FROM classification_cache
        WHERE cache_key = ?
        """,
        (cache_key,),
    ).fetchone()

    g = gold.get(str(report_id))

    print(f"\n{'-' * 100}")
    print(f"REPORT {report_id}")
    print(f"{'-' * 100}")
    print(f"TEXT: {text}")

    if not g:
        print("GOLD: MISSING")
        continue

    print(
        f"GOLD: "
        f"hazard={g['hazard_assessment']} | "
        f"LSR={g['lsr_rule']} | "
        f"control={g['control_status']} | "
        f"severity={g['severity']} | "
        f"precursor={g['is_sif_precursor']}"
    )

    if not row:
        print("LLM CACHE: NOT FOUND")
        continue

    try:
        llm = json.loads(row[0])
    except json.JSONDecodeError:
        print("LLM CACHE: INVALID JSON")
        continue

    print(
        f"LLM:  "
        f"hazard={llm.get('hazard_assessment')} | "
        f"LSR={llm.get('lsr_rule')} | "
        f"control={llm.get('control_status')} | "
        f"severity={llm.get('severity')} | "
        f"precursor={llm.get('is_sif_precursor')}"
    )

    print(f"CONFIDENCE: {llm.get('confidence')}")
    print(f"REASONING: {llm.get('reasoning')}")
    print(f"FLAGGED: {llm.get('flagged_phrases')}")

db.close()

print("\n" + "=" * 100)
print("END")
print("=" * 100)