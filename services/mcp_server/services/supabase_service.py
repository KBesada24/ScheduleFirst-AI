"""
Supabase database service for CUNY Schedule Optimizer
Handles all database operations via Supabase client
"""
from typing import List, Optional, Dict, Any, cast
from uuid import UUID
from datetime import datetime

from supabase import create_client, Client
from postgrest.exceptions import APIError

from ..config import settings
from ..models.course import Course, CourseSection, CourseCreate, CourseSectionCreate, CourseSearchFilter
from ..models.professor import Professor, ProfessorReview, ProfessorCreate, ProfessorReviewCreate
from ..models.schedule import UserSchedule, UserScheduleCreate
from ..utils.logger import get_logger


logger = get_logger(__name__)


class SupabaseService:
    """Service for interacting with Supabase PostgreSQL database"""
    
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        logger.info("Supabase client initialized")
    
    # ============ Course Operations ============
    
    async def get_courses_by_semester(self, semester: str, university: Optional[str] = None) -> List[Course]:
        """Get all courses for a given semester"""
        try:
            query = self.client.table("courses").select("*").eq("semester", semester)
            
            if university:
                query = query.eq("university", university)
            
            response = query.execute()
            courses = cast(List[Dict[str, Any]], response.data)
            return [Course(**course) for course in courses]
        
        except APIError as e:
            logger.error(f"Error fetching courses: {e}")
            return []
    
    async def get_course_by_code(self, course_code: str, semester: str, university: str) -> Optional[Course]:
        """Get a specific course by code"""
        try:
            response = self.client.table("courses").select("*").eq(
                "course_code", course_code
            ).eq("semester", semester).eq("university", university).execute()
            
            if response.data:
                # Type hint to help Pylance understand the structure
                course_data = cast(Dict[str, Any], response.data[0])
                return Course(**course_data)
            return None
        
        except APIError as e:
            logger.error(f"Error fetching course {course_code}: {e}")
            return None
    
    async def insert_course(self, course: CourseCreate) -> Optional[Course]:
        """Insert a new course"""
        try:
            response = self.client.table("courses").insert(
                course.model_dump(exclude_none=True)
            ).execute()
            
            if response.data:
                logger.info(f"Inserted course: {course.course_code}")
                course_data = cast(Dict[str, Any], response.data[0])
                return Course(**course_data)
            return None
        
        except APIError as e:
            logger.error(f"Error inserting course: {e}")
            return None
    
    async def insert_courses(self, courses: List[Dict[str, Any]]) -> int:
        """Bulk insert courses"""
        try:
            response = self.client.table("courses").upsert(
                courses,
                on_conflict="course_code,university,semester"
            ).execute()
            
            count = len(response.data) if response.data else 0
            logger.info(f"Inserted/updated {count} courses")
            return count
        
        except APIError as e:
            logger.error(f"Error bulk inserting courses: {e}")
            return 0
    
    async def search_courses(self, filters: CourseSearchFilter) -> List[Course]:
        """Search courses with filters"""
        try:
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
            
            response = query.execute()
            courses_data = cast(List[Dict[str, Any]], response.data)
            return [Course(**course) for course in courses_data]
        
        except APIError as e:
            logger.error(f"Error searching courses: {e}")
            return []
    
    # ============ Course Section Operations ============
    
    async def get_sections_by_course(self, course_id: UUID) -> List[CourseSection]:
        """Get all sections for a course"""
        try:
            response = self.client.table("course_sections").select("*").eq(
                "course_id", str(course_id)
            ).execute()
            
            sections_data = cast(List[Dict[str, Any]], response.data)
            return [CourseSection(**section) for section in sections_data]
        
        except APIError as e:
            logger.error(f"Error fetching sections for course {course_id}: {e}")
            return []
    
    async def insert_section(self, section: CourseSectionCreate) -> Optional[CourseSection]:
        """Insert a new course section"""
        try:
            data = section.model_dump(exclude_none=True)
            data['course_id'] = str(data['course_id'])
            
            response = self.client.table("course_sections").insert(data).execute()
            
            if response.data:
                section_data = cast(Dict[str, Any], response.data[0])
                return CourseSection(**section_data)
            return None
        
        except APIError as e:
            logger.error(f"Error inserting section: {e}")
            return None
    
    async def insert_sections(self, sections: List[Dict[str, Any]]) -> int:
        """Bulk insert course sections"""
        try:
            response = self.client.table("course_sections").upsert(
                sections,
                on_conflict="course_id,section_number"
            ).execute()
            
            count = len(response.data) if response.data else 0
            logger.info(f"Inserted/updated {count} sections")
            return count
        
        except APIError as e:
            logger.error(f"Error bulk inserting sections: {e}")
            return 0
    
    async def get_sections_by_professor(self, professor_name: str, semester: str) -> List[CourseSection]:
        """Get all sections taught by a professor in a semester"""
        try:
            response = self.client.table("course_sections").select(
                "*"
            ).ilike("professor_name", f"%{professor_name}%").execute()
            
            sections_data = cast(List[Dict[str, Any]], response.data)
            return [CourseSection(**section) for section in sections_data]
        
        except APIError as e:
            logger.error(f"Error fetching sections for professor {professor_name}: {e}")
            return []
    
    # ============ Professor Operations ============
    
    async def get_professor_by_name(self, name: str, university: str) -> Optional[Professor]:
        """Get professor by name and university"""
        try:
            response = self.client.table("professors").select("*").ilike(
                "name", f"%{name}%"
            ).eq("university", university).execute()
            
            if response.data:
                prof_data = cast(Dict[str, Any], response.data[0])
                return Professor(**prof_data)
            return None
        
        except APIError as e:
            logger.error(f"Error fetching professor {name}: {e}")
            return None
    
    async def get_professor_by_id(self, professor_id: UUID) -> Optional[Professor]:
        """Get professor by ID"""
        try:
            response = self.client.table("professors").select("*").eq(
                "id", str(professor_id)
            ).execute()
            
            if response.data:
                prof_data = cast(Dict[str, Any], response.data[0])
                return Professor(**prof_data)
            return None
        
        except APIError as e:
            logger.error(f"Error fetching professor {professor_id}: {e}")
            return None
    
    async def insert_professor(self, professor: ProfessorCreate) -> Optional[Professor]:
        """Insert a new professor"""
        try:
            response = self.client.table("professors").insert(
                professor.model_dump(exclude_none=True)
            ).execute()
            
            if response.data:
                logger.info(f"Inserted professor: {professor.name}")
                prof_data = cast(Dict[str, Any], response.data[0])
                return Professor(**prof_data)
            return None
        
        except APIError as e:
            logger.error(f"Error inserting professor: {e}")
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
        try:
            self.client.table("professors").update({
                "grade_letter": grade_letter,
                "composite_score": composite_score,
                "average_rating": average_rating,
                "average_difficulty": average_difficulty,
                "review_count": review_count,
                "last_updated": datetime.now().isoformat()
            }).eq("id", str(professor_id)).execute()
            
            logger.info(f"Updated grades for professor {professor_id}")
            return True
        
        except APIError as e:
            logger.error(f"Error updating professor grades: {e}")
            return False
    
    async def get_professors_by_university(self, university: str) -> List[Professor]:
        """Get all professors from a university"""
        try:
            response = self.client.table("professors").select("*").eq(
                "university", university
            ).execute()
            
            profs_data = cast(List[Dict[str, Any]], response.data)
            return [Professor(**prof) for prof in profs_data]
        
        except APIError as e:
            logger.error(f"Error fetching professors for {university}: {e}")
            return []
    
    # ============ Professor Review Operations ============
    
    async def get_reviews_by_professor(self, professor_id: UUID) -> List[ProfessorReview]:
        """Get all reviews for a professor"""
        try:
            response = self.client.table("professor_reviews").select("*").eq(
                "professor_id", str(professor_id)
            ).execute()
            
            reviews_data = cast(List[Dict[str, Any]], response.data)
            return [ProfessorReview(**review) for review in reviews_data]
        
        except APIError as e:
            logger.error(f"Error fetching reviews for professor {professor_id}: {e}")
            return []
    
    async def insert_review(self, review: ProfessorReviewCreate) -> Optional[ProfessorReview]:
        """Insert a new professor review"""
        try:
            data = review.model_dump(exclude_none=True)
            data['professor_id'] = str(data['professor_id'])
            
            response = self.client.table("professor_reviews").insert(data).execute()
            
            if response.data:
                review_data = cast(Dict[str, Any], response.data[0])
                return ProfessorReview(**review_data)
            return None
        
        except APIError as e:
            logger.error(f"Error inserting review: {e}")
            return None
    
    async def insert_reviews(self, reviews: List[Dict[str, Any]]) -> int:
        """Bulk insert professor reviews"""
        try:
            response = self.client.table("professor_reviews").upsert(reviews).execute()
            
            count = len(response.data) if response.data else 0
            logger.info(f"Inserted/updated {count} reviews")
            return count
        
        except APIError as e:
            logger.error(f"Error bulk inserting reviews: {e}")
            return 0
    
    # ============ User Schedule Operations ============
    
    async def get_user_schedules(self, user_id: UUID) -> List[UserSchedule]:
        """Get all schedules for a user"""
        try:
            response = self.client.table("user_schedules").select("*").eq(
                "user_id", str(user_id)
            ).execute()
            
            schedules_data = cast(List[Dict[str, Any]], response.data)
            return [UserSchedule(**schedule) for schedule in schedules_data]
        
        except APIError as e:
            logger.error(f"Error fetching schedules for user {user_id}: {e}")
            return []
    
    async def insert_schedule(self, schedule: UserScheduleCreate) -> Optional[UserSchedule]:
        """Insert a new user schedule"""
        try:
            data = schedule.model_dump(exclude_none=True)
            data['user_id'] = str(data['user_id'])
            data['sections'] = [str(s) for s in data['sections']]
            
            response = self.client.table("user_schedules").insert(data).execute()
            
            if response.data:
                schedule_data = cast(Dict[str, Any], response.data[0])
                return UserSchedule(**schedule_data)
            return None
        
        except APIError as e:
            logger.error(f"Error inserting schedule: {e}")
            return None
    
    async def delete_schedule(self, schedule_id: UUID) -> bool:
        """Delete a user schedule"""
        try:
            self.client.table("user_schedules").delete().eq(
                "id", str(schedule_id)
            ).execute()
            
            logger.info(f"Deleted schedule {schedule_id}")
            return True
        
        except APIError as e:
            logger.error(f"Error deleting schedule: {e}")
            return False
    
    # ============ Utility Operations ============
    
    async def update_sync_timestamp(self, semester: str) -> bool:
        """Update the last sync timestamp for a semester"""
        try:
            self.client.table("sync_logs").insert({
                "semester": semester,
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            }).execute()
            
            return True
        
        except APIError as e:
            logger.error(f"Error updating sync timestamp: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            # Simple query to test connection
            self.client.table("courses").select("id").limit(1).execute()
            return True
        
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Singleton instance
supabase_service = SupabaseService()
