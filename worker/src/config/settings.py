"""worker 侧配置：沿用 backend 的环境变量约定。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "syncmesh"
    db_user: str = "syncmesh"
    db_password: str = "syncmesh_pw_2026"
    redis_url: str = "redis://redis:6379/0"
    source_dir: str = "/data/sources"
    artifact_dir: str = "/data/artifacts"
    mock_rest_base_url: str = "http://backend:8000"
    scheduler_poll_seconds: int = 30

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()


settings = get_settings()
