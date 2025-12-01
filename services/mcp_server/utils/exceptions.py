"""
Custom exception hierarchy for CUNY Schedule Optimizer
Provides structured error handling with consistent error codes and messages
"""
from typing import Optional, Dict, Any, List


class ScheduleOptimizerError(Exception):
    """
    Base exception for all Schedule Optimizer errors.
    
    Attributes:
        code: Machine-readable error code (e.g., "DATA_NOT_FOUND")
        message: Technical error message for logging
        user_message: User-friendly message for display
        details: Additional context about the error
        suggestions: Actionable suggestions to resolve the error
    """
    
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.user_message = user_message or "An unexpected error occurred. Please try again."
        self.details = details or {}
        self.suggestions = suggestions or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "code": self.code,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
            "suggestions": self.suggestions
        }


class DataNotFoundError(ScheduleOptimizerError):
    """
    Raised when requested data does not exist in database or external sources.
    
    Examples:
        - Course not found for given semester/university
        - Professor not found in RateMyProfessors
        - Section ID does not exist
    """
    
    def __init__(
        self,
        entity_type: str,
        identifier: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        default_message = f"{entity_type} not found: {identifier}"
        default_user_message = f"The requested {entity_type.lower()} could not be found."
        default_suggestions = [
            f"Verify the {entity_type.lower()} identifier is correct",
            "Try searching with different criteria",
            "The data may not be available for this semester"
        ]
        
        super().__init__(
            message=message or default_message,
            code="DATA_NOT_FOUND",
            user_message=default_user_message,
            details={
                "entity_type": entity_type,
                "identifier": identifier,
                **(details or {})
            },
            suggestions=suggestions or default_suggestions
        )
        self.entity_type = entity_type
        self.identifier = identifier


class DataStaleError(ScheduleOptimizerError):
    """
    Raised when data exists but is too old to be reliable.
    
    Examples:
        - Course data older than 7 days
        - Professor reviews older than 30 days
        - Sync metadata indicates failed refresh
    """
    
    def __init__(
        self,
        entity_type: str,
        last_updated: str,
        ttl_exceeded_by: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        default_message = f"{entity_type} data is stale (last updated: {last_updated})"
        default_user_message = f"The {entity_type.lower()} data is outdated and may not be accurate."
        default_suggestions = [
            "Request a data refresh",
            "Results shown may not reflect current availability",
            "Check back later for updated information"
        ]
        
        super().__init__(
            message=message or default_message,
            code="DATA_STALE",
            user_message=default_user_message,
            details={
                "entity_type": entity_type,
                "last_updated": last_updated,
                "ttl_exceeded_by": ttl_exceeded_by,
                **(details or {})
            },
            suggestions=suggestions or default_suggestions
        )
        self.entity_type = entity_type
        self.last_updated = last_updated


class ScrapingError(ScheduleOptimizerError):
    """
    Raised when web scraping operations fail.
    
    Examples:
        - CUNY Global Search is unavailable
        - RateMyProfessors API returns error
        - Network timeout during scraping
        - Rate limiting encountered
    """
    
    def __init__(
        self,
        source: str,
        reason: Optional[str] = None,
        operation: Optional[str] = None,
        is_retryable: bool = True,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        op_str = f" during {operation}" if operation else ""
        default_message = f"Scraping failed for {source}{op_str}: {reason or 'Unknown error'}"
        default_user_message = f"Unable to fetch data from {source}. Please try again later."
        
        default_suggestions = []
        if is_retryable:
            default_suggestions.append("Try again in a few moments")
        default_suggestions.extend([
            "The external service may be temporarily unavailable",
            "Cached data may be available as a fallback"
        ])
        
        super().__init__(
            message=message or default_message,
            code="SCRAPING_ERROR",
            user_message=default_user_message,
            details={
                "source": source,
                "operation": operation,
                "reason": reason,
                "is_retryable": is_retryable,
                **(details or {})
            },
            suggestions=suggestions or default_suggestions
        )
        self.source = source
        self.operation = operation
        self.is_retryable = is_retryable


class PopulationError(ScheduleOptimizerError):
    """
    Raised when on-demand data population fails.
    
    Examples:
        - Failed to populate course data for semester
        - Failed to enrich professor with reviews
        - Partial population completed with errors
    """
    
    def __init__(
        self,
        entity_type: str,
        operation: str,
        partial_success: bool = False,
        items_succeeded: int = 0,
        items_failed: int = 0,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        if partial_success:
            default_message = f"Partial population of {entity_type}: {items_succeeded} succeeded, {items_failed} failed"
            default_user_message = f"Some {entity_type.lower()} data could not be loaded. Showing partial results."
        else:
            default_message = f"Failed to populate {entity_type} during {operation}"
            default_user_message = f"Unable to load {entity_type.lower()} data. Please try again."
        
        default_suggestions = [
            "Try again with fewer items",
            "Some data may be available from cache",
            "Check if the semester/university combination is valid"
        ]
        
        super().__init__(
            message=message or default_message,
            code="POPULATION_ERROR" if not partial_success else "PARTIAL_POPULATION",
            user_message=default_user_message,
            details={
                "entity_type": entity_type,
                "operation": operation,
                "partial_success": partial_success,
                "items_succeeded": items_succeeded,
                "items_failed": items_failed,
                **(details or {})
            },
            suggestions=suggestions or default_suggestions
        )
        self.entity_type = entity_type
        self.partial_success = partial_success
        self.items_succeeded = items_succeeded
        self.items_failed = items_failed


class CircuitBreakerOpenError(ScheduleOptimizerError):
    """
    Raised when a circuit breaker is open and requests are being rejected.
    
    Examples:
        - Too many failures to RateMyProfessors API
        - Database connection failures exceeded threshold
        - Scraper rate limited
    """
    
    def __init__(
        self,
        service_name: str,
        retry_after_seconds: int,
        failure_count: int,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        default_message = f"Circuit breaker open for {service_name} after {failure_count} failures"
        default_user_message = f"The {service_name} service is temporarily unavailable."
        default_suggestions = [
            f"Please try again in {retry_after_seconds} seconds",
            "Cached data may be available",
            "Try a different query or filter"
        ]
        
        super().__init__(
            message=message or default_message,
            code="CIRCUIT_BREAKER_OPEN",
            user_message=default_user_message,
            details={
                "service_name": service_name,
                "retry_after_seconds": retry_after_seconds,
                "failure_count": failure_count,
                **(details or {})
            },
            suggestions=suggestions or default_suggestions
        )
        self.service_name = service_name
        self.retry_after_seconds = retry_after_seconds


class ValidationError(ScheduleOptimizerError):
    """
    Raised when input validation fails.
    
    Examples:
        - Invalid course code format
        - Invalid semester string
        - Missing required parameters
    """
    
    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        default_message = f"Validation failed for {field}: {reason}"
        default_user_message = f"Invalid value for {field}."
        default_suggestions = [
            f"Check the format of {field}",
            "Refer to the API documentation for valid values"
        ]
        
        super().__init__(
            message=message or default_message,
            code="VALIDATION_ERROR",
            user_message=default_user_message,
            details={
                "field": field,
                "value": str(value),
                "reason": reason,
                **(details or {})
            },
            suggestions=suggestions or default_suggestions
        )
        self.field = field
        self.value = value
        self.reason = reason


class DatabaseError(ScheduleOptimizerError):
    """
    Raised when database operations fail.
    
    Examples:
        - Connection timeout
        - Query execution failed
        - Transaction rollback
    """
    
    def __init__(
        self,
        operation: str,
        reason: Optional[str] = None,
        is_retryable: bool = True,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        default_message = f"Database error during {operation}: {reason or 'Unknown error'}"
        default_user_message = "A database error occurred. Please try again."
        
        default_suggestions = []
        if is_retryable:
            default_suggestions.append("Try again in a few moments")
        default_suggestions.append("If the problem persists, contact support")
        
        super().__init__(
            message=message or default_message,
            code="DATABASE_ERROR",
            user_message=default_user_message,
            details={
                "operation": operation,
                "reason": reason,
                "is_retryable": is_retryable,
                **(details or {})
            },
            suggestions=suggestions or default_suggestions
        )
        self.operation = operation
        self.is_retryable = is_retryable


class RateLimitError(ScheduleOptimizerError):
    """
    Raised when an external service rate limits requests.
    
    Examples:
        - 429 Too Many Requests from RateMyProfessors
        - API quota exceeded
    """
    
    def __init__(
        self,
        service: str,
        retry_after: Optional[int] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        default_message = f"Rate limit exceeded for {service}"
        if retry_after:
            default_message += f". Retry after {retry_after}s"
            
        default_user_message = f"The {service} service is busy. Please try again later."
        
        default_suggestions = [
            "Wait a few moments before trying again",
            "Reduce the frequency of requests"
        ]
        if retry_after:
            default_suggestions.insert(0, f"Wait {retry_after} seconds")
            
        super().__init__(
            message=message or default_message,
            code="RATE_LIMIT_ERROR",
            user_message=default_user_message,
            details={
                "service": service,
                "retry_after": retry_after,
                **(details or {})
            },
            suggestions=suggestions or default_suggestions
        )
        self.service = service
        self.retry_after = retry_after


class ExternalServiceError(ScheduleOptimizerError):
    """
    Raised when an external service fails or returns an error.
    
    Examples:
        - 500 Internal Server Error from API
        - Service is down or unreachable
        - Bad Gateway / Service Unavailable
    """
    
    def __init__(
        self,
        service: str,
        operation: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        default_message = f"External service error in {service} during {operation}"
        default_user_message = f"The {service} service encountered an error."
        
        default_suggestions = [
            "Try again later",
            "The service may be down for maintenance",
            "Check service status page if available"
        ]
        
        super().__init__(
            message=message or default_message,
            code="EXTERNAL_SERVICE_ERROR",
            user_message=default_user_message,
            details={
                "service": service,
                "operation": operation,
                **(details or {})
            },
            suggestions=suggestions or default_suggestions
        )
        self.service = service
        self.operation = operation


# Export all exceptions
__all__ = [
    "ScheduleOptimizerError",
    "DataNotFoundError",
    "DataStaleError",
    "ScrapingError",
    "PopulationError",
    "CircuitBreakerOpenError",
    "ValidationError",
    "DatabaseError",
    "RateLimitError",
    "ExternalServiceError",
]
