"""
Pytest fixtures and test utilities for CUNY Schedule Optimizer tests
"""
import pytest
import asyncio
from datetime import datetime, timedelta, time
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server.models.course import Course, CourseSection
from mcp_server.models.professor import Professor, ProfessorReview
from mcp_server.models.sync_metadata import SyncMetadata
from mcp_server.utils.cache import cache_manager, InMemoryCache
from mcp_server.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitState,
)


# ============ Time Helpers ============

def get_fresh_timestamp(ttl_seconds: int = 3600) -> datetime:
    """Get a timestamp that is within TTL (fresh data)"""
    return datetime.now() - timedelta(seconds=ttl_seconds // 2)


def get_stale_timestamp(ttl_seconds: int = 3600) -> datetime:
    """Get a timestamp that exceeds TTL (stale data)"""
    return datetime.now() - timedelta(seconds=ttl_seconds * 2)


def get_boundary_timestamp(ttl_seconds: int = 3600) -> datetime:
    """Get a timestamp exactly at TTL boundary"""
    return datetime.now() - timedelta(seconds=ttl_seconds)


# ============ Model Factory Functions ============

def create_mock_course(
    id: Optional[UUID] = None,
    course_code: str = "CSC101",
    name: str = "Introduction to Computer Science",
    credits: int = 3,
    university: str = "Baruch College",
    semester: str = "Fall 2025",
    subject_code: Optional[str] = None,
    course_number: Optional[str] = None,
    description: Optional[str] = None,
    last_scraped: Optional[datetime] = None,
    is_stale: bool = False,
    **overrides
) -> Course:
    """Factory function to create mock Course objects"""
    data = {
        "id": id or uuid4(),
        "course_code": course_code,
        "name": name,
        "credits": credits,
        "university": university,
        "semester": semester,
        "subject_code": subject_code or course_code[:3],
        "course_number": course_number or course_code[3:],
        "description": description,
        "last_scraped": last_scraped or datetime.now(),
        "is_stale": is_stale,
        "created_at": datetime.now(),
        **overrides
    }
    return Course(**data)


def create_mock_section(
    id: Optional[UUID] = None,
    course_id: Optional[UUID] = None,
    section_number: str = "001",
    professor_id: Optional[UUID] = None,
    professor_name: Optional[str] = "Dr. Smith",
    days: str = "MWF",
    start_time: Optional[time] = None,
    end_time: Optional[time] = None,
    location: str = "Room 101",
    modality: str = "In-person",
    enrolled: int = 25,
    capacity: int = 30,
    **overrides
) -> CourseSection:
    """Factory function to create mock CourseSection objects"""
    data = {
        "id": id or uuid4(),
        "course_id": course_id or uuid4(),
        "section_number": section_number,
        "professor_id": professor_id,
        "professor_name": professor_name,
        "days": days,
        "start_time": start_time or time(9, 0),
        "end_time": end_time or time(10, 15),
        "location": location,
        "modality": modality,
        "enrolled": enrolled,
        "capacity": capacity,
        "scraped_at": datetime.now(),
        "updated_at": datetime.now(),
        **overrides
    }
    return CourseSection(**data)


def create_mock_professor(
    id: Optional[UUID] = None,
    name: str = "Dr. John Smith",
    university: str = "Baruch College",
    department: Optional[str] = "Computer Science",
    ratemyprof_id: Optional[str] = None,
    average_rating: Optional[float] = 4.2,
    average_difficulty: Optional[float] = 3.1,
    review_count: Optional[int] = 50,
    grade_letter: Optional[str] = "B+",
    composite_score: Optional[int] = 85,
    last_updated: Optional[datetime] = None,
    data_source: str = "ratemyprof",
    **overrides
) -> Professor:
    """Factory function to create mock Professor objects"""
    data = {
        "id": id or uuid4(),
        "name": name,
        "university": university,
        "department": department,
        "ratemyprof_id": ratemyprof_id,
        "average_rating": average_rating,
        "average_difficulty": average_difficulty,
        "review_count": review_count,
        "grade_letter": grade_letter,
        "composite_score": composite_score,
        "last_updated": last_updated or datetime.now(),
        "data_source": data_source,
        "created_at": datetime.now(),
        **overrides
    }
    return Professor(**data)


def create_mock_review(
    id: Optional[UUID] = None,
    professor_id: Optional[UUID] = None,
    rating: float = 4.0,
    difficulty: float = 3.0,
    comment: Optional[str] = "Great professor!",
    course_code: Optional[str] = "CSC101",
    would_take_again: Optional[bool] = True,
    tags: Optional[List[str]] = None,
    sentiment_scores: Optional[Dict[str, float]] = None,
    **overrides
) -> ProfessorReview:
    """Factory function to create mock ProfessorReview objects"""
    data = {
        "id": id or uuid4(),
        "professor_id": professor_id or uuid4(),
        "rating": rating,
        "difficulty": difficulty,
        "comment": comment,
        "course_code": course_code,
        "would_take_again": would_take_again,
        "tags": tags or ["Helpful", "Clear grading"],
        "sentiment_scores": sentiment_scores,
        "scraped_at": datetime.now(),
        **overrides
    }
    return ProfessorReview(**data)


def create_mock_sync_metadata(
    id: Optional[UUID] = None,
    entity_type: str = "courses",
    semester: str = "Fall 2025",
    university: str = "Baruch College",
    last_sync: Optional[datetime] = None,
    sync_status: str = "success",
    error_message: Optional[str] = None,
    **overrides
) -> SyncMetadata:
    """Factory function to create mock SyncMetadata objects"""
    data = {
        "id": id or uuid4(),
        "entity_type": entity_type,
        "semester": semester,
        "university": university,
        "last_sync": last_sync or datetime.now(),
        "sync_status": sync_status,
        "error_message": error_message,
        "created_at": datetime.now(),
        **overrides
    }
    return SyncMetadata(**data)


# ============ Mock Service Fixtures ============

@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client with chainable query methods"""
    mock_client = MagicMock()
    
    # Setup chainable query builder
    mock_builder = MagicMock()
    mock_builder.select.return_value = mock_builder
    mock_builder.insert.return_value = mock_builder
    mock_builder.update.return_value = mock_builder
    mock_builder.delete.return_value = mock_builder
    mock_builder.upsert.return_value = mock_builder
    mock_builder.eq.return_value = mock_builder
    mock_builder.neq.return_value = mock_builder
    mock_builder.gt.return_value = mock_builder
    mock_builder.gte.return_value = mock_builder
    mock_builder.lt.return_value = mock_builder
    mock_builder.lte.return_value = mock_builder
    mock_builder.ilike.return_value = mock_builder
    mock_builder.limit.return_value = mock_builder
    
    # Default execute response
    mock_response = MagicMock()
    mock_response.data = []
    mock_builder.execute.return_value = mock_response
    
    mock_client.table.return_value = mock_builder
    
    return mock_client


@pytest.fixture
def mock_supabase_service(mock_supabase_client):
    """Create a mock SupabaseService"""
    with patch('mcp_server.services.supabase_service.supabase_service') as mock_service:
        mock_service.client = mock_supabase_client
        
        # Setup common async methods
        mock_service.get_courses_by_semester = AsyncMock(return_value=[])
        mock_service.get_course_by_code = AsyncMock(return_value=None)
        mock_service.get_sections_by_course = AsyncMock(return_value=[])
        mock_service.get_section_by_id = AsyncMock(return_value=None)
        mock_service.get_professor_by_name = AsyncMock(return_value=None)
        mock_service.get_professor_by_id = AsyncMock(return_value=None)
        mock_service.get_reviews_by_professor = AsyncMock(return_value=[])
        mock_service.get_sync_metadata = AsyncMock(return_value=None)
        mock_service.update_sync_metadata = AsyncMock(return_value=True)
        mock_service.insert_courses = AsyncMock(return_value=0)
        mock_service.insert_sections = AsyncMock(return_value=0)
        mock_service.insert_professor = AsyncMock(return_value=None)
        mock_service.insert_reviews = AsyncMock(return_value=0)
        mock_service.update_professor_grades = AsyncMock(return_value=True)
        mock_service.search_courses = AsyncMock(return_value=[])
        mock_service.health_check = AsyncMock(return_value=True)
        
        yield mock_service


@pytest.fixture
def mock_data_freshness_service():
    """Create a mock DataFreshnessService"""
    with patch('mcp_server.services.data_freshness_service.data_freshness_service') as mock_service:
        mock_service.is_course_data_fresh = AsyncMock(return_value=True)
        mock_service.is_professor_data_fresh = AsyncMock(return_value=True)
        mock_service.is_review_data_fresh = AsyncMock(return_value=True)
        mock_service.get_last_sync = AsyncMock(return_value=datetime.now())
        mock_service.mark_sync_in_progress = AsyncMock(return_value=True)
        mock_service.mark_sync_complete = AsyncMock(return_value=True)
        
        # TTL constants
        mock_service.COURSE_DATA_TTL = 7 * 24 * 3600
        mock_service.PROFESSOR_DATA_TTL = 7 * 24 * 3600
        mock_service.REVIEW_DATA_TTL = 30 * 24 * 3600
        
        yield mock_service


@pytest.fixture
def mock_data_population_service():
    """Create a mock DataPopulationService"""
    from mcp_server.services.data_population_service import PopulationResult
    
    with patch('mcp_server.services.data_population_service.data_population_service') as mock_service:
        mock_service.ensure_course_data = AsyncMock(
            return_value=PopulationResult(success=True)
        )
        mock_service.ensure_professor_data = AsyncMock(
            return_value=PopulationResult(success=True)
        )
        
        yield mock_service


@pytest.fixture
def mock_sync_courses_job():
    """Create a mock sync_courses_job"""
    with patch('mcp_server.services.data_population_service.sync_courses_job') as mock_job:
        mock_job.return_value = {"success": True, "courses_synced": 100}
        yield mock_job


@pytest.fixture
def mock_scrape_reviews_job():
    """Create a mock scrape_reviews_job"""
    with patch('mcp_server.services.data_population_service.scrape_reviews_job') as mock_job:
        mock_job.return_value = {"success": True, "reviews_scraped": 50}
        yield mock_job


@pytest.fixture
def mock_update_grades_job():
    """Create a mock update_grades_job"""
    with patch('mcp_server.services.data_population_service.update_grades_job') as mock_job:
        mock_job.return_value = {"success": True}
        yield mock_job


# ============ Cache Fixtures ============

@pytest.fixture
async def clean_cache():
    """Ensure cache is cleared before and after each test"""
    await cache_manager.clear()
    yield cache_manager
    await cache_manager.clear()


@pytest.fixture
def fresh_cache():
    """Create a fresh InMemoryCache instance for isolated testing"""
    return InMemoryCache(default_ttl=300, max_size=100)


# ============ Circuit Breaker Fixtures ============

@pytest.fixture
def fresh_circuit_breaker():
    """Create a fresh CircuitBreaker instance for isolated testing"""
    return CircuitBreaker(
        name="test_breaker",
        failure_threshold=3,
        recovery_timeout=5,
        half_open_max_calls=2
    )


@pytest.fixture
def fresh_circuit_registry():
    """Create a fresh CircuitBreakerRegistry for isolated testing"""
    return CircuitBreakerRegistry()


@pytest.fixture
async def reset_circuit_breakers():
    """Reset all global circuit breakers before/after test"""
    from mcp_server.utils.circuit_breaker import circuit_breaker_registry
    
    await circuit_breaker_registry.reset_all()
    yield
    await circuit_breaker_registry.reset_all()


# ============ Sample Data Sets ============

@pytest.fixture
def sample_courses():
    """Generate a list of sample courses"""
    return [
        create_mock_course(course_code="CSC101", name="Intro to CS"),
        create_mock_course(course_code="CSC201", name="Data Structures"),
        create_mock_course(course_code="MATH201", name="Calculus I"),
    ]


@pytest.fixture
def sample_sections(sample_courses):
    """Generate sample sections for courses"""
    sections = []
    for course in sample_courses:
        sections.extend([
            create_mock_section(
                course_id=course.id,
                section_number="001",
                professor_name="Dr. Smith",
                days="MWF",
                start_time=time(9, 0),
                end_time=time(9, 50)
            ),
            create_mock_section(
                course_id=course.id,
                section_number="002",
                professor_name="Dr. Johnson",
                days="TTh",
                start_time=time(10, 0),
                end_time=time(11, 15)
            ),
        ])
    return sections


@pytest.fixture
def sample_professors():
    """Generate a list of sample professors"""
    return [
        create_mock_professor(name="Dr. John Smith", grade_letter="A", composite_score=92),
        create_mock_professor(name="Dr. Jane Johnson", grade_letter="B+", composite_score=85),
        create_mock_professor(name="Dr. Bob Williams", grade_letter="C", composite_score=70),
    ]


@pytest.fixture
def sample_reviews(sample_professors):
    """Generate sample reviews for professors"""
    reviews = []
    for prof in sample_professors:
        reviews.extend([
            create_mock_review(professor_id=prof.id, rating=4.5, comment="Excellent!"),
            create_mock_review(professor_id=prof.id, rating=3.5, comment="Good but tough"),
        ])
    return reviews


# ============ API Test Client Fixture ============

@pytest.fixture
def test_client():
    """Create FastAPI TestClient"""
    from fastapi.testclient import TestClient
    from pathlib import Path
    
    # Import must be done here to avoid circular imports
    import sys
    # Use relative path from this file's location
    services_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(services_dir))
    
    from api_server import app
    return TestClient(app)


# ============ Async Test Helpers ============

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
