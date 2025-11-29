"""
API Response Models
Standardized response wrappers for the REST API
"""
from typing import Generic, TypeVar, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMetadata(BaseModel):
    """Metadata for API responses"""
    source: str = Field(..., description="Source of data: cache, database, scraper, hybrid")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    is_fresh: bool = Field(..., description="Whether data is considered fresh")
    auto_populated: bool = Field(False, description="Whether data was auto-populated on demand")
    count: Optional[int] = Field(None, description="Number of items in result")


class ApiResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper"""
    data: T
    metadata: ResponseMetadata
