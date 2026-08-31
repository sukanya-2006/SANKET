"""
load_reports.py

Loads the 150 synthetic + 30 OSHA reports into the live Supabase `reports`
table. Run this once Supabase is connected (confirmed via /health showing
"database": "connected").

Usage (from project root):
    python load_reports.py

Reads:  data/synthetic/synthetic_reports_for_labeling.csv
        data/osha/osha_real_reports.csv

Safe to re-run: uses INSERT ... ON CONFLICT DO NOTHING, so re-running this
after reports already exist won't create duplicates.
"""

import sys
import os
import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# This script runs from the project root, but backend/app/config.py's
# .env lookup is relative to the current working directory - so without
# this, it silently looks in the wrong place and db_configured comes back
# False even though backend/.env is set up correctly.
load_dotenv(dotenv_path=Path(__file__).resolve().parent / "backend" / ".env")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import db  # noqa: E402

SYNTHETIC_PATH = "data/synthetic/synthetic_reports_for_labeling.csv"
OSHA_PATH = "data/osha/osha_real_reports.csv"

INSERT_REPORT = """
INSERT INTO reports (
    report_id, report_text, source, site, activity, shift,
    report_date, is_contractor, created_at
) VALUES (
    %(report_id)s, %(report_text)s, %(source)s, %(site)s, %(activity)s, %(shift)s,
    %(report_date)s, %(is_contractor)s, %(created_at)s
)
ON CONFLICT (report_id) DO NOTHING
"""

INSERT_SITE = """
INSERT INTO sites (site) VALUES (%(site)s)
ON CONFLICT (site) DO NOTHING
"""


def load_sites(report_rows):
    """The reports table has a foreign key to sites - every distinct site
    name used by a report must exist there first, or the insert fails."""
    distinct_sites = sorted({
        r["site"] for r in report_rows if r.get("site")
    })
    if not distinct_sites:
        return
    site_rows = [{"site": s} for s in distinct_sites]
    inserted = db.executemany(INSERT_SITE, site_rows)
    print(f"Ensured {len(distinct_sites)} sites exist in the sites table "
          f"({inserted} newly inserted).")


def load_synthetic():
    if not os.path.exists(SYNTHETIC_PATH):
        print(f"[!] {SYNTHETIC_PATH} not found, skipping.")
        return []

    df = pd.read_csv(SYNTHETIC_PATH, encoding="utf-8-sig")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "report_id": str(r["report_id"]),
            "report_text": r["text"],
            "source": "synthetic",
            "site": r["site"],
            "activity": r["activity"],
            "shift": r["shift"].lower() if isinstance(r["shift"], str) else r["shift"],
            "report_date": r["report_date"],
            "is_contractor": bool(r["is_contractor"]),
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        })
    return rows


def load_osha():
    if not os.path.exists(OSHA_PATH):
        print(f"[!] {OSHA_PATH} not found, skipping.")
        return []

    df = pd.read_csv(OSHA_PATH, encoding="utf-8-sig")
    text_col = "report_text" if "report_text" in df.columns else "text"

    rows = []
    for i, r in df.iterrows():
        # OSHA reports have no site/activity/shift metadata - null is the
        # honest answer, not a fabricated guess. The dashboard's aggregation
        # already excludes source='osha' from site/activity rankings for
        # exactly this reason (see TECH_STACK.md aggregation rules).
        rows.append({
            "report_id": str(151 + i),
            "report_text": r[text_col],
            "source": "osha",
            "site": None,
            "activity": None,
            "shift": None,
            "report_date": datetime.date.today().isoformat(),
            "is_contractor": None,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        })
    return rows


def main():
    if not db.is_live():
        sys.exit(
            "[!] Database is not configured/reachable. Check SUPABASE_DB_URL "
            "in backend/.env and confirm /health shows database: connected."
        )

    all_rows = load_synthetic() + load_osha()

    if not all_rows:
        sys.exit("[!] No report data found to load.")

    load_sites(all_rows)

    inserted = db.executemany(INSERT_REPORT, all_rows)
    print(f"Attempted to insert {len(all_rows)} reports "
          f"({inserted} new rows written; existing report_ids were skipped).")


if __name__ == "__main__":
    main()