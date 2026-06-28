import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    database_url: str = f"sqlite+aiosqlite:///{DATA_DIR / 'stock_research_v2.db'}"
    host: str = "0.0.0.0"
    port: int = 8000
    # Phase 2 AI
    minimax_api_key: str = ""
    minimax_model: str = "MiniMax-Text-01"

    model_config = {"env_file": str(BASE_DIR / ".env"), "extra": "ignore"}


settings = Settings()
