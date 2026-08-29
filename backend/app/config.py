from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Blank until Phase 3 — the API runs fully in stub mode without a database.
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Flip to false once the real pipeline (Member 2) is wired in.
    stub_mode: bool = True

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    rubric_version: str = "2.0"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def db_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
