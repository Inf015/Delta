from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base de datos
    database_url: str = "postgresql://simtelemetry:changeme@db:5432/simtelemetry"
    # Pool de conexiones — aumentar en producción según carga
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_pool_recycle: int = 1800  # segundos — reconectar conexiones viejas

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # Auth — SECRET_KEY DEBE setearse como env var en producción
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
    track_maps_path: str = "/data/track_maps"

    # CORS — separar por comas en producción: https://app.example.com,https://www.example.com
    allowed_origins: str = "http://localhost:3000"

    # Entorno (development | production)
    environment: str = "development"

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_not_be_default(cls, v: str) -> str:
        import os
        if v == "changeme" and os.getenv("ENVIRONMENT", "development") == "production":
            raise ValueError("SECRET_KEY no puede ser 'changeme' en producción")
        return v

    @field_validator("anthropic_api_key")
    @classmethod
    def anthropic_key_format(cls, v: str) -> str:
        import os
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production" and v and not v.startswith("sk-ant-"):
            raise ValueError("ANTHROPIC_API_KEY tiene formato inválido")
        return v

    class Config:
        env_file = ".env"


settings = Settings()
