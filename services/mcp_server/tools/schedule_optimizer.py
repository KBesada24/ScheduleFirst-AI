"""
MCP Tools for CUNY Schedule Optimizer
FastMCP tool definitions for schedule optimization and professor evaluation
"""
from datetime import datetime
from typing import List, Dict, Optional
from fastmcp import FastMCP

from ..services.supabase_service import supabase_service
from ..services.constraint_solver import schedule_optimizer
from ..services.ratemyprof_scraper import ratemyprof_scraper
from ..services.sentiment_analyzer import sentiment_analyzer
from ..models.schedule import ScheduleConstraints, ScheduleOptimizationRequest
from ..models.professor import ProfessorGradeMetrics
from ..models.course import CourseSearchFilter
from ..utils.logger import get_logger
from ..utils.exceptions import (
    ScheduleOptimizerError,
    DataNotFoundError,
    DataStaleError,
    DatabaseError,
    CircuitBreakerOpenError,
    ScrapingError,
)
from ..config import settings
from ..services.data_population_service import data_population_service


logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("CUNY Schedule Optimizer")


def _build_response(
    success: bool,
    data: Optional[Dict] = None,
    error: Optional[str] = None,
    error_code: Optional[str] = None,
    warnings: Optional[List[str]] = None,
    suggestions: Optional[List[str]] = None,
    data_quality: str = "full",
) -> Dict:
    """
    Build a standardized response with warnings support.
    
    Args:
        success: Whether the operation succeeded
        data: Response data (merged into response if provided)
        error: Error message if failed
        error_code: Machine-readable error code
        warnings: List of warning messages
        suggestions: Actionable suggestions for errors
        data_quality: "full", "partial", "degraded", or "stale"
    """
    response = {
        "success": success,
        "warnings": warnings or [],
        "data_quality": data_quality,
    }
    
    if data:
        response.update(data)
    
    if error:
        response["error"] = error
        if error_code:
            response["error_code"] = error_code
        if suggestions:
            response["suggestions"] = suggestions
    
    return response


@mcp.tool()
async def fetch_course_sections(
    course_codes: List[str],
    semester: str,
    university: Optional[str] = None
) -> Dict:
    """
    Fetch available course sections from CUNY database
    
    Args:
        course_codes: List of course codes (e.g., ["CSC381", "MATH201"])
        semester: Semester (e.g., "Fall 2025")
        university: Optional CUNY school name
    
    Returns:
        Dictionary with course sections, professors, times, and enrollment
    """
    warnings: List[str] = []
    data_quality = "full"
    
    try:
        logger.info(f"Fetching sections for {len(course_codes)} courses")
        
        sections_data = []
        courses_not_found = []
        
        target_university = university or "Baruch College"
        
        # Trigger population for this semester/university
        population_result = await data_population_service.ensure_course_data(semester, target_university)
        if population_result.warnings:
            warnings.extend(population_result.warnings)
        if population_result.is_partial:
            data_quality = "partial"
        
        for course_code in course_codes:
            try:
                if not university:
                    courses = await supabase_service.search_courses(
                        CourseSearchFilter(
                            course_code=course_code,
                            semester=semester
                        )
                    )
                    course = courses[0] if courses else None
                else:
                    course = await supabase_service.get_course_by_code(
                        course_code, semester, university
                    )
                
                if not course:
                    courses_not_found.append(course_code)
                    continue
                
                # Get sections
                sections = await supabase_service.get_sections_by_course(course.id)
                
                sections_data.append({
                    'course_code': course.course_code,
                    'course_name': course.name,
                    'credits': course.credits,
                    'university': course.university,
                    'total_sections': len(sections),
                    'sections': [
                        {
                            'id': str(section.id),
                            'section_number': section.section_number,
                            'professor_name': section.professor_name,
                            'days': section.days,
                            'start_time': section.start_time.isoformat() if section.start_time else None,
                            'end_time': section.end_time.isoformat() if section.end_time else None,
                            'location': section.location,
                            'modality': section.modality,
                            'enrolled': section.enrolled,
                            'capacity': section.capacity,
                            'seats_available': (section.capacity - section.enrolled) if section.capacity and section.enrolled else None
                        }
                        for section in sections
                    ]
                })
            except DataNotFoundError:
                courses_not_found.append(course_code)
            except DatabaseError as e:
                logger.warning(f"Database error fetching {course_code}: {e}")
                warnings.append(f"Could not fetch {course_code}: database error")
        
        # Add warning for courses not found
        if courses_not_found:
            warnings.append(f"Courses not found: {', '.join(courses_not_found)}")
            if len(courses_not_found) == len(course_codes):
                data_quality = "degraded"
        
        return _build_response(
            success=True,
            data={
                'semester': semester,
                'total_courses': len(sections_data),
                'courses': sections_data,
                'metadata': {
                    'source': 'hybrid',
                    'auto_populated': True
                }
            },
            warnings=warnings,
            data_quality=data_quality,
        )
    
    except CircuitBreakerOpenError as e:
        logger.warning(f"Circuit breaker open: {e}")
        return _build_response(
            success=False,
            error=e.user_message,
            error_code=e.code,
            suggestions=e.suggestions,
            data={"courses": []},
        )
    except DatabaseError as e:
        logger.error(f"Database error fetching course sections: {e}")
        return _build_response(
            success=False,
            error=e.user_message,
            error_code=e.code,
            suggestions=e.suggestions,
            data={"courses": []},
        )
    except Exception as e:
        logger.error(f"Error fetching course sections: {e}", exc_info=True)
        return _build_response(
            success=False,
            error="An unexpected error occurred while fetching courses",
            error_code="INTERNAL_ERROR",
            data={"courses": []},
        )


@mcp.tool()
async def generate_optimized_schedule(
    required_courses: List[str],
    semester: str,
    university: str,
    preferred_days: Optional[List[str]] = None,
    earliest_start_time: Optional[str] = None,
    latest_end_time: Optional[str] = None,
    min_professor_rating: Optional[float] = None,
    max_schedules: int = 5
) -> Dict:
    """
    Generate optimized course schedules based on requirements and preferences
    
    Args:
        required_courses: List of required course codes
        semester: Semester (e.g., "Fall 2025")
        university: CUNY school name
        preferred_days: Preferred days (e.g., ["MWF", "TTh"])
        earliest_start_time: Earliest desired class time (HH:MM)
        latest_end_time: Latest desired class time (HH:MM)
        min_professor_rating: Minimum professor rating (0-5)
        max_schedules: Maximum number of schedules to return
    
    Returns:
        Dictionary with optimized schedules ranked by preference score
    """
    warnings: List[str] = []
    data_quality = "full"
    
    try:
        logger.info(f"Generating {max_schedules} optimized schedules")
        
        # Ensure data exists
        population_result = await data_population_service.ensure_course_data(semester, university)
        if population_result.warnings:
            warnings.extend(population_result.warnings)
        if population_result.is_partial:
            data_quality = "partial"
        
        # Create constraints
        constraints = ScheduleConstraints(
            required_course_codes=required_courses,
            preferred_days=preferred_days,
            earliest_start_time=earliest_start_time,
            latest_end_time=latest_end_time,
            min_professor_rating=min_professor_rating,
            max_hours_per_day=None,
            preferred_campuses=None,
            min_credits=None,
            max_credits=None
        )
        
        # Generate schedules
        schedules = await schedule_optimizer.generate_optimized_schedules(
            required_courses=required_courses,
            semester=semester,
            university=university,
            constraints=constraints,
            max_results=max_schedules
        )
        
        if not schedules:
            warnings.append("No valid schedules found with current constraints")
        
        # Convert to dict format
        schedules_data = [
            {
                'rank': schedule.rank,
                'total_credits': schedule.total_credits,
                'overall_score': round(schedule.overall_score, 1),
                'preference_score': round(schedule.preference_score, 1),
                'professor_quality_score': round(schedule.professor_quality_score, 1),
                'time_convenience_score': round(schedule.time_convenience_score, 1),
                'average_professor_rating': schedule.average_professor_rating,
                'conflicts': [
                    {
                        'type': c.conflict_type,
                        'severity': c.severity,
                        'description': c.description,
                        'suggestion': c.suggestion
                    }
                    for c in schedule.conflicts
                ],
                'classes': [
                    {
                        'course_code': slot.course_code,
                        'course_name': slot.course_name,
                        'section_id': str(slot.section.id),
                        'professor': slot.professor_name,
                        'professor_grade': slot.professor_grade,
                        'days': slot.section.days,
                        'time': f"{slot.section.start_time} - {slot.section.end_time}",
                        'location': slot.section.location
                    }
                    for slot in schedule.slots
                ]
            }
            for schedule in schedules
        ]
        
        return _build_response(
            success=True,
            data={
                'total_schedules': len(schedules_data),
                'schedules': schedules_data,
            },
            warnings=warnings,
            data_quality=data_quality,
        )
    
    except CircuitBreakerOpenError as e:
        logger.warning(f"Circuit breaker open during schedule generation: {e}")
        return _build_response(
            success=False,
            error=e.user_message,
            error_code=e.code,
            suggestions=e.suggestions,
            data={"schedules": []},
        )
    except DatabaseError as e:
        logger.error(f"Database error generating schedules: {e}")
        return _build_response(
            success=False,
            error=e.user_message,
            error_code=e.code,
            suggestions=e.suggestions,
            data={"schedules": []},
        )
    except Exception as e:
        logger.error(f"Error generating schedules: {e}", exc_info=True)
        return _build_response(
            success=False,
            error="An unexpected error occurred while generating schedules",
            error_code="INTERNAL_ERROR",
            data={"schedules": []},
        )


async def _get_professor_grade_impl(
    professor_name: str,
    university: str,
    course_code: Optional[str] = None
) -> Dict:
    """
    Internal implementation for getting professor grade
    """
    warnings: List[str] = []
    data_quality = "full"
    
    try:
        logger.info(f"Fetching grade for {professor_name}")
        
        # Ensure professor data exists and is fresh
        population_result = await data_population_service.ensure_professor_data(professor_name, university)
        if population_result.warnings:
            warnings.extend(population_result.warnings)
        if population_result.is_partial:
            data_quality = "partial"
        
        if not population_result.success:
            return _build_response(
                success=False,
                error=population_result.error or "Could not fetch professor data",
                error_code="POPULATION_ERROR",
                warnings=warnings,
                data={"professor_name": professor_name},
            )
        
        # Get professor from database
        professor = await supabase_service.get_professor_by_name(professor_name, university)
        
        return _build_response(
            success=True,
            data={
                'professor_name': professor.name,
                'university': professor.university,
                'grade_letter': professor.grade_letter,
                'composite_score': professor.composite_score,
                'average_rating': professor.average_rating,
                'average_difficulty': professor.average_difficulty,
                'review_count': professor.review_count,
                'last_updated': professor.last_updated.isoformat() if professor.last_updated else None,
                'metadata': {
                    'source': 'hybrid',
                    'auto_populated': True
                }
            },
            warnings=warnings,
            data_quality=data_quality,
        )
    
    except DataNotFoundError as e:
        logger.warning(f"Professor not found: {professor_name}")
        return _build_response(
            success=False,
            error=e.user_message,
            error_code=e.code,
            suggestions=e.suggestions,
            warnings=warnings,
            data={"professor_name": professor_name},
        )
    except CircuitBreakerOpenError as e:
        logger.warning(f"Circuit breaker open: {e}")
        return _build_response(
            success=False,
            error=e.user_message,
            error_code=e.code,
            suggestions=e.suggestions,
            data={"professor_name": professor_name},
        )
    except DatabaseError as e:
        logger.error(f"Database error getting professor grade: {e}")
        return _build_response(
            success=False,
            error=e.user_message,
            error_code=e.code,
            suggestions=e.suggestions,
            data={"professor_name": professor_name},
        )
    except Exception as e:
        logger.error(f"Error getting professor grade: {e}", exc_info=True)
        return _build_response(
            success=False,
            error="An unexpected error occurred",
            error_code="INTERNAL_ERROR",
            data={"professor_name": professor_name},
        )


@mcp.tool()
async def get_professor_grade(
    professor_name: str,
    university: str,
    course_code: Optional[str] = None
) -> Dict:
    """
    Get AI-generated grade for a professor based on RateMyProfessors reviews
    
    Args:
        professor_name: Full name of professor
        university: CUNY school name
        course_code: Optional course code to filter ratings
    
    Returns:
        Dictionary with professor grade (A-F), metrics, and review analysis
    """
    return await _get_professor_grade_impl(professor_name, university, course_code)


@mcp.tool()
async def compare_professors(
    professor_names: List[str],
    university: str,
    course_code: Optional[str] = None
) -> Dict:
    """
    Compare multiple professors and get AI recommendation
    
    Args:
        professor_names: List of professor names to compare
        university: CUNY school name
        course_code: Optional course code to filter ratings
    
    Returns:
        Comparison data with metrics and AI recommendation
    """
    warnings: List[str] = []
    data_quality = "full"
    
    try:
        logger.info(f"Comparing {len(professor_names)} professors")
        
        professors_data = []
        professors_failed = []
        
        for name in professor_names:
            prof_grade = await _get_professor_grade_impl(name, university, course_code)
            if prof_grade['success']:
                professors_data.append(prof_grade)
                # Collect any warnings from individual professor fetches
                if prof_grade.get('warnings'):
                    warnings.extend(prof_grade['warnings'])
            else:
                professors_failed.append(name)
        
        if professors_failed:
            warnings.append(f"Could not fetch data for: {', '.join(professors_failed)}")
        
        if not professors_data:
            return _build_response(
                success=False,
                error="No professor data could be retrieved",
                error_code="DATA_NOT_FOUND",
                warnings=warnings,
                suggestions=["Check professor names are spelled correctly", "Try searching for professors individually"],
            )
        
        # Determine data quality
        if len(professors_failed) > 0:
            data_quality = "partial" if len(professors_data) > 0 else "degraded"
        
        # Sort by grade
        professors_data.sort(key=lambda p: p.get('composite_score', 0), reverse=True)
        
        # Generate recommendation
        best_prof = professors_data[0]
        recommendation = f"Based on ratings and reviews, {best_prof['professor_name']} " \
                        f"(Grade: {best_prof['grade_letter']}) is recommended."
        
        return _build_response(
            success=True,
            data={
                'total_professors': len(professors_data),
                'professors': professors_data,
                'recommendation': recommendation,
                'course_code': course_code,
            },
            warnings=warnings,
            data_quality=data_quality,
        )
    
    except CircuitBreakerOpenError as e:
        logger.warning(f"Circuit breaker open during professor comparison: {e}")
        return _build_response(
            success=False,
            error=e.user_message,
            error_code=e.code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        logger.error(f"Error comparing professors: {e}", exc_info=True)
        return _build_response(
            success=False,
            error="An unexpected error occurred while comparing professors",
            error_code="INTERNAL_ERROR",
        )


@mcp.tool()
async def check_schedule_conflicts(
    section_ids: List[str]
) -> Dict:
    """
    Check for conflicts in a set of course sections
    
    Args:
        section_ids: List of section IDs (UUIDs)
    
    Returns:
        Dictionary with detected conflicts
    """
    warnings: List[str] = []
    
    try:
        from uuid import UUID
        
        # Fetch sections
        sections = []
        sections_not_found = []
        
        for section_id in section_ids:
            try:
                section = await supabase_service.get_section_by_id(section_id)
                sections.append(section)
            except DataNotFoundError:
                sections_not_found.append(section_id)
                logger.warning(f"Section {section_id} not found during conflict check")
            except DatabaseError as e:
                warnings.append(f"Could not fetch section {section_id[:8]}...")
                logger.warning(f"Database error fetching section {section_id}: {e}")
        
        if sections_not_found:
            warnings.append(f"{len(sections_not_found)} section(s) not found")
        
        if not sections:
            return _build_response(
                success=False,
                error="No valid sections found to check",
                error_code="DATA_NOT_FOUND",
                warnings=warnings,
            )
        
        # Detect conflicts
        conflicts = schedule_optimizer.detect_conflicts(sections)
        
        return _build_response(
            success=True,
            data={
                'total_conflicts': len(conflicts),
                'conflicts': [
                    {
                        'type': c.conflict_type,
                        'severity': c.severity,
                        'description': c.description,
                        'suggestion': c.suggestion
                    }
                    for c in conflicts
                ]
            },
            warnings=warnings,
            data_quality="partial" if warnings else "full",
        )
    
    except CircuitBreakerOpenError as e:
        logger.warning(f"Circuit breaker open: {e}")
        return _build_response(
            success=False,
            error=e.user_message,
            error_code=e.code,
            suggestions=e.suggestions,
        )
    except DatabaseError as e:
        logger.error(f"Database error checking conflicts: {e}")
        return _build_response(
            success=False,
            error=e.user_message,
            error_code=e.code,
            suggestions=e.suggestions,
        )
    except Exception as e:
        logger.error(f"Error checking conflicts: {e}", exc_info=True)
        return _build_response(
            success=False,
            error="An unexpected error occurred while checking conflicts",
            error_code="INTERNAL_ERROR",
        )


# Export MCP server instance
__all__ = ['mcp']
