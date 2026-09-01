import sys
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / "backend" / ".env")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app import db, classifier_llm  # noqa: E402

MISSING = """
SELECT r.report_id
FROM reports r
LEFT JOIN latest_predictions l ON l.report_id = r.report_id
WHERE l.report_id IS NULL OR l.model_version != %(v)s
"""

def main():
    if not db.is_live():
        sys.exit("[!] Database not connected.")

    version = classifier_llm.classify.version
    rows = db.query(MISSING, {"v": version})
    print(f"Reports NOT yet on version {version}:\n")
    for r in rows:
        print(r)
    print(f"\nTotal missing: {len(rows)}")

if __name__ == "__main__":
    main()