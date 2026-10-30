import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "SLN Warehouse Management System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, str):
            if v.lower() in ("release", "false", "0", "prod", "production", "no"):
                return False
            if v.lower() in ("debug", "true", "1", "dev", "development", "yes"):
                return True
        return bool(v)

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://odoo:odoo@localhost:5433/sln_warehouse",
        description="Async PostgreSQL connection string using asyncpg driver",
    )
    TEST_DATABASE_URL: str = Field(
        default="postgresql+asyncpg://odoo:odoo@localhost:5433/sln_warehouse_test",
        description="Async PostgreSQL test database connection string",
    )
    SYNC_DATABASE_URL: str = Field(
        default="postgresql+psycopg2://odoo:odoo@localhost:5433/sln_warehouse",
        description="Synchronous PostgreSQL connection string for Alembic migrations if needed",
    )

    JWT_SECRET_KEY: str = Field(
        default="sln-wms-enterprise-backend-secure-dev-key-928374829103847592",
        description="Secret key for signing and verifying JWT tokens",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("prod", "production")


settings = Settings()
