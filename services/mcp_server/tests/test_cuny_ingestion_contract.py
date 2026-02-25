"""Tests for CUNY ingestion contract models and config defaults."""
import pytest

from mcp_server.config import Settings
from mcp_server.services.cuny_ingestion_contract import IngestionSourceResult


class TestIngestionSourceResult:
    def test_defaults_and_serialization(self):
        result = IngestionSourceResult(success=True, source="browser_use")

        assert result.success is True
        assert result.source == "browser_use"
        assert result.courses == []
        assert result.warnings == []
        assert result.error is None

        serialized = result.to_dict()
        assert serialized == {
            "success": True,
            "source": "browser_use",
            "courses": [],
            "warnings": [],
            "error": None,
            "fallback_used": False,
        }


class TestSettingsBrowserUseDefaults:
    def test_browser_use_flag_defaults(self):
        settings = Settings(
            SUPABASE_URL="https://example.supabase.co",
            SUPABASE_SERVICE_ROLE_KEY="service-role",
            SUPABASE_ANON_KEY="anon-key",
            CUNY_BROWSER_USE_ENABLED=False,
            CUNY_SELENIUM_FALLBACK_ENABLED=True,
            CUNY_SHADOW_MODE=False,
            CUNY_BROWSER_USE_TIMEOUT=45,
            CUNY_BROWSER_USE_MAX_RETRIES=1,
            CUNY_BROWSER_USE_POLL_INTERVAL=2,
            CUNY_BROWSER_USE_MAX_STEPS=140,
            CUNY_BROWSER_USE_LLM="browser-use-llm",
            BROWSER_USE_API_KEY=None,
        )

        assert settings.cuny_browser_use_enabled is False
        assert settings.cuny_selenium_fallback_enabled is True
        assert settings.cuny_shadow_mode is False
        assert settings.cuny_browser_use_timeout == 45
        assert settings.cuny_browser_use_max_retries == 1
        assert settings.browser_use_api_key is None
        assert settings.cuny_browser_use_poll_interval == 2
        assert settings.cuny_browser_use_max_steps == 140
        assert settings.cuny_browser_use_llm == "browser-use-llm"
