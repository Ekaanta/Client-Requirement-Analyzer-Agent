from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field


class Settings(BaseSettings):
    # Grok AI
    grok_api_key: str = Field(default="", alias="GROK_API_KEY")
    grok_model: str = Field(
        default="grok-3-mini",
        validation_alias=AliasChoices("GROK_MODEL", "ROK_MODEL"),
    )

    # n8n
    n8n_webhook_url: str = Field(
        default="http://localhost:5678/webhook/requirement-validator",
        alias="N8N_WEBHOOK_URL",
    )
    n8n_api_key: str = Field(default="", alias="N8N_API_KEY")

    # Figma
    figma_access_token: str = Field(default="", alias="FIGMA_ACCESS_TOKEN")

    # FastAPI
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_debug: bool = Field(default=False, alias="API_DEBUG")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")

    # Streamlit
    backend_url: str = Field(default="http://localhost:8000", alias="BACKEND_URL")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", alias="LOG_FILE")

    # Timeouts
    n8n_timeout_seconds: int = 120

    figma_timeout_seconds: int = 30

    model_config = {
        "env_file": Path(__file__).resolve().parents[2] / ".env",
        "populate_by_name": True,
        "extra": "ignore",
    }


def get_settings() -> Settings:
    return Settings()
