from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str = "sk-placeholder"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DATABASE_URL: str = "sqlite:///./app.db"
    UPLOAD_DIR: str = "./uploads"
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

settings = Settings()
