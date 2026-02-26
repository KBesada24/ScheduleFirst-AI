"""
Configuration management for CUNY Schedule Optimizer Backend
Loads environment variables and provides typed configuration objects
"""
import os
from pathlib import Path
from typing import Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    
    @staticmethod
    def parse_bool(v: Any) -> bool:
        """Parse boolean from string values"""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return bool(v)
    
    # Ollama Configuration
    ollama_host: str = Field(default="https://ollama.com", alias="OLLAMA_HOST")
    ollama_model: str = Field(default="qwen3-coder-next:cloud", alias="OLLAMA_MODEL")
    ollama_api_key: Optional[str] = Field(default=None, alias="OLLAMA_API_KEY")
    
    # Supabase Configuration
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(..., alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_anon_key: str = Field(..., alias="SUPABASE_ANON_KEY")
    
    # Database Configuration (Optional - only needed for direct PostgreSQL access)
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    
    # Redis/Cache Configuration (optional)
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")
    cache_ttl: int = Field(default=3600, alias="CACHE_TTL")  # 1 hour default
    cache_max_size: int = Field(default=1000, alias="CACHE_MAX_SIZE")
    cache_ttl_courses: int = Field(default=86400, alias="CACHE_TTL_COURSES")  # 24 hours
    cache_ttl_professors: int = Field(default=43200, alias="CACHE_TTL_PROFESSORS")  # 12 hours
    cache_ttl_reviews: int = Field(default=21600, alias="CACHE_TTL_REVIEWS")  # 6 hours
    cache_ttl_schedules: int = Field(default=1800, alias="CACHE_TTL_SCHEDULES")  # 30 minutes
    
    # Web Scraping Configuration
    scraper_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        alias="SCRAPER_USER_AGENT"
    )
    scraper_request_delay: float = Field(default=2.0, alias="SCRAPER_REQUEST_DELAY")
    scraper_max_retries: int = Field(default=3, alias="SCRAPER_MAX_RETRIES")
    
    # CUNY Global Search Configuration
    cuny_global_search_url: str = Field(
        default="https://globalsearch.cuny.edu/",
        alias="CUNY_GLOBAL_SEARCH_URL"
    )
    cuny_browser_use_enabled: bool = Field(default=False, alias="CUNY_BROWSER_USE_ENABLED")
    cuny_selenium_fallback_enabled: bool = Field(default=True, alias="CUNY_SELENIUM_FALLBACK_ENABLED")
    cuny_shadow_mode: bool = Field(default=False, alias="CUNY_SHADOW_MODE")
    cuny_browser_use_timeout: int = Field(default=45, alias="CUNY_BROWSER_USE_TIMEOUT")
    cuny_browser_use_max_retries: int = Field(default=1, alias="CUNY_BROWSER_USE_MAX_RETRIES")
    browser_use_api_key: Optional[str] = Field(default=None, alias="BROWSER_USE_API_KEY")
    cuny_browser_use_poll_interval: int = Field(default=2, alias="CUNY_BROWSER_USE_POLL_INTERVAL")
    cuny_browser_use_max_steps: int = Field(default=140, alias="CUNY_BROWSER_USE_MAX_STEPS")
    cuny_browser_use_llm: str = Field(default="browser-use-llm", alias="CUNY_BROWSER_USE_LLM")
    
    # RateMyProfessors Configuration
    ratemyprof_base_url: str = Field(
        default="https://www.ratemyprofessors.com",
        alias="RATEMYPROF_BASE_URL"
    )
    ratemyprof_graphql_url: str = Field(
        default="https://www.ratemyprofessors.com/graphql",
        alias="RATEMYPROF_GRAPHQL_URL"
    )
    
    # Sentiment Analysis Configuration
    sentiment_model_name: str = Field(
        default="distilbert-base-uncased-finetuned-sst-2-english",
        alias="SENTIMENT_MODEL_NAME"
    )
    
    # Schedule Optimization Configuration
    max_schedules_to_generate: int = Field(default=5, alias="MAX_SCHEDULES_TO_GENERATE")
    optimization_timeout: int = Field(default=30, alias="OPTIMIZATION_TIMEOUT")  # seconds
    
    # Background Jobs Configuration
    sync_schedule_cron: str = Field(
        default="0 2 * * 0",  # Every Sunday at 2 AM
        alias="SYNC_SCHEDULE_CRON"
    )
    
    # Logging Configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")  # json or text
    log_max_bytes: int = Field(default=10_485_760, alias="LOG_MAX_BYTES")  # 10MB
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")
    log_full_tool_results: bool = Field(default=False, alias="LOG_FULL_TOOL_RESULTS")
    log_tool_result_preview_chars: int = Field(default=200, alias="LOG_TOOL_RESULT_PREVIEW_CHARS")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=4, alias="API_WORKERS")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, alias="RATE_LIMIT_PERIOD")  # seconds
    
    # Monitoring & Error Tracking
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")
    
    # Admin API Key (for protected admin endpoints)
    admin_api_key: Optional[str] = Field(default=None, alias="ADMIN_API_KEY")
    
    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).parent.parent.parent / ".env",        # Root .env
            Path(__file__).parent.parent.parent / ".env.local",  # Root .env.local
            Path(__file__).parent.parent / ".env",               # services/.env
            Path(__file__).parent.parent / ".env.local",         # services/.env.local
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton"""
    global _settings
    if _settings is None:
        try:
            _settings = Settings()  # type: ignore
        except Exception as e:
            raise RuntimeError(
                f"Failed to load settings. Please ensure your .env file exists in the project root "
                f"and contains all required environment variables:\n"
                f"SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY\n"
                f"Optional: OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_API_KEY\n"
                f"Error: {e}"
            )
    return _settings


# Export for easy imports
settings = get_settings()