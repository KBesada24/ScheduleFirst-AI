"""
API Response Models
Standardized response wrappers for the REST API
"""
from typing import Generic, TypeVar, Optional, Any, List, Dict, Literal, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

T = TypeVar("T")

class DataQuality(str, Enum):
    """Indicates the quality/completeness of returned data"""
    FULL = "full"           # All requested data available and fresh
    PARTIAL = "partial"     # Some data missing or from fallback sources
    DEGRADED = "degraded"   # Significant data missing, using cached/stale data
    MINIMAL = "minimal"     # Only basic data available


class ResponseMetadata(BaseModel):
    """Metadata for API responses"""
    source: str = Field(..., description="Source of data: cache, database, scraper, hybrid")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    is_fresh: bool = Field(..., description="Whether data is considered fresh")
    auto_populated: bool = Field(False, description="Whether data was auto-populated on demand")
    count: Optional[int] = Field(None, description="Number of items in result")
    data_quality: DataQuality = Field(
        default=DataQuality.FULL, 
        description="Quality indicator for returned data"
    )


class ApiResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper for successful responses"""
    success: bool = Field(default=True, description="Whether the request succeeded")
    data: T
    metadata: ResponseMetadata
    warnings: List[str] = Field(
        default_factory=list, 
        description="Non-fatal warnings about the response"
    )


class ErrorResponse(BaseModel):
    """
    Unified error response format for all API errors.
    
    This provides consistent error handling across all endpoints with
    machine-readable codes and user-friendly messages.
    """
    success: bool = Field(default=False, description="Always False for errors")
    error: bool = Field(default=True, description="Indicates this is an error response")
    code: str = Field(..., description="Machine-readable error code (e.g., DATA_NOT_FOUND)")
    message: str = Field(..., description="Technical error message for logging/debugging")
    user_message: str = Field(..., description="User-friendly message for display")
    details: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Additional context about the error"
    )
    suggestions: List[str] = Field(
        default_factory=list, 
        description="Actionable suggestions to resolve the error"
    )
    
    @classmethod
    def from_exception(cls, exc: Exception, code: str = "INTERNAL_ERROR") -> "ErrorResponse":
        """Create ErrorResponse from a generic exception"""
        from ..utils.exceptions import ScheduleOptimizerError
        
        if isinstance(exc, ScheduleOptimizerError):
            return cls(
                code=exc.code,
                message=exc.message,
                user_message=exc.user_message,
                details=exc.details,
                suggestions=exc.suggestions
            )
        
        return cls(
            code=code,
            message=str(exc),
            user_message="An unexpected error occurred. Please try again.",
            details={"exception_type": type(exc).__name__},
            suggestions=["If the problem persists, contact support"]
        )


class ApiResponseUnion(BaseModel):
    """
    Union type for API responses that can be either success or error.
    Use this for OpenAPI documentation of endpoints that may return errors.
    """
    # This is a discriminated union - check 'success' field
    pass


# Type alias for endpoints that return data or errors
ApiResult = Union[ApiResponse[T], ErrorResponse]


class HealthResponse(BaseModel):
    """Health check response"""
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Overall system health status"
    )
    database: Literal["connected", "disconnected"] = Field(
        ..., description="Database connection status"
    )
    environment: str = Field(..., description="Current environment (development/production)")
    gemini_api: Literal["configured", "not configured"] = Field(
        ..., description="Gemini API configuration status"
    )
    cache: Optional[Dict[str, Any]] = Field(
        default=None, description="Cache statistics if available"
    )
    circuit_breakers: Optional[Dict[str, str]] = Field(
        default=None, description="Circuit breaker states"
    )


class PaginationMetadata(BaseModel):
    """Pagination information for list endpoints"""
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response wrapper"""
    success: bool = Field(default=True)
    data: List[T]
    metadata: ResponseMetadata
    pagination: PaginationMetadata
    warnings: List[str] = Field(default_factory=list)

