"""
config/settings.py — GeoRisk Oracle configuration
Reads from .env via pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # NVIDIA NIM (Nemotron + Llama)
    nim_api_key: str = ""
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1"  # deep reasoning
    llama_model: str = "meta/llama-3.3-70b-instruct"           # fast screener

    # Risk scoring
    risk_threshold: int = 60       # alert if score >= this
    max_tokens: int = 2048
    temperature: float = 0.2       # low temp for deterministic reasoning

    # NewsAPI
    news_api_key: str = ""
    news_max_articles: int = 10

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
