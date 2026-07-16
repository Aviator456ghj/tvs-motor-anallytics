from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ServicesOS Platform API"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/servicesos"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    default_commission_rate: float = 0.12  # 12% platform commission
    default_advance_percent: float = 0.30  # 30% advance at booking time

    cors_origins: list[str] = ["http://localhost:3000"]

    # Payment gateway keys (stubbed - wire real keys via env in production)
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    stripe_secret_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
