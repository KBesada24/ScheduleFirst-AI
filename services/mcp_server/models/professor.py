"""
Professor-related Pydantic models
"""
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict


class ProfessorBase(BaseModel):
    """Base professor model"""
    name: str = Field(..., description="Professor full name")
    ratemyprof_id: Optional[str] = Field(None, description="RateMyProfessors ID")
    university: str = Field(..., description="CUNY school name")
    department: Optional[str] = Field(None, description="Department")
    
    # Rating metrics
    average_rating: Optional[float] = Field(None, ge=0, le=5, description="Average rating (0-5)")
    average_difficulty: Optional[float] = Field(None, ge=0, le=5, description="Average difficulty (0-5)")
    review_count: Optional[int] = Field(None, ge=0, description="Number of reviews")
    
    # AI-generated grade
    grade_letter: Optional[str] = Field(None, pattern="^[A-F][+-]?$", description="Letter grade (A-F)")
    composite_score: Optional[int] = Field(None, ge=0, le=100, description="Composite score (0-100)")


class ProfessorCreate(ProfessorBase):
    """Model for creating a new professor"""
    pass


class Professor(ProfessorBase):
    """Full professor model with database fields"""
    id: UUID = Field(default_factory=uuid4)
    last_updated: Optional[datetime] = Field(None)
    created_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True)


class ProfessorReviewBase(BaseModel):
    """Base professor review model"""
    rating: float = Field(..., ge=0, le=5, description="Overall rating")
    difficulty: float = Field(..., ge=0, le=5, description="Difficulty rating")
    comment: Optional[str] = Field(None, description="Review comment")
    course_code: Optional[str] = Field(None, description="Course reviewed")
    would_take_again: Optional[bool] = Field(None, description="Would take again")
    tags: List[str] = Field(default_factory=list, description="Review tags")
    
    # Sentiment analysis results
    sentiment_scores: Optional[Dict[str, float]] = Field(None, description="Aspect sentiment scores")
    # Keys: teaching_clarity, grading_fairness, engagement, accessibility, class_difficulty


class ProfessorReviewCreate(ProfessorReviewBase):
    """Model for creating a new review"""
    professor_id: UUID


class ProfessorReview(ProfessorReviewBase):
    """Full professor review model"""
    id: UUID = Field(default_factory=uuid4)
    professor_id: UUID
    scraped_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(from_attributes=True)


class ProfessorWithReviews(Professor):
    """Professor with all reviews"""
    reviews: List[ProfessorReview] = Field(default_factory=list)


class ProfessorGradeMetrics(BaseModel):
    """Detailed metrics for professor grading"""
    overall_grade: str = Field(..., description="Letter grade (A-F)")
    composite_score: int = Field(..., ge=0, le=100, description="Overall score")
    
    # Aspect scores
    teaching_clarity_score: float = Field(..., ge=0, le=100)
    grading_fairness_score: float = Field(..., ge=0, le=100)
    engagement_score: float = Field(..., ge=0, le=100)
    accessibility_score: float = Field(..., ge=0, le=100)
    
    # Metadata
    review_count: int = Field(..., ge=0)
    average_rating: float = Field(..., ge=0, le=5)
    average_difficulty: float = Field(..., ge=0, le=5)
    would_take_again_percent: Optional[float] = Field(None, ge=0, le=100)
    
    # Top tags
    top_positive_tags: List[str] = Field(default_factory=list)
    top_negative_tags: List[str] = Field(default_factory=list)
    
    # Confidence
    confidence: float = Field(..., ge=0, le=1, description="Confidence score based on data quality")


class ProfessorComparison(BaseModel):
    """Comparison of multiple professors"""
    professors: List[Professor]
    metrics: List[ProfessorGradeMetrics]
    recommendation: Optional[str] = Field(None, description="AI recommendation")
    course_code: Optional[str] = Field(None, description="Course being compared for")
