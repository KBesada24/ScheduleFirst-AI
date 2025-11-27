"""
Data Population Service
Coordinates on-demand data fetching and population
"""
import asyncio
from typing import Optional, Dict, Any
from uuid import UUID

from ..utils.logger import get_logger
from .data_freshness_service import data_freshness_service
from .supabase_service import supabase_service

# Import background jobs
# Note: Using string imports or deferred imports inside methods might be safer 
# to avoid circular dependencies if jobs import services that import this
from ...background_jobs.jobs.sync_cuny_courses import sync_courses_job
from ...background_jobs.jobs.scrape_reviews import scrape_reviews_job
from ...background_jobs.jobs.update_professor_grades import update_grades_job


logger = get_logger(__name__)


class DataPopulationService:
    """Service to ensure data exists and is fresh"""
    
    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        logger.info("Data Population Service initialized")
    
    async def ensure_course_data(
        self, 
        semester: str, 
        university: str, 
        force: bool = False
    ) -> bool:
        """
        Ensure course data exists for a semester/university.
        If missing or stale, triggers sync job.
        """
        try:
            # Check freshness if not forced
            if not force and await data_freshness_service.is_course_data_fresh(semester, university):
                return True
            
            lock_key = f"courses:{semester}:{university}"
            
            # Acquire lock to prevent duplicate syncs
            async with await self._get_lock(lock_key):
                # Double check freshness after acquiring lock (in case another process just finished)
                if not force and await data_freshness_service.is_course_data_fresh(semester, university):
                    return True
                
                logger.info(f"Triggering on-demand course sync for {semester} at {university}")
                
                # Mark as in progress
                await data_freshness_service.mark_sync_in_progress("courses", semester, university)
                
                # Trigger job
                result = await sync_courses_job(semester=semester, university=university)
                
                if result.get("success"):
                    return True
                else:
                    logger.error(f"Course sync failed: {result.get('error')}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error ensuring course data: {e}")
            return False

    async def ensure_professor_data(
        self, 
        professor_name: str, 
        university: str, 
        force: bool = False
    ) -> bool:
        """
        Ensure professor data (reviews and grades) exists.
        """
        try:
            # Check if professor exists first
            professor = await supabase_service.get_professor_by_name(professor_name, university)
            
            # If professor exists, check freshness
            if professor and not force:
                if await data_freshness_service.is_professor_data_fresh(professor.id):
                    return True
            
            lock_key = f"professor:{professor_name}:{university}"
            
            async with await self._get_lock(lock_key):
                # Double check
                if professor and not force:
                    if await data_freshness_service.is_professor_data_fresh(professor.id):
                        return True
                
                logger.info(f"Triggering on-demand professor scrape for {professor_name}")
                
                # 1. Scrape reviews
                scrape_result = await scrape_reviews_job(
                    professor_name=professor_name, 
                    university=university
                )
                
                if not scrape_result.get("success"):
                    logger.error(f"Review scrape failed: {scrape_result.get('error')}")
                    return False
                
                # Refresh professor object to get ID if it was just created
                if not professor:
                    professor = await supabase_service.get_professor_by_name(professor_name, university)
                    if not professor:
                        logger.error("Professor still not found after scrape")
                        return False
                
                # 2. Update grades
                grade_result = await update_grades_job(professor_id=professor.id)
                
                return grade_result.get("success", False)

        except Exception as e:
            logger.error(f"Error ensuring professor data: {e}")
            return False

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create a lock for a specific key"""
        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]


# Singleton instance
data_population_service = DataPopulationService()
