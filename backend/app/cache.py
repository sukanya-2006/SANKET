"""SQLite classification cache — TECH_STACK v2 §Caching.

Keyed on `sha256(report_text + prompt_version)`. Two jobs:

1. **Reproducible evaluation runs.** Re-running the eval does not re-bill the API or re-roll the
   model's answer, so a number you quoted yesterday is the number you get today.
2. **Wifi insurance for reports we have already seen.** It does not cover the live demo box,
   which takes new text by definition — that is what the offline fallback is for. Cache and
   fallback are both needed; neither replaces the other.

The prompt version is inside the key on purpose: editing the prompt must invalidate every
cached answer, or the eval quietly mixes two prompts.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from contextlib import closing

from .config import get_settings
from .schemas import ClassificationResult

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS classification_cache (
    cache_key      TEXT PRIMARY KEY,
    prompt_version TEXT NOT NULL,
    model_version  TEXT NOT NULL,
    payload        TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def cache_key(report_text: str, prompt_version: str | None = None) -> str:
    version = prompt_version or get_settings().prompt_version
    return hashlib.sha256((report_text + version).encode("utf-8")).hexdigest()


def _connect() -> sqlite3.Connection:
    path = get_settings().cache_path
    # sqlite will not create a missing parent directory; it just reports "unable to open
    # database file", which reads like a permissions problem and is not one.
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.execute(_SCHEMA)
    return conn


def get(report_text: str) -> tuple[ClassificationResult, str] | None:
    """Return (result, model_version) on a hit, or None."""
    settings = get_settings()
    if not settings.cache_enabled:
        return None

    with _lock, closing(_connect()) as conn:
        row = conn.execute(
            "SELECT payload, model_version FROM classification_cache WHERE cache_key = ?",
            (cache_key(report_text),),
        ).fetchone()

    if row is None:
        return None
    return ClassificationResult.model_validate(json.loads(row[0])), row[1]


def put(report_text: str, result: ClassificationResult, model_version: str) -> None:
    settings = get_settings()
    if not settings.cache_enabled:
        return

    with _lock, closing(_connect()) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO classification_cache "
            "(cache_key, prompt_version, model_version, payload) VALUES (?, ?, ?, ?)",
            (
                cache_key(report_text),
                settings.prompt_version,
                model_version,
                result.model_dump_json(),
            ),
        )
        conn.commit()


def clear() -> None:
    with _lock, closing(_connect()) as conn:
        conn.execute("DELETE FROM classification_cache")
        conn.commit()


def size() -> int:
    with _lock, closing(_connect()) as conn:
        return conn.execute("SELECT count(*) FROM classification_cache").fetchone()[0]
