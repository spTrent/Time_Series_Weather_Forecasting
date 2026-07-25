from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine

MODELS_DIR = Path(__file__).resolve().parents[2] / 'Models'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    postgres_user: str
    postgres_password: str
    postgres_db: str
    pgdb_host: str = 'localhost'
    pgdb_port: int = 5432


settings = Settings()  # type: ignore[call-arg]


def get_engine() -> Engine:
    url = (
        f'postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}'
        f'@{settings.pgdb_host}:{settings.pgdb_port}/{settings.postgres_db}'
    )
    return create_engine(url, pool_pre_ping=True)
