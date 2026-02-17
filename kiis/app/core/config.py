from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "KIIS"
    DEBUG: bool = False
    SECRET_KEY: str = ""
    JWT_SECRET: str = ""  # 크로스 백엔드 공유 시크릿 (비어있으면 SECRET_KEY 폴백)

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://kiis_user:kiis_dev_password@localhost:5432/kiis"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ElasticSearch
    ELASTICSEARCH_URL: str = ""

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]

    # Rate Limiting (Auth)
    RATE_LIMIT_LOGIN_MAX: int = 5
    RATE_LIMIT_LOGIN_WINDOW: int = 60

    # Database Pool
    DB_POOL_SIZE: int = 10
    DB_POOL_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_TIMEOUT: int = 30

    # DART API
    DART_API_KEY: str = ""
    DART_BASE_URL: str = "https://opendart.fss.or.kr/api"
    DART_RATE_LIMIT_PER_MINUTE: int = 900
    DART_RATE_LIMIT_PER_DAY: int = 9000

    # KOFIA (금융투자협회)
    KOFIA_DIS_BASE_URL: str = "https://dis.kofia.or.kr"
    KOFIA_RATE_LIMIT_PER_MINUTE: int = 20  # 3초 간격 = 분당 20회
    KOFIA_RATE_LIMIT_PER_DAY: int = 1000
    KOFIA_REQUEST_DELAY: float = 3.0  # robots.txt 준수 최소 간격 (초)
    KOFIA_DB_FRESHNESS_HOURS: int = 24  # DB 데이터 최신 판별 기준 (시간)

    # Slack
    SLACK_WEBHOOK_URL: str = ""

    # SMTP (Email)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True

    # Scheduler
    SCHEDULER_ENABLED: bool = True
    DART_SYNC_INTERVAL_HOURS: int = 1
    NEWS_COLLECT_INTERVAL_HOURS: int = 2
    REPUTATION_RECALC_HOUR: int = 3
    PORTFOLIO_CHECK_HOUR: int = 5
    WATCHLIST_ALERT_INTERVAL_HOURS: int = 6
    MANAGER_TRACKING_DAY_OF_WEEK: str = "mon"

    # REITs (리츠정보시스템)
    REITS_BASE_URL: str = "https://reits.molit.go.kr"
    REITS_RATE_LIMIT_PER_MINUTE: int = 20  # 3초 간격 = 분당 20회
    REITS_RATE_LIMIT_PER_DAY: int = 500
    REITS_REQUEST_DELAY: float = 3.0  # robots.txt 준수 최소 간격 (초)


settings = Settings()
