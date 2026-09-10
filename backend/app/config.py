from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Supabase is Postgres. We connect with psycopg over the pooled connection string so the
    # aggregation runs the exact plain SQL in sql/aggregates.sql — which is the thing Member 4
    # has to be able to read aloud. Blank means the API runs database-free on the seeded stub.
    supabase_db_url: str = ""

    # Only needed if something later wants the REST/storage APIs. The SQL path does not use it.
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Bumped whenever the classification prompt changes. Part of the cache key, so a prompt
    # edit cannot silently serve answers produced by the previous prompt.
    prompt_version: str = "v4"

    # TECH_STACK v2: on API failure or timeout, the local baseline answers.
    # Raised from the original 10.0s default - the primary model
    # (gpt-oss-20b via Groq) occasionally needs longer than 10s under load,
    # and a premature timeout wastes a perfectly good answer by discarding
    # it in favour of the much weaker stub fallback. This value is the
    # floor even if .env doesn't set LLM_TIMEOUT_SECONDS at all.
    llm_timeout_seconds: float = 60.0

    cache_path: Path = Path("backend/app/llm_cache.sqlite")
    cache_enabled: bool = True

    # cors_origins: str = "http://localhost:5173,http://localhost:3000"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,https://sanket-frontend.onrender.com"
    rubric_version: str = "2.2"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def db_configured(self) -> bool:
        return bool(self.supabase_db_url)


# backend/app/config.py -> backend/app -> backend -> repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    # Anchor a relative cache path to the repo root rather than the working directory.
    # The documented way to start the server is `cd backend && uvicorn app.main:app`, so a
    # path like "backend/app/llm_cache.sqlite" resolved against the cwd becomes
    # backend/backend/app/... which does not exist - and every /analyze request then 500s on
    # "unable to open database file". The tests never saw it because conftest points
    # CACHE_PATH at a tmp directory that always exists.
    if not settings.cache_path.is_absolute():
        object.__setattr__(settings, "cache_path", REPO_ROOT / settings.cache_path)

    return settings