from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    llm_provider: Literal["ollama", "openai", "anthropic", "gemini"] = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "deepseek-r1:latest"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-7"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    backend_port: int = 8000
    storage_path: Path = Path("./storage")
    max_file_size_mb: int = 100
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def uploads_dir(self) -> Path:
        return self.storage_path / "uploads"

    @property
    def generated_code_dir(self) -> Path:
        return self.storage_path / "generated_code"

    @property
    def reports_dir(self) -> Path:
        return self.storage_path / "reports"

    @property
    def sessions_dir(self) -> Path:
        return self.storage_path / "sessions"


settings = Settings()

for d in [settings.uploads_dir, settings.generated_code_dir,
          settings.reports_dir, settings.sessions_dir]:
    d.mkdir(parents=True, exist_ok=True)
