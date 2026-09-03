"""
doctor.py — what is wired, what is missing, and what to do next.

    python doctor.py              full status
    python doctor.py --member 5   just what Member 5 needs
    python doctor.py --quiet      one line per check, for a quick glance

Run this before asking anyone what the state of the project is, and again before
any demo. It never modifies anything and never fails - if a component is missing
it says so and tells you the command that fixes it.

Written because "does the backend work / are the labels done / is Supabase up"
was being answered by reading six files and asking two people.
"""

import argparse
import csv
import io
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OK, BAD, WARN, INFO = "  [ok]  ", "  [--]  ", "  [!!]  ", "        "
todo = []          # (priority, member, action)


def note(priority, member, action):
    todo.append((priority, member, action))


def section(title):
    print(f"\n{title}")
    print("  " + "-" * 68)


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------- environment
def check_env():
    section("ENVIRONMENT")
    print(f"{OK}python {sys.version.split()[0]}")

    missing = []
    for mod, why in [("fastapi", "the API"), ("pydantic", "the schema"),
                     ("psycopg", "Postgres"), ("groq", "the real classifier"),
                     ("sklearn", "the baseline"), ("pandas", "the label scripts")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append((mod, why))

    if missing:
        for mod, why in missing:
            print(f"{BAD}{mod} not installed — needed for {why}")
        note(1, "anyone", "pip install -r backend/requirements.txt")
    else:
        print(f"{OK}all dependencies installed")

    env = ROOT / "backend" / ".env"
    if env.exists():
        print(f"{OK}backend/.env present")
    else:
        print(f"{BAD}backend/.env missing — no database, no API key")
        note(1, "M4", "create backend/.env (copy .env.example) and set SUPABASE_DB_URL")

    if os.environ.get("GROQ_API_KEY"):
        print(f"{OK}GROQ_API_KEY set in the environment")
    elif env.exists() and "GROQ_API_KEY" in env.read_text(encoding="utf-8", errors="replace"):
        print(f"{OK}GROQ_API_KEY present in backend/.env")
    else:
        print(f"{WARN}GROQ_API_KEY not found — the API will answer from the baseline")
        note(2, "M2", "add GROQ_API_KEY to backend/.env")


# ---------------------------------------------------------------- backend
def check_backend():
    section("BACKEND")
    try:
        from app import classifier, db
        from app.config import get_settings
    except Exception as exc:
        print(f"{BAD}cannot import the app: {type(exc).__name__}: {exc}")
        note(1, "M4", "backend is not importable — fix before anything else")
        return

    settings = get_settings()
    print(f"{OK}app imports cleanly")
    print(f"{INFO}rubric version {settings.rubric_version}, prompt version {settings.prompt_version}")

    if db.is_live():
        try:
            n = db.query("SELECT count(*) AS n FROM reports")[0]["n"]
            print(f"{OK}database connected — {n} reports loaded")
            if not n:
                note(2, "M4", "python load_reports.py  (database is empty)")
        except Exception as exc:
            print(f"{WARN}database configured but unreachable: {exc}")
            note(1, "M4", "check SUPABASE_DB_URL; the project may be paused")
    else:
        print(f"{WARN}no database — the API serves the seeded stub (180 fake reports)")
        note(1, "M4", "set SUPABASE_DB_URL in backend/.env, then: python load_reports.py")

    versions = classifier.active_versions()
    for slot, label in [("primary", "real classifier"), ("baseline", "fallback")]:
        v = versions[slot]
        if v == "stub-0.1.0":
            print(f"{WARN}{slot:<9} = {v}  (keyword stub, NOT the {label})")
        else:
            print(f"{OK}{slot:<9} = {v}")

    if versions["baseline"] == "stub-0.1.0":
        note(2, "M2", "python train_baseline.py  (needs data/gold_labels.csv first)")


# ---------------------------------------------------------------- data
def check_data():
    section("DATA AND LABELS")

    for rel, what in [("data/synthetic/synthetic_reports_for_labeling.csv", "150 synthetic reports"),
                      ("data/osha/osha_real_reports.csv", "30 OSHA reports")]:
        path = ROOT / rel
        if path.exists():
            print(f"{OK}{what}: {len(read_csv(path))} rows")
        else:
            print(f"{BAD}{rel} missing")
            note(1, "M3", f"produce {rel}")

    annotators = sorted(
        p for p in (ROOT / "data").glob("*labels_*.csv")
        if "stub" not in p.name and "gold_labels.csv" not in p.name
    )
    if not annotators:
        print(f"{BAD}no annotator files found")
        note(1, "M1/M3", "python create_labeling_template.py --annotator <name>")

    for path in annotators:
        try:
            rows = read_csv(path)
        except Exception:
            continue
        if not rows or "hazard_assessment" not in rows[0]:
            continue
        done = sum(1 for r in rows if (r.get("hazard_assessment") or "").strip())
        mark = OK if done == len(rows) else (WARN if done else BAD)
        print(f"{mark}{path.name:<40} {done}/{len(rows)} labelled")
        if 0 < done < len(rows):
            note(1, "annotator", f"python label_reports.py --annotator "
                                 f"{path.stem.split('labels_')[-1]}")

    gold = ROOT / "data" / "gold_labels.csv"
    if gold.exists():
        rows = read_csv(gold)
        print(f"{OK}gold_labels.csv: {len(rows)} adjudicated labels")
        if len(rows) < 150:
            note(2, "M6", f"only {len(rows)} gold labels — tiebreak the remainder "
                          "(data/labeling_disagreements.csv)")
    else:
        print(f"{BAD}gold_labels.csv missing — nothing downstream can run")
        note(1, "M3", "python merge_labels.py --a <A>.csv --b <B>.csv")

    model = ROOT / "backend" / "app" / "baseline_model.joblib"
    print(f"{OK if model.exists() else BAD}baseline_model.joblib "
          f"{'trained' if model.exists() else 'not trained'}")


# ---------------------------------------------------------------- honesty
def check_honesty():
    """The checks that protect the numbers we quote on stage."""
    section("NUMBERS WE COULD BE ASKED TO DEFEND")

    files = sorted(
        p for p in (ROOT / "data").glob("*labels_*.csv")
        if "stub" not in p.name and "gold_labels.csv" not in p.name
    )
    complete = []
    for path in files:
        try:
            rows = read_csv(path)
        except Exception:
            continue
        if rows and "hazard_assessment" in rows[0] and all(
            (r.get("hazard_assessment") or "").strip() for r in rows
        ):
            complete.append((path, rows))

    if len(complete) < 2:
        print(f"{INFO}fewer than two complete annotator files — no ceiling to compute yet")
        return

    # Was is_sif_precursor derived, or typed by feel?
    for path, rows in complete:
        bad = 0
        for r in rows:
            h = (r.get("hazard_assessment") or "").strip()
            c = (r.get("control_status") or "").strip()
            try:
                s = int(r.get("severity") or 0)
            except ValueError:
                continue
            derived = h == "yes" and c in ("absent", "failed") and s >= 4
            typed = str(r.get("is_sif_precursor") or "").strip().upper() == "TRUE"
            bad += derived != typed
        pct = bad / len(rows)
        if pct > 0.05:
            print(f"{WARN}{path.name}: {bad}/{len(rows)} rows contradict their own gates "
                  f"({pct:.0%})")
            note(1, "M1", f"{path.name} typed is_sif_precursor by hand — rerun "
                          f"check_independence.py before quoting any number")
        else:
            print(f"{OK}{path.name}: is_sif_precursor derived correctly")

    print(f"{INFO}for the ceiling itself run:")
    print(f"{INFO}  python check_independence.py --a <A>.csv --b <B>.csv")


# ---------------------------------------------------------------- tests
def check_tests(run):
    section("TESTS")
    if not run:
        print(f"{INFO}skipped (pass --tests to run them)")
        return
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT / "backend", capture_output=True, text=True,
    )
    tail = [l for l in result.stdout.strip().splitlines() if l.strip()][-1:]
    line = tail[0] if tail else "no output"
    print(f"{OK if result.returncode == 0 else BAD}{line}")
    if result.returncode != 0:
        note(1, "anyone", "cd backend && pytest -q   — the suite is red")


# ---------------------------------------------------------------- next steps
MEMBER_WORK = {
    "1": ["Own the rubric, the pitch and the honesty line.",
          "Book the 15-minute external EHS review — rubric §9 has a blank for the name.",
          "Keep docs/rubric.md's changelog truthful about what changed between labelling rounds."],
    "2": ["Train the baseline the hour gold_labels.csv lands: python train_baseline.py",
          "train_baseline.py should read eval/split.json so the baseline is not scored on its",
          "  own training data — see the leakage warning in eval/run_eval.py.",
          "Tune the prompt on the 30 dev reports only. Bump PROMPT_VERSION when you change it."],
    "3": ["Own evaluation: python eval/run_eval.py",
          "Report F1 and PR-AUC, never accuracy. Quote the agreement ceiling first."],
    "4": ["Set SUPABASE_DB_URL in backend/.env, then python load_reports.py",
          "Then python batch_classify.py to populate predictions."],
    "5": ["The API runs with no database and no key — build against it now.",
          "cd backend && uvicorn app.main:app --reload   then http://localhost:8000/docs",
          "Generate types from /openapi.json. Build the degraded-mode banner on is_fallback."],
    "6": ["Deploy: render.yaml is ready. Vercel for the frontend.",
          "Verify the suite the way a stranger would: clone, venv, pip install, pytest.",
          "Free tiers sleep — wake Render and Supabase before any demo."],
}


def print_next(member):
    section("WHAT TO DO NEXT")
    if member:
        for line in MEMBER_WORK.get(member, [f"no entry for member {member}"]):
            print(f"{INFO}{line}")
        print()

    if not todo:
        print(f"{OK}nothing blocking found")
        return

    for priority, who in sorted({(p, w) for p, w, _ in todo}):
        actions = [a for p, w, a in todo if (p, w) == (priority, who)]
        if member and who not in (member, f"M{member}", "anyone", "annotator"):
            continue
        tag = "BLOCKING" if priority == 1 else "then"
        for a in actions:
            print(f"  {tag:<9} [{who:<9}] {a}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--member", help="1-6: show that member's work as well")
    ap.add_argument("--tests", action="store_true", help="actually run the test suite")
    ap.add_argument("--quiet", action="store_true", help="skip the next-steps section")
    args = ap.parse_args()

    print("=" * 72)
    print("  SIF PRECURSOR DETECTION — PROJECT DOCTOR")
    print("=" * 72)

    check_env()
    check_backend()
    check_data()
    check_honesty()
    check_tests(args.tests)
    if not args.quiet:
        print_next(args.member)
    print()


if __name__ == "__main__":
    main()
