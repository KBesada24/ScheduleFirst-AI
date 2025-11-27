"""
Course-related Pydantic models
"""
from datetime import datetime, time
from typing import Optional, List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict


class CourseBase(BaseModel):
    """Base course model"""
    course_code: str = Field(..., description="Course code (e.g., CSC381)")
    subject_code: Optional[str] = Field(None, description="Subject code (e.g., CSC)")
    course_number: Optional[str] = Field(None, description="Course number (e.g., 381)")
    name: str = Field(..., description="Course name")
    credits: Optional[int] = Field(None, ge=0, le=6, description="Credit hours")
    university: str = Field(..., description="CUNY school name")
    semester: str = Field(..., description="Semester (e.g., Fall 2025)")
    description: Optional[str] = Field(None, description="Course description")


class CourseCreate(CourseBase):
    """Model for creating a new course"""
    pass


class Course(CourseBase):
    """Full course model with database fields"""
    id: UUID = Field(default_factory=uuid4)
    last_scraped: Optional[datetime] = Field(default_factory=datetime.now)
    is_stale: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True)


class CourseSectionBase(BaseModel):
    """Base course section model"""
    section_number: str = Field(..., description="Section number")
    professor_id: Optional[UUID] = Field(None, description="Professor ID")
    professor_name: Optional[str] = Field(None, description="Professor name")
    
    # Schedule details
    days: Optional[str] = Field(None, description="Days (e.g., MWF, TTh, Online)")
    start_time: Optional[time] = Field(None, description="Start time")
    end_time: Optional[time] = Field(None, description="End time")
    
    # Location
    location: Optional[str] = Field(None, description="Room/building")
    modality: Optional[str] = Field(None, description="In-person, Online, or Hybrid")
    
    # Enrollment
    enrolled: Optional[int] = Field(None, ge=0, description="Current enrollment")
    capacity: Optional[int] = Field(None, ge=0, description="Max capacity")


class CourseSectionCreate(CourseSectionBase):
    """Model for creating a new course section"""
    course_id: UUID


class CourseSection(CourseSectionBase):
    """Full course section model with database fields"""
    id: UUID = Field(default_factory=uuid4)
    course_id: UUID
    scraped_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True)


class CourseWithSections(Course):
    """Course with all its sections"""
    sections: List[CourseSection] = Field(default_factory=list)


class CourseSearchFilter(BaseModel):
    """Model for course search filters"""
    course_code: Optional[str] = None
    subject_code: Optional[str] = None
    university: Optional[str] = None
    semester: Optional[str] = None
    professor_name: Optional[str] = None
    days: Optional[str] = None
    modality: Optional[str] = None
    min_credits: Optional[int] = None
    max_credits: Optional[int] = None
    has_available_seats: Optional[bool] = None


class CourseSearchResult(BaseModel):
    """Search result with course and sections"""
    course: Course
    sections: List[CourseSection]
    total_sections: int
    available_sections: int
