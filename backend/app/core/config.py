import os
from pathlib import Path

from pydantic_settings import BaseSettings

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_PATH = REPO_ROOT / "dclaw_agent.db"


def _default_database_url() -> str:
    """Default to a local SQLite file so devs can boot without Docker.

    Production / Docker should set DATABASE_URL explicitly to Postgres.
    """
    if env_url := os.environ.get("DATABASE_URL"):
        return env_url
    return f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH}"


class Settings(BaseSettings):
    database_url: str = _default_database_url()
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    class Config:
        env_file = ".env"


settings = Settings()
