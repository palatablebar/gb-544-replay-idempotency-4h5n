"""集中配置：全部来自环境变量，默认值与 .env.example 保持一致。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # 数据库
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "syncmesh"
    db_user: str = "syncmesh"
    db_password: str = "syncmesh_pw_2026"

    # 安全
    jwt_secret: str = "syncmesh-jwt-secret-change-me-2026"
    api_key_pepper: str = "syncmesh-api-key-pepper-2026"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    refresh_token_days: int = 7

    # 运行时
    redis_url: str = "redis://localhost:6379/0"
    source_dir: str = "/data/sources"
    artifact_dir: str = "/data/artifacts"
    max_upload_mb: int = 200
    default_max_concurrent_runs: int = 2
    mock_rest_base_url: str = "http://backend:8000"
    scheduler_poll_seconds: int = 30
    seed_demo: bool = True

    # schema 名
    meta_schema: str = "meta"
    staging_schema: str = "staging"
    target_schema: str = "target"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def async_engine_url(self) -> str:  # 预留：worker 与本服务共用同一 URL
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
