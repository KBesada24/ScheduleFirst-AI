"""
Sync Metadata Pydantic model
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict


class SyncMetadata(BaseModel):
    """Model for tracking data synchronization status"""
    id: UUID = Field(default_factory=uuid4)
    entity_type: str = Field(..., description="Type of entity: courses, professors, reviews")
    semester: Optional[str] = Field(None, description="Semester (for courses)")
    university: Optional[str] = Field(None, description="University name")
    last_sync: datetime = Field(default_factory=datetime.now)
    sync_status: str = Field(..., description="Status: success, failed, in_progress")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True)
