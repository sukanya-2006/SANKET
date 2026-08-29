"""Test setup: importable `app`, and an isolated cache per test.

The classification cache is on disk by design (it survives restarts so the demo is wifi-proof),
which means tests must not share it — a cached answer from one test would silently satisfy the
next one's assertion.
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
    yield
    cache.clear()
    get_settings.cache_clear()
