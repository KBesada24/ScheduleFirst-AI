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
    
    # API Keys
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    
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
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=4, alias="API_WORKERS")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, alias="RATE_LIMIT_PERIOD")  # seconds
    
    # Monitoring & Error Tracking
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")
    
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent / ".env",  # Points to root .env
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
                f"GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY\n"
                f"Error: {e}"
            )
    return _settings


# Export for easy imports
settings = get_settings()
