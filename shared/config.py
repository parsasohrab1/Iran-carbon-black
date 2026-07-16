from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    service_name: str = "unknown"
    service_port: int = 8000
    domain: str = ""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "carbon_black"
    postgres_user: str = "icb_admin"
    postgres_password: str = "change_me"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "icb_minio"
    minio_root_password: str = "change_me"
    minio_bucket_raw: str = "datalake-raw"
    minio_bucket_curated: str = "datalake-curated"
    minio_bucket_models: str = "ml-models"
    minio_secure: bool = False

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883

    jwt_secret: str = "change_me_jwt_secret_min_32_chars_long!!"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    auth_2fa_enabled: bool = True
    auth_2fa_required: bool = False
    auth_max_failed_logins: int = 5
    auth_lockout_minutes: int = 15
    password_min_length: int = 10
    require_password_complexity: bool = True

    # OT / IT zoning
    network_zone: str = "it"  # it | ot | dmz
    ot_api_allowlist: str = "/health,/ready,/metrics,/api/v1/ingestion/,/api/v1/energy/"

    # SLA targets (SRS)
    sla_availability_target: float = 99.9
    rto_seconds: int = 7200
    rpo_seconds: int = 3600

    backup_dir: str = "./backups"
    rate_limit_per_minute: int = 120

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
