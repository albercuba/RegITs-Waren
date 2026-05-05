from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_secret_key: str = "change-me-in-production"
    admin_password: str = "admin"
    cors_origins: str = "http://localhost:8081,http://localhost:5173,http://127.0.0.1:5173"
    database_path: str = "/app/data/regits.db"
    upload_dir: str = "/app/uploads"
    max_upload_mb: int = 12
    ocr_max_dimension: int = 1800
    ocr_timeout_seconds: int = 8
    ocr_fallback_timeout_seconds: int = 3
    ocr_default_mode: str = "fast"
    barcode_high_confidence_score: int = 50
    barcode_margin_over_second: int = 25

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
