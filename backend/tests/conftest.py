"""Test setup: importable `app`, isolated cache, and a deterministic classifier registry.

Two things here exist to stop tests depending on the machine they run on:

* **The cache is on disk by design** (it survives restarts so the demo is wifi-proof), so tests
  must not share it — a cached answer from one test would silently satisfy the next one's
  assertion.
* **The registry is global.** `main.py` registers the real Groq classifier at import when the
  package is installed, so the same test passed locally and failed on a clean clone purely
  because of whether `pip install -r requirements.txt` had been run and whether a key was set.
  Every test therefore starts from the stub in both slots; tests that care about a specific
  classifier register their own.
"""

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    from app import cache, classifier
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "cache.sqlite3"))
    monkeypatch.setenv("SUPABASE_DB_URL", "")
    classifier.reset_metrics()

    original_primary = classifier._primary
    original_baseline = classifier._baseline
    classifier.register_primary(classifier._stub)
    classifier.register_baseline(classifier._stub)

    yield

    classifier.register_primary(original_primary)
    classifier.register_baseline(original_baseline)
    cache.clear()
    get_settings.cache_clear()
