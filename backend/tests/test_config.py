"""Tests for app/config.py — Settings and directory properties."""
import pytest
from pathlib import Path
from app.config import Settings


class TestSettings:
    def test_default_provider(self):
        s = Settings(storage_path="/tmp/test_opus_storage")
        assert s.llm_provider == "ollama"

    def test_default_ollama_values(self):
        s = Settings(storage_path="/tmp/test_opus_storage")
        assert "11434" in s.ollama_base_url
        assert "deepseek" in s.ollama_model

    def test_default_port(self):
        s = Settings(storage_path="/tmp/test_opus_storage")
        assert s.backend_port == 8000

    def test_default_max_file_size(self):
        s = Settings(storage_path="/tmp/test_opus_storage")
        assert s.max_file_size_mb == 100

    def test_uploads_dir_property(self, tmp_path):
        s = Settings(storage_path=str(tmp_path))
        assert s.uploads_dir == tmp_path / "uploads"

    def test_generated_code_dir_property(self, tmp_path):
        s = Settings(storage_path=str(tmp_path))
        assert s.generated_code_dir == tmp_path / "generated_code"

    def test_reports_dir_property(self, tmp_path):
        s = Settings(storage_path=str(tmp_path))
        assert s.reports_dir == tmp_path / "reports"

    def test_sessions_dir_property(self, tmp_path):
        s = Settings(storage_path=str(tmp_path))
        assert s.sessions_dir == tmp_path / "sessions"

    def test_storage_path_is_path_type(self):
        s = Settings(storage_path="/tmp/test_opus_storage")
        assert isinstance(s.storage_path, Path)

    def test_override_provider(self):
        s = Settings(llm_provider="openai", storage_path="/tmp/test_opus_storage")
        assert s.llm_provider == "openai"

    def test_override_openai_key(self):
        s = Settings(openai_api_key="sk-test", storage_path="/tmp/test_opus_storage")
        assert s.openai_api_key == "sk-test"


class TestSettingsDirectoryCreation:
    def test_directories_created_on_import(self):
        from app.config import settings
        assert settings.uploads_dir.exists()
        assert settings.generated_code_dir.exists()
        assert settings.reports_dir.exists()
        assert settings.sessions_dir.exists()
