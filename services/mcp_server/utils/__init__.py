"""
Utility modules for the MCP server
"""
from .logger import get_logger, setup_logging
from .cache import cache_manager
from .validators import validate_course_code, validate_semester, validate_time_range
from .exceptions import (
    ScheduleOptimizerError,
    DataNotFoundError,
    DataStaleError,
    ScrapingError,
    PopulationError,
    CircuitBreakerOpenError,
    ValidationError,
    DatabaseError,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitState,
    circuit_breaker_registry,
    ratemyprof_breaker,
    cuny_scraper_breaker,
    supabase_breaker,
    ollama_breaker,
)

__all__ = [
    "get_logger",
    "setup_logging",
    "cache_manager",
    "validate_course_code",
    "validate_semester",
    "validate_time_range",
    # Exceptions
    "ScheduleOptimizerError",
    "DataNotFoundError",
    "DataStaleError",
    "ScrapingError",
    "PopulationError",
    "CircuitBreakerOpenError",
    "ValidationError",
    "DatabaseError",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitState",
    "circuit_breaker_registry",
    "ratemyprof_breaker",
    "cuny_scraper_breaker",
    "supabase_breaker",
    "ollama_breaker",
]
