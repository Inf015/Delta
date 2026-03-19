from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base de datos
    database_url: str = "postgresql://simtelemetry:changeme@db:5432/simtelemetry"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # Auth
    secret_key: str = "changeme"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 días

    # Anthropic
    anthropic_api_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Google Drive
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/drive/callback"

    # Storage
    csv_data_path: str = "/data/csvs"
    pdf_data_path: str = "/data/pdfs"
    kb_data_path: str = "/data/knowledge_base"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
