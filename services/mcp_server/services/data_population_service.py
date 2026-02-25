"""
Data Population Service
Coordinates on-demand data fetching and population with structured error handling
"""
import asyncio
from typing import Optional, Dict, Any, List
from uuid import UUID

from ..utils.logger import get_logger
from ..utils.exceptions import (
    DatabaseError,
    DataNotFoundError,
    DataStaleError,
    ScrapingError,
    ExternalServiceError,
    CircuitBreakerOpenError,
)
from .data_freshness_service import data_freshness_service
from .supabase_service import supabase_service
from ..utils.cache import cache_manager

# Import background jobs
# Note: Using absolute imports since background_jobs is a sibling package to mcp_server
from background_jobs.jobs.sync_cuny_courses import sync_courses_job
from background_jobs.jobs.scrape_reviews import scrape_reviews_job
from background_jobs.jobs.update_professor_grades import update_grades_job


logger = get_logger(__name__)


class PopulationResult:
    """Result of a data population operation"""
    
    def __init__(
        self,
        success: bool,
        warnings: Optional[List[str]] = None,
        error: Optional[str] = None,
        is_partial: bool = False,
        source: str = "none",
        fallback_used: bool = False,
    ):
        self.success = success
        self.warnings = warnings or []
        self.error = error
        self.is_partial = is_partial
        self.source = source
        self.fallback_used = fallback_used
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "warnings": self.warnings,
            "error": self.error,
            "is_partial": self.is_partial,
            "source": self.source,
            "fallback_used": self.fallback_used,
        }


class DataPopulationService:
    """Service to ensure data exists and is fresh, with structured error handling"""
    
    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        logger.info("Data Population Service initialized")
    
    async def ensure_course_data(
        self, 
        semester: str, 
        university: str, 
        force: bool = False,
        subject_code: Optional[str] = None,
    ) -> PopulationResult:
        """
        Ensure course data exists for a semester/university.
        If missing or stale, triggers sync job.
        
        Returns:
            PopulationResult with success status and any warnings
        """
        warnings: List[str] = []
        
        try:
            # Check cache for recent success
            cache_scope = f":{subject_code.upper()}" if subject_code else ""
            cache_key = f"population:courses:{semester}:{university}{cache_scope}"
            if not force:
                cached_result = await cache_manager.get(cache_key)
                if cached_result:
                    return PopulationResult(success=True, source="cache")

            # Check freshness if not forced
            if not force:
                try:
                    is_fresh = await data_freshness_service.is_course_data_fresh(semester, university)
                    if is_fresh:
                        return PopulationResult(success=True, source="fresh_cache")
                except DatabaseError as e:
                    # Freshness check failed, continue with sync
                    logger.warning(f"Freshness check failed, proceeding with sync: {e}")
                    warnings.append("Could not verify data freshness")
            
            lock_key = f"courses:{semester}:{university}{cache_scope}"
            
            # Acquire lock to prevent duplicate syncs
            async with await self._get_lock(lock_key):
                # Double check freshness after acquiring lock
                if not force:
                    try:
                        if await data_freshness_service.is_course_data_fresh(semester, university):
                            return PopulationResult(success=True, source="fresh_cache")
                    except DatabaseError:
                        pass  # Continue with sync
                
                logger.info(f"Triggering on-demand course sync for {semester} at {university}")
                logger.info(
                    "Course sync scope",
                    extra={
                        "semester": semester,
                        "university": university,
                        "subject_code": subject_code,
                        "force": force,
                        "cache_key": cache_key,
                    },
                )
                
                # Mark as in progress
                try:
                    await data_freshness_service.mark_sync_in_progress("courses", semester, university)
                except DatabaseError as e:
                    # Non-fatal, continue with sync
                    logger.warning(f"Could not mark sync in progress: {e}")
                
                # Trigger job
                sync_kwargs: Dict[str, Any] = {
                    "semester": semester,
                    "university": university,
                }
                if subject_code:
                    sync_kwargs["subject_code"] = subject_code

                result = await sync_courses_job(**sync_kwargs)
                logger.info(
                    "Course sync raw result",
                    extra={
                        "success": result.get("success"),
                        "source": result.get("source"),
                        "fallback_used": result.get("fallback_used"),
                        "courses_synced": result.get("courses_synced"),
                        "sections_synced": result.get("sections_synced"),
                        "warnings": result.get("warnings"),
                        "error": result.get("error"),
                    },
                )
                
                if result.get("success"):
                    await cache_manager.set(cache_key, True, ttl=60)
                    sync_warnings = result.get("warnings") or []
                    return PopulationResult(
                        success=True,
                        warnings=[*warnings, *sync_warnings],
                        source=result.get("source", "none"),
                        fallback_used=bool(result.get("fallback_used", False)),
                        is_partial=len(sync_warnings) > 0,
                    )
                else:
                    error_msg = result.get("error", "Unknown sync error")
                    logger.error(f"Course sync failed: {error_msg}")
                    return PopulationResult(
                        success=False,
                        warnings=[*warnings, *(result.get("warnings") or [])],
                        error=f"Course sync failed: {error_msg}",
                        source=result.get("source", "none"),
                        fallback_used=bool(result.get("fallback_used", False)),
                    )
        
        except CircuitBreakerOpenError as e:
            logger.warning(f"Circuit open for course sync: {e}")
            return PopulationResult(
                success=False,
                error="Course data service temporarily unavailable, please try again later",
            )
        except ExternalServiceError as e:
            logger.error(f"External service error during course sync: {e}")
            return PopulationResult(
                success=False,
                error=f"External service error: {e.user_message}",
            )
        except Exception as e:
            logger.error(f"Unexpected error ensuring course data: {e}", exc_info=True)
            return PopulationResult(
                success=False,
                error="An unexpected error occurred while fetching course data",
            )

    async def ensure_professor_data(
        self, 
        professor_name: str, 
        university: str, 
        force: bool = False
    ) -> PopulationResult:
        """
        Ensure professor data (reviews and grades) exists.
        
        Returns:
            PopulationResult with success status and any warnings
        """
        warnings: List[str] = []
        
        try:
            # Check cache for recent success
            cache_key = f"population:professor:{professor_name}:{university}"
            if not force:
                cached_result = await cache_manager.get(cache_key)
                if cached_result:
                    return PopulationResult(success=True)

            # Check if professor exists first
            professor = None
            try:
                professor = await supabase_service.get_professor_by_name(professor_name, university)
            except DataNotFoundError:
                # Professor doesn't exist yet, will be created during scrape
                logger.info(f"Professor {professor_name} not in database, will scrape")
            except DatabaseError as e:
                logger.warning(f"Error checking professor existence: {e}")
                warnings.append("Could not verify existing professor data")
            
            # If professor exists, check freshness
            if professor and not force:
                try:
                    if await data_freshness_service.is_professor_data_fresh(professor.id):
                        return PopulationResult(success=True)
                except DatabaseError:
                    pass  # Continue with scrape
            
            lock_key = f"professor:{professor_name}:{university}"
            
            async with await self._get_lock(lock_key):
                # Double check
                if professor and not force:
                    try:
                        if await data_freshness_service.is_professor_data_fresh(professor.id):
                            return PopulationResult(success=True)
                    except DatabaseError:
                        pass
                
                logger.info(f"Triggering on-demand professor scrape for {professor_name}")
                
                # 1. Scrape reviews
                scrape_result = await scrape_reviews_job(
                    professor_name=professor_name, 
                    university=university
                )
                
                if not scrape_result.get("success"):
                    error_msg = scrape_result.get("error", "Unknown scrape error")
                    logger.warning(f"Review scrape failed: {error_msg}")
                    # This is non-fatal - professor might still be usable without reviews
                    warnings.append(f"Could not fetch reviews: {error_msg}")
                
                # Refresh professor object to get ID if it was just created
                if not professor:
                    try:
                        professor = await supabase_service.get_professor_by_name(professor_name, university)
                    except DataNotFoundError:
                        # Professor still doesn't exist even after scrape attempt
                        return PopulationResult(
                            success=False,
                            warnings=warnings,
                            error=f"Professor '{professor_name}' not found at {university}",
                        )
                    except DatabaseError as e:
                        return PopulationResult(
                            success=False,
                            warnings=warnings,
                            error=f"Database error while fetching professor: {e.user_message}",
                        )
                
                # 2. Update grades
                grade_result = await update_grades_job(professor_id=professor.id)
                
                if not grade_result.get("success"):
                    # Non-fatal - grades are nice to have
                    warnings.append("Could not update grade statistics")
                
                # Success even if some operations had warnings
                await cache_manager.set(cache_key, True, ttl=60)
                
                return PopulationResult(
                    success=True,
                    warnings=warnings,
                    is_partial=len(warnings) > 0,
                )

        except CircuitBreakerOpenError as e:
            logger.warning(f"Circuit open for professor data: {e}")
            return PopulationResult(
                success=False,
                error="Professor data service temporarily unavailable, please try again later",
            )
        except ScrapingError as e:
            logger.error(f"Scraping error for professor data: {e}")
            return PopulationResult(
                success=False,
                warnings=warnings,
                error=f"Could not scrape professor data: {e.user_message}",
            )
        except ExternalServiceError as e:
            logger.error(f"External service error for professor data: {e}")
            return PopulationResult(
                success=False,
                warnings=warnings,
                error=f"External service error: {e.user_message}",
            )
        except Exception as e:
            logger.error(f"Unexpected error ensuring professor data: {e}", exc_info=True)
            return PopulationResult(
                success=False,
                warnings=warnings,
                error="An unexpected error occurred while fetching professor data",
            )

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create a lock for a specific key"""
        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]


# Singleton instance
data_population_service = DataPopulationService()
