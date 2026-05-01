from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_secret_key: str = "change-me-in-production"
    admin_password: str = "admin"
    database_path: str = "/app/data/regits.db"
    upload_dir: str = "/app/uploads"
    max_upload_mb: int = 12
    ocr_timeout_seconds: int = 8
    ocr_fallback_timeout_seconds: int = 3
    ocr_max_dimension: int = 1800

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
