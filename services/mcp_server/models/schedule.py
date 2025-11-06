"""
Schedule-related Pydantic models
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict
from .course import CourseSection


class ScheduleConflict(BaseModel):
    """Represents a scheduling conflict"""
    conflict_type: str = Field(..., description="Type: time_overlap, travel_time, prerequisite")
    section1_id: UUID
    section2_id: Optional[UUID] = None
    description: str = Field(..., description="Human-readable conflict description")
    severity: str = Field(..., description="Severity: critical, warning, info")
    suggestion: Optional[str] = Field(None, description="Suggested resolution")


class ScheduleConstraints(BaseModel):
    """User constraints for schedule optimization"""
    # Required courses
    required_course_codes: List[str] = Field(..., description="Must-take courses")
    
    # Time preferences
    preferred_days: Optional[List[str]] = Field(None, description="Preferred days (MWF, TTh)")
    earliest_start_time: Optional[str] = Field(None, description="Earliest class time (HH:MM)")
    latest_end_time: Optional[str] = Field(None, description="Latest class time (HH:MM)")
    max_hours_per_day: Optional[int] = Field(None, ge=1, le=12, description="Max hours per day")
    
    # Campus preferences
    preferred_campuses: Optional[List[str]] = Field(None, description="Preferred campus locations")
    allow_online: bool = Field(default=True, description="Allow online courses")
    
    # Professor preferences
    min_professor_rating: Optional[float] = Field(None, ge=0, le=5, description="Min professor rating")
    prefer_high_rated_professors: bool = Field(default=True)
    
    # Course load
    min_credits: Optional[int] = Field(None, ge=1, description="Minimum credits")
    max_credits: Optional[int] = Field(None, le=21, description="Maximum credits")
    
    # Other constraints
    avoid_back_to_back_campuses: bool = Field(default=True)
    min_break_between_classes: Optional[int] = Field(default=10, description="Minutes")


class ScheduleSlot(BaseModel):
    """A single time slot in a schedule"""
    section: CourseSection
    course_code: str
    course_name: str
    professor_name: Optional[str] = None
    professor_grade: Optional[str] = None


class OptimizedSchedule(BaseModel):
    """A complete optimized schedule"""
    schedule_id: UUID = Field(default_factory=uuid4)
    slots: List[ScheduleSlot] = Field(..., description="All course sections in schedule")
    
    # Metrics
    total_credits: int = Field(..., description="Total credit hours")
    average_professor_rating: Optional[float] = Field(None, description="Average rating")
    conflicts: List[ScheduleConflict] = Field(default_factory=list)
    
    # Scoring
    preference_score: float = Field(..., ge=0, le=100, description="How well it matches preferences")
    professor_quality_score: float = Field(..., ge=0, le=100)
    time_convenience_score: float = Field(..., ge=0, le=100)
    overall_score: float = Field(..., ge=0, le=100)
    
    # Metadata
    rank: Optional[int] = Field(None, description="Ranking among all generated schedules")
    notes: Optional[str] = Field(None, description="Notes about this schedule")


class ScheduleOptimizationRequest(BaseModel):
    """Request to optimize a schedule"""
    user_id: Optional[UUID] = None
    semester: str = Field(..., description="Semester (e.g., Fall 2025)")
    constraints: ScheduleConstraints
    university: Optional[str] = Field(None, description="Primary CUNY school")
    max_results: int = Field(default=5, ge=1, le=10, description="Max schedules to return")


class ScheduleOptimizationResponse(BaseModel):
    """Response with optimized schedules"""
    schedules: List[OptimizedSchedule]
    total_generated: int
    computation_time_ms: float
    warnings: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class UserScheduleBase(BaseModel):
    """Base user schedule model"""
    name: Optional[str] = Field(None, description="User-given schedule name")
    semester: str
    sections: List[UUID] = Field(..., description="List of section IDs")
    is_active: bool = Field(default=True)


class UserScheduleCreate(UserScheduleBase):
    """Model for creating a user schedule"""
    user_id: UUID


class UserSchedule(UserScheduleBase):
    """Full user schedule model"""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True)


class UserScheduleWithDetails(UserSchedule):
    """User schedule with full section details"""
    section_details: List[ScheduleSlot]
    total_credits: int
    conflicts: List[ScheduleConflict]
