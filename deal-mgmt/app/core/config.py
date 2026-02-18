from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "Deal Management"
    DEBUG: bool = False
    SECRET_KEY: str = ""
    JWT_SECRET: str = ""  # 크로스 백엔드 공유 시크릿 (비어있으면 SECRET_KEY 폴백)

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://deal_mgmt_user:deal_mgmt_dev_password@localhost:5436/deal_mgmt"

    # JWT
    JWT_ALGORITHM: str = "HS256"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]

    # Database Pool
    DB_POOL_SIZE: int = 10
    DB_POOL_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_TIMEOUT: int = 30

    # Service URLs (inter-service communication)
    FDD_API_URL: str = "http://localhost:8000/api/v1"
    IM_API_URL: str = "http://localhost:8002/api"
    KIIS_API_URL: str = "http://localhost:8001/api/v1"


settings = Settings()
