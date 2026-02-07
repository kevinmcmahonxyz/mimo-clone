from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = "sqlite:///data/db/mimo.db"
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5-20250929"
    sandbox_image: str = "mimo-sandbox:latest"
    sandbox_timeout: int = 10
    sandbox_memory_limit: str = "64m"
    sandbox_cpu_period: int = 100000
    sandbox_cpu_quota: int = 50000
    data_dir: Path = Path("data")
    debug: bool = False

    model_config = {"env_prefix": "MIMO_", "env_file": ".env"}


settings = Settings()
