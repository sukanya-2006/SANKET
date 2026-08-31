# from functools import lru_cache
# from pathlib import Path

# from pydantic_settings import BaseSettings, SettingsConfigDict


# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(env_file=".env", extra="ignore")

#     # Supabase is Postgres. We connect with psycopg over the pooled connection string so the
#     # aggregation runs the exact plain SQL in sql/aggregates.sql — which is the thing Member 4
#     # has to be able to read aloud. Blank means the API runs database-free on the seeded stub.
#     supabase_db_url: str = ""

#     # Only needed if something later wants the REST/storage APIs. The SQL path does not use it.
#     supabase_url: str = ""
#     supabase_service_key: str = ""

#     # Bumped whenever the classification prompt changes. Part of the cache key, so a prompt
#     # edit cannot silently serve answers produced by the previous prompt.
#     prompt_version: str = "v1"

#     # TECH_STACK v2: on API failure or timeout, the local baseline answers.
#     llm_timeout_seconds: float = 10.0

#     cache_path: Path = Path("cache.sqlite3")
#     cache_enabled: bool = True

#     cors_origins: str = "http://localhost:5173,http://localhost:3000"

#     rubric_version: str = "2.1"

#     @property
#     def cors_origin_list(self) -> list[str]:
#         return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

#     @property
#     def db_configured(self) -> bool:
#         return bool(self.supabase_db_url)


# @lru_cache
# def get_settings() -> Settings:
#     return Settings()

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
    prompt_version: str = "v1"

    # TECH_STACK v2: on API failure or timeout, the local baseline answers.
    # Raised from the original 10.0s default - the primary model
    # (gpt-oss-20b via Groq) occasionally needs longer than 10s under load,
    # and a premature timeout wastes a perfectly good answer by discarding
    # it in favour of the much weaker stub fallback. This value is the
    # floor even if .env doesn't set LLM_TIMEOUT_SECONDS at all.
    llm_timeout_seconds: float = 25.0

    cache_path: Path = Path("cache.sqlite3")
    cache_enabled: bool = True

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    rubric_version: str = "2.1"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def db_configured(self) -> bool:
        return bool(self.supabase_db_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()