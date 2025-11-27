"""
Data Freshness Service
Manages data staleness logic and sync metadata
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from ..models.sync_metadata import SyncMetadata
from ..services.supabase_service import supabase_service
from ..utils.logger import get_logger


logger = get_logger(__name__)


class DataFreshnessService:
    """Service to check if data is fresh based on TTLs"""
    
    # TTL Constants (in seconds)
    COURSE_DATA_TTL = 7 * 24 * 3600  # 7 days
    PROFESSOR_DATA_TTL = 7 * 24 * 3600  # 7 days
    REVIEW_DATA_TTL = 30 * 24 * 3600  # 30 days
    
    def __init__(self):
        logger.info("Data Freshness Service initialized")
    
    async def is_course_data_fresh(self, semester: str, university: str) -> bool:
        """
        Check if course data for a semester/university is fresh
        Returns True if data exists and is within TTL
        """
        try:
            # Check sync metadata first
            metadata = await supabase_service.get_sync_metadata("courses", semester, university)
            
            if not metadata or metadata.sync_status != "success":
                return False
            
            # Check if expired
            if self._is_expired(metadata.last_sync, self.COURSE_DATA_TTL):
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking course freshness: {e}")
            return False
    
    async def is_professor_data_fresh(self, professor_id: UUID) -> bool:
        """
        Check if professor data is fresh
        Returns True if data exists and is within TTL
        """
        try:
            professor = await supabase_service.get_professor_by_id(professor_id)
            
            if not professor or not professor.last_updated:
                return False
            
            # Check if expired
            if self._is_expired(professor.last_updated, self.PROFESSOR_DATA_TTL):
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking professor freshness: {e}")
            return False
    
    async def is_review_data_fresh(self, professor_id: UUID) -> bool:
        """
        Check if review data for a professor is fresh
        Returns True if recent reviews exist
        """
        try:
            # Check sync metadata for reviews
            # Note: We might need a more granular way to track review syncs per professor
            # For now, we check the professor's last update time as a proxy
            return await self.is_professor_data_fresh(professor_id)
            
        except Exception as e:
            logger.error(f"Error checking review freshness: {e}")
            return False
    
    async def get_last_sync(self, entity_type: str, semester: str, university: str) -> Optional[datetime]:
        """Get the last successful sync timestamp"""
        try:
            metadata = await supabase_service.get_sync_metadata(entity_type, semester, university)
            if metadata and metadata.sync_status == "success":
                return metadata.last_sync
            return None
        except Exception as e:
            logger.error(f"Error getting last sync: {e}")
            return None
    
    async def mark_sync_in_progress(self, entity_type: str, semester: str, university: str) -> bool:
        """Mark a sync operation as in progress"""
        try:
            return await supabase_service.update_sync_metadata(
                entity_type, semester, university, "in_progress"
            )
        except Exception as e:
            logger.error(f"Error marking sync in progress: {e}")
            return False
    
    async def mark_sync_complete(
        self, 
        entity_type: str, 
        semester: str, 
        university: str, 
        status: str = "success",
        error: Optional[str] = None
    ) -> bool:
        """Mark a sync operation as complete (success or failed)"""
        try:
            return await supabase_service.update_sync_metadata(
                entity_type, semester, university, status, error
            )
        except Exception as e:
            logger.error(f"Error marking sync complete: {e}")
            return False

    def _is_expired(self, timestamp: datetime, ttl_seconds: int) -> bool:
        """Check if a timestamp is older than TTL"""
        # Ensure timestamp is timezone-aware if needed, or naive if comparing to naive
        # For simplicity assuming both are compatible or naive UTC
        if timestamp.tzinfo is None:
            now = datetime.now()
        else:
            now = datetime.now(timestamp.tzinfo)
            
        return (now - timestamp).total_seconds() > ttl_seconds


# Singleton instance
data_freshness_service = DataFreshnessService()
