from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://mentor:mentor@localhost:5433/mentor"
    embed_provider: Literal["fake", "ollama", "workers_ai"] = "ollama"
    ollama_url: str = "http://localhost:11434"
    cf_account_id: str = ""
    cf_api_token: str = ""
    daily_limit: int = 200
