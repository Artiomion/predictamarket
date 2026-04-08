from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/predictamarket"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT — no defaults: service MUST NOT start with known secrets
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 15  # minutes
    JWT_REFRESH_EXPIRATION: int = 43200  # 30 days in minutes

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_PRO_MONTHLY: str = ""
    STRIPE_PRICE_PRO_ANNUAL: str = ""
    STRIPE_PRICE_PREMIUM_MONTHLY: str = ""
    STRIPE_PRICE_PREMIUM_ANNUAL: str = ""

    # External APIs
    FRED_API_KEY: str = ""

    # Observability
    SENTRY_DSN: str = ""

    # Service URLs (for api-gateway proxying)
    AUTH_SERVICE_URL: str = "http://localhost:8001"
    MARKET_SERVICE_URL: str = "http://localhost:8002"
    NEWS_SERVICE_URL: str = "http://localhost:8003"
    FORECAST_SERVICE_URL: str = "http://localhost:8004"
    PORTFOLIO_SERVICE_URL: str = "http://localhost:8005"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8006"
    EDGAR_SERVICE_URL: str = "http://localhost:8007"

    # Internal service-to-service auth — no default
    INTERNAL_API_KEY: str

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Email (SendGrid or SMTP)
    EMAIL_ENABLED: bool = False
    SENDGRID_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "alerts@predictamarket.com"
    EMAIL_FROM_NAME: str = "PredictaMarket"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # App
    APP_ENV: str = "development"
    DEBUG: bool = True

    @field_validator("JWT_SECRET", "INTERNAL_API_KEY")
    @classmethod
    def no_placeholder_secrets(cls, v: str, info) -> str:
        placeholders = {"change-me-in-production", "change-me-internal-key", "secret", ""}
        if v.lower() in placeholders:
            raise ValueError(f"{info.field_name} must be set to a real secret, not a placeholder")
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
