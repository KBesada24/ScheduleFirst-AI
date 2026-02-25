"""
Supabase database service for CUNY Schedule Optimizer
Handles all database operations via Supabase client
"""
from typing import List, Optional, Dict, Any, cast
from uuid import UUID
from datetime import datetime, timedelta
import inspect

from supabase import create_client, Client
from postgrest.exceptions import APIError

from ..config import settings
from ..models.course import Course, CourseSection, CourseCreate, CourseSectionCreate, CourseSearchFilter
from ..models.professor import Professor, ProfessorReview, ProfessorCreate, ProfessorReviewCreate
from ..models.schedule import UserSchedule, UserScheduleCreate
from ..models.sync_metadata import SyncMetadata
from ..utils.logger import get_logger
from ..utils.cache import cache_manager
from ..utils.exceptions import DatabaseError, DataNotFoundError
from ..utils.circuit_breaker import supabase_breaker


logger = get_logger(__name__)


class SupabaseService:
    """Service for interacting with Supabase PostgreSQL database"""
    
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        logger.info("Supabase client initialized")
    
    def _handle_api_error(self, e: APIError, operation: str, context: Dict[str, Any] = None) -> None:
        """
        Convert Supabase APIError to custom DatabaseError with context.
        
        Args:
            e: The original APIError
            operation: Description of the operation that failed
            context: Additional context about the operation
        """
        error_message = str(e)
        is_retryable = True
        
        # Determine if error is retryable based on error type
        if "timeout" in error_message.lower():
            is_retryable = True
        elif "permission" in error_message.lower() or "unauthorized" in error_message.lower():
            is_retryable = False
        elif "not found" in error_message.lower():
            is_retryable = False
        
        logger.error(
            f"Database error during {operation}: {error_message}",
            extra={"context": context or {}, "is_retryable": is_retryable}
        )
        
        raise DatabaseError(
            operation=operation,
            reason=error_message,
            is_retryable=is_retryable,
            details=context
        )

    async def _execute_query(self, query: Any) -> Any:
        """Execute a PostgREST query builder for both sync and async test doubles."""
        result = query.execute()
        if inspect.isawaitable(result):
            return await result
        return result
    
    # ============ Course Operations ============
    
    @cache_manager.cached(prefix="courses:list", ttl=300)
    async def get_courses_by_semester(self, semester: str, university: Optional[str] = None) -> List[Course]:
        """Get all courses for a given semester"""
        context = {"semester": semester, "university": university}
        try:
            async def _execute():
                query = self.client.table("courses").select("*").eq("semester", semester)
                if university:
                    query = query.eq("university", university)
                return query.execute()
            
            response = await supabase_breaker.call(_execute)
            courses = cast(List[Dict[str, Any]], response.data)
            return [Course(**course) for course in courses]
        
        except APIError as e:
            self._handle_api_error(e, "get_courses_by_semester", context)
            return []  # Unreachable but satisfies type checker
    
    @cache_manager.cached(prefix="courses:detail", ttl=300)
    async def get_course_by_code(self, course_code: str, semester: str, university: str) -> Optional[Course]:
        """Get a specific course by code"""
        context = {"course_code": course_code, "semester": semester, "university": university}
        try:
            async def _execute():
                return self.client.table("courses").select("*").eq(
                    "course_code", course_code
                ).eq("semester", semester).eq("university", university).execute()
            
            response = await supabase_breaker.call(_execute)
            
            if response.data:
                course_data = cast(Dict[str, Any], response.data[0])
                return Course(**course_data)
            return None
        
        except APIError as e:
            self._handle_api_error(e, "get_course_by_code", context)
            return None
    
    async def insert_course(self, course: CourseCreate) -> Optional[Course]:
        """Insert a new course"""
        context = {"course_code": course.course_code, "university": course.university}
        try:
            async def _execute():
                return self.client.table("courses").insert(
                    course.model_dump(exclude_none=True)
                ).execute()
            
            response = await supabase_breaker.call(_execute)
            
            if response.data:
                logger.info(f"Inserted course: {course.course_code}")
                course_data = cast(Dict[str, Any], response.data[0])
                return Course(**course_data)
            return None
        
        except APIError as e:
            self._handle_api_error(e, "insert_course", context)
            return None
    
    async def insert_courses(self, courses: List[Dict[str, Any]]) -> int:
        """Bulk insert courses"""
        context = {"course_count": len(courses)}
        try:
            async def _execute():
                return self.client.table("courses").upsert(
                    courses,
                    on_conflict="course_code,university,semester"
                ).execute()
            
            response = await supabase_breaker.call(_execute)
            
            count = len(response.data) if response.data else 0
            logger.info(f"Inserted/updated {count} courses")
            return count
        
        except APIError as e:
            self._handle_api_error(e, "insert_courses", context)
            return 0
    
    async def search_courses(self, filters: CourseSearchFilter) -> List[Course]:
        """Search courses with filters"""
        context = {"filters": filters.model_dump(exclude_none=True)}
        try:
            async def _execute():
                query = self.client.table("courses").select("*")
                
                if filters.course_code:
                    query = query.ilike("course_code", f"%{filters.course_code}%")
                if filters.subject_code:
                    query = query.eq("subject_code", filters.subject_code)
                if filters.university:
                    query = query.eq("university", filters.university)
                if filters.semester:
                    query = query.eq("semester", filters.semester)
                if filters.min_credits is not None:
                    query = query.gte("credits", filters.min_credits)
                if filters.max_credits is not None:
                    query = query.lte("credits", filters.max_credits)
                
                return query.execute()
            
            response = await supabase_breaker.call(_execute)
            courses_data = cast(List[Dict[str, Any]], response.data)
            return [Course(**course) for course in courses_data]
        
        except APIError as e:
            self._handle_api_error(e, "search_courses", context)
            return []
    
    # ============ Course Section Operations ============
    
    async def get_sections_by_course(self, course_id: UUID) -> List[CourseSection]:
        """Get all sections for a course"""
        context = {"course_id": str(course_id)}
        try:
            async def _execute():
                return self.client.table("course_sections").select("*").eq(
                    "course_id", str(course_id)
                ).execute()
            
            response = await supabase_breaker.call(_execute)
            sections_data = cast(List[Dict[str, Any]], response.data)
            return [CourseSection(**section) for section in sections_data]
        
        except APIError as e:
            self._handle_api_error(e, "get_sections_by_course", context)
            return []
    
    async def insert_section(self, section: CourseSectionCreate) -> Optional[CourseSection]:
        """Insert a new course section"""
        context = {"course_id": str(section.course_id), "section_number": section.section_number}
        try:
            data = section.model_dump(exclude_none=True)
            data['course_id'] = str(data['course_id'])
            
            async def _execute():
                return self.client.table("course_sections").insert(data).execute()
            
            response = await supabase_breaker.call(_execute)
            
            if response.data:
                section_data = cast(Dict[str, Any], response.data[0])
                return CourseSection(**section_data)
            return None
        
        except APIError as e:
            self._handle_api_error(e, "insert_section", context)
            return None
    
    async def insert_sections(self, sections: List[Dict[str, Any]]) -> int:
        """Bulk insert course sections"""
        context = {"section_count": len(sections)}
        try:
            async def _execute():
                return self.client.table("course_sections").upsert(
                    sections,
                    on_conflict="course_id,section_number"
                ).execute()
            
            response = await supabase_breaker.call(_execute)
            
            count = len(response.data) if response.data else 0
            logger.info(f"Inserted/updated {count} sections")
            return count
        
        except APIError as e:
            self._handle_api_error(e, "insert_sections", context)
            return 0
    
    async def get_sections_by_professor(self, professor_name: str, semester: str) -> List[CourseSection]:
        """Get all sections taught by a professor in a semester"""
        context = {"professor_name": professor_name, "semester": semester}
        try:
            async def _execute():
                return self.client.table("course_sections").select(
                    "*"
                ).ilike("professor_name", f"%{professor_name}%").execute()
            
            response = await supabase_breaker.call(_execute)
            sections_data = cast(List[Dict[str, Any]], response.data)
            return [CourseSection(**section) for section in sections_data]
        
        except APIError as e:
            self._handle_api_error(e, "get_sections_by_professor", context)
            return []

    async def get_section_by_id(self, section_id: str) -> Optional[CourseSection]:
        """Get a course section by ID"""
        context = {"section_id": section_id}
        try:
            async def _execute():
                return self.client.table("course_sections").select("*").eq(
                    "id", section_id
                ).execute()
            
            response = await supabase_breaker.call(_execute)
            
            if response.data:
                section_data = cast(Dict[str, Any], response.data[0])
                return CourseSection(**section_data)
            return None
        
        except APIError as e:
            self._handle_api_error(e, "get_section_by_id", context)
            return None
    
    # ============ Professor Operations ============
    
    @cache_manager.cached(prefix="professors:name", ttl=300)
    async def get_professor_by_name(self, name: str, university: str) -> Optional[Professor]:
        """Get professor by name and university"""
        context = {"name": name, "university": university}
        try:
            async def _execute():
                return self.client.table("professors").select("*").ilike(
                    "name", f"%{name}%"
                ).eq("university", university).execute()
            
            response = await supabase_breaker.call(_execute)
            
            if response.data:
                prof_data = cast(Dict[str, Any], response.data[0])
                return Professor(**prof_data)
            return None
        
        except APIError as e:
            self._handle_api_error(e, "get_professor_by_name", context)
            return None
    
    @cache_manager.cached(prefix="professors:id", ttl=300)
    async def get_professor_by_id(self, professor_id: UUID) -> Optional[Professor]:
        """Get professor by ID"""
        context = {"professor_id": str(professor_id)}
        try:
            async def _execute():
                return self.client.table("professors").select("*").eq(
                    "id", str(professor_id)
                ).execute()
            
            response = await supabase_breaker.call(_execute)
            
            if response.data:
                prof_data = cast(Dict[str, Any], response.data[0])
                return Professor(**prof_data)
            return None
        
        except APIError as e:
            self._handle_api_error(e, "get_professor_by_id", context)
            return None
    
    async def insert_professor(self, professor: ProfessorCreate) -> Optional[Professor]:
        """Insert a new professor"""
        context = {"name": professor.name, "university": professor.university}
        try:
            async def _execute():
                return self.client.table("professors").insert(
                    professor.model_dump(exclude_none=True)
                ).execute()
            
            response = await supabase_breaker.call(_execute)
            
            if response.data:
                logger.info(f"Inserted professor: {professor.name}")
                prof_data = cast(Dict[str, Any], response.data[0])
                return Professor(**prof_data)
            return None
        
        except APIError as e:
            self._handle_api_error(e, "insert_professor", context)
            return None
    
    async def update_professor_grades(
        self,
        professor_id: UUID,
        grade_letter: str,
        composite_score: int,
        average_rating: float,
        average_difficulty: float,
        review_count: int
    ) -> bool:
        """Update professor grades and metrics"""
        context = {"professor_id": str(professor_id), "grade_letter": grade_letter}
        try:
            async def _execute():
                return self.client.table("professors").update({
                    "grade_letter": grade_letter,
                    "composite_score": composite_score,
                    "average_rating": average_rating,
                    "average_difficulty": average_difficulty,
                    "review_count": review_count,
                    "last_updated": datetime.now().isoformat()
                }).eq("id", str(professor_id)).execute()
            
            await supabase_breaker.call(_execute)
            logger.info(f"Updated grades for professor {professor_id}")
            return True
        
        except APIError as e:
            self._handle_api_error(e, "update_professor_grades", context)
            return False
    
    async def get_professors_by_university(self, university: str) -> List[Professor]:
        """Get all professors from a university"""
        context = {"university": university}
        try:
            async def _execute():
                return self.client.table("professors").select("*").eq(
                    "university", university
                ).execute()
            
            response = await supabase_breaker.call(_execute)
            profs_data = cast(List[Dict[str, Any]], response.data)
            return [Professor(**prof) for prof in profs_data]
        
        except APIError as e:
            self._handle_api_error(e, "get_professors_by_university", context)
            return []
    
    # ============ Professor Review Operations ============
    
    @cache_manager.cached(prefix="reviews:list", ttl=300)
    async def get_reviews_by_professor(self, professor_id: UUID) -> List[ProfessorReview]:
        """Get all reviews for a professor"""
        context = {"professor_id": str(professor_id)}
        try:
            async def _execute():
                return self.client.table("professor_reviews").select("*").eq(
                    "professor_id", str(professor_id)
                ).execute()
            
            response = await supabase_breaker.call(_execute)
            reviews_data = cast(List[Dict[str, Any]], response.data)
            return [ProfessorReview(**review) for review in reviews_data]
        
        except APIError as e:
            self._handle_api_error(e, "get_reviews_by_professor", context)
            return []
    
    async def insert_review(self, review: ProfessorReviewCreate) -> Optional[ProfessorReview]:
        """Insert a new professor review"""
        context = {"professor_id": str(review.professor_id)}
        try:
            data = review.model_dump(exclude_none=True)
            data['professor_id'] = str(data['professor_id'])
            
            async def _execute():
                return self.client.table("professor_reviews").insert(data).execute()
            
            response = await supabase_breaker.call(_execute)
            
            if response.data:
                review_data = cast(Dict[str, Any], response.data[0])
                return ProfessorReview(**review_data)
            return None
        
        except APIError as e:
            self._handle_api_error(e, "insert_review", context)
            return None
    
    async def insert_reviews(self, reviews: List[Dict[str, Any]]) -> int:
        """Bulk insert professor reviews"""
        context = {"review_count": len(reviews)}
        try:
            async def _execute():
                return self.client.table("professor_reviews").upsert(reviews).execute()
            
            response = await supabase_breaker.call(_execute)
            
            count = len(response.data) if response.data else 0
            logger.info(f"Inserted/updated {count} reviews")
            return count
        
        except APIError as e:
            self._handle_api_error(e, "insert_reviews", context)
            return 0
    
    # ============ User Schedule Operations ============
    
    async def get_user_schedules(self, user_id: UUID) -> List[UserSchedule]:
        """Get all schedules for a user"""
        context = {"user_id": str(user_id)}
        try:
            async def _execute():
                return self.client.table("user_schedules").select("*").eq(
                    "user_id", str(user_id)
                ).execute()
            
            response = await supabase_breaker.call(_execute)
            schedules_data = cast(List[Dict[str, Any]], response.data)
            return [UserSchedule(**schedule) for schedule in schedules_data]
        
        except APIError as e:
            self._handle_api_error(e, "get_user_schedules", context)
            return []
    
    async def insert_schedule(self, schedule: UserScheduleCreate) -> Optional[UserSchedule]:
        """Insert a new user schedule"""
        context = {"user_id": str(schedule.user_id), "name": schedule.name}
        try:
            data = schedule.model_dump(exclude_none=True)
            data['user_id'] = str(data['user_id'])
            data['sections'] = [str(s) for s in data['sections']]
            
            async def _execute():
                return self.client.table("user_schedules").insert(data).execute()
            
            response = await supabase_breaker.call(_execute)
            
            if response.data:
                schedule_data = cast(Dict[str, Any], response.data[0])
                return UserSchedule(**schedule_data)
            return None
        
        except APIError as e:
            self._handle_api_error(e, "insert_schedule", context)
            return None
    
    async def delete_schedule(self, schedule_id: UUID) -> bool:
        """Delete a user schedule"""
        context = {"schedule_id": str(schedule_id)}
        try:
            async def _execute():
                return self.client.table("user_schedules").delete().eq(
                    "id", str(schedule_id)
                ).execute()
            
            await supabase_breaker.call(_execute)
            logger.info(f"Deleted schedule {schedule_id}")
            return True
        
        except APIError as e:
            self._handle_api_error(e, "delete_schedule", context)
            return False
    
    # ============ Utility Operations ============
    
    async def update_sync_timestamp(self, semester: str) -> bool:
        """Update the last sync timestamp for a semester"""
        # Deprecated: Use update_sync_metadata instead
        context = {"semester": semester}
        try:
            async def _execute():
                return self.client.table("sync_logs").insert({
                    "semester": semester,
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed"
                }).execute()
            
            await supabase_breaker.call(_execute)
            return True
        except APIError as e:
            self._handle_api_error(e, "update_sync_timestamp", context)
            return False

    # ============ Sync Metadata Operations ============

    @cache_manager.cached(prefix="sync:metadata", ttl=60)
    async def get_sync_metadata(
        self, 
        entity_type: str, 
        semester: str, 
        university: str
    ) -> Optional[SyncMetadata]:
        """Get sync metadata record"""
        context = {"entity_type": entity_type, "semester": semester, "university": university}
        try:
            async def _execute():
                query = self.client.table("sync_metadata").select("*").eq(
                    "entity_type", entity_type
                ).eq("semester", semester).eq("university", university)
                return await self._execute_query(query)
            
            response = await supabase_breaker.call(_execute)
            if inspect.isawaitable(response):
                response = await response
            
            if response.data:
                data = cast(Dict[str, Any], response.data[0])
                return SyncMetadata(**data)
            return None
        except APIError as e:
            self._handle_api_error(e, "get_sync_metadata", context)
            return None

    async def update_sync_metadata(
        self,
        entity_type: str,
        semester: str,
        university: str,
        status: str,
        error: Optional[str] = None
    ) -> bool:
        """Update or create sync metadata record"""
        context = {"entity_type": entity_type, "semester": semester, "university": university, "status": status}
        try:
            data = {
                "entity_type": entity_type,
                "semester": semester,
                "university": university,
                "sync_status": status,
                "last_sync": datetime.now().isoformat(),
                "error_message": error
            }
            
            # Try to find existing first to get ID
            try:
                existing = await self.get_sync_metadata(entity_type, semester, university)
            except DatabaseError as e:
                raise DatabaseError(
                    operation="update_sync_metadata",
                    reason=(e.details or {}).get("reason"),
                    is_retryable=e.is_retryable,
                    details=context,
                )
            
            if existing:
                async def _execute():
                    query = self.client.table("sync_metadata").update(data).eq("id", str(existing.id))
                    return await self._execute_query(query)
            else:
                async def _execute():
                    query = self.client.table("sync_metadata").insert(data)
                    return await self._execute_query(query)
            
            response = await supabase_breaker.call(_execute)
            if inspect.isawaitable(response):
                await response
            return True
        except DatabaseError:
            raise
        except APIError as e:
            self._handle_api_error(e, "update_sync_metadata", context)
            return False

    async def get_stale_entities(self, entity_type: str, ttl_seconds: int) -> List[Dict[str, Any]]:
        """Find stale sync records"""
        context = {"entity_type": entity_type, "ttl_seconds": ttl_seconds}
        try:
            cutoff = datetime.now() - timedelta(seconds=ttl_seconds)
            
            async def _execute():
                query = self.client.table("sync_metadata").select("*").eq(
                    "entity_type", entity_type
                ).lt("last_sync", cutoff.isoformat())
                return await self._execute_query(query)
            
            response = await supabase_breaker.call(_execute)
            if inspect.isawaitable(response):
                response = await response
            return cast(List[Dict[str, Any]], response.data)
        except APIError as e:
            self._handle_api_error(e, "get_stale_entities", context)
            return []
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            async def _execute():
                return self.client.table("courses").select("id").limit(1).execute()
            
            # Don't use circuit breaker for health check - we want to know actual status
            await _execute()
            return True
        
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Singleton instance
supabase_service = SupabaseService()
