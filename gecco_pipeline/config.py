from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    """Pipeline configuration loaded from environment variables and .env file."""

    # API Configuration
    GOOGLE_API_KEY: str = Field(description="Google AI API key for Gemini")
    MODEL_NAME: str = Field(default="gemini-2.5-flash")

    # Paths
    PDF_BASE_DIR: Path = Field(default=Path("data/pdfs"))
    OUTPUT_DIR: Path = Field(default=Path("data/outputs"))
    REPORTS_DIR: Path = Field(default=Path("data/reports"))

    # Processing
    MAX_RETRIES: int = Field(default=3)
    RETRY_BASE_DELAY: float = Field(default=2.0, description="Base delay in seconds for exponential backoff")
    BATCH_SIZE: int = Field(default=5, description="Number of concurrent extractions")
    RATE_LIMIT_RPM: int = Field(default=60, description="Max requests per minute")
    TEMPERATURE: float = Field(default=0.1, description="LLM temperature for extraction")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_settings() -> Settings:
    """Create and return a Settings instance."""
    return Settings()
