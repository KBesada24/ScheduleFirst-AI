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
from ..config import settings
from ..services.data_population_service import data_population_service


logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("CUNY Schedule Optimizer")


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
    try:
        logger.info(f"Fetching sections for {len(course_codes)} courses")
        
        sections_data = []
        
        # Auto-populate data if needed
        # We assume all courses are for the same semester/university if provided
        # If university is not provided, we might need to handle that, but for now let's assume
        # the user wants data for the default university if not specified, or we skip population
        target_university = university or "Baruch College" # Default for now
        
        # Trigger population for this semester/university
        # This ensures we have the latest course data
        await data_population_service.ensure_course_data(semester, target_university)
        
        for course_code in course_codes:
            if not university:
                # Search across all universities
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
                logger.warning(f"Course {course_code} not found")
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
        
        return {
            'success': True,
            'semester': semester,
            'total_courses': len(sections_data),
            'courses': sections_data,
            'metadata': {
                'source': 'hybrid',
                'auto_populated': True
            }
        }
    
    except Exception as e:
        logger.error(f"Error fetching course sections: {e}")
        return {
            'success': False,
            'error': str(e),
            'courses': []
        }


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
    try:
        logger.info(f"Generating {max_schedules} optimized schedules")
        
        # Ensure data exists
        await data_population_service.ensure_course_data(semester, university)
        
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
        
        return {
            'success': True,
            'total_schedules': len(schedules_data),
            'schedules': schedules_data
        }
    
    except Exception as e:
        logger.error(f"Error generating schedules: {e}")
        return {
            'success': False,
            'error': str(e),
            'schedules': []
        }


async def _get_professor_grade_impl(
    professor_name: str,
    university: str,
    course_code: Optional[str] = None
) -> Dict:
    """
    Internal implementation for getting professor grade
    """
    try:
        logger.info(f"Fetching grade for {professor_name}")
        
        # Ensure professor data exists and is fresh
        await data_population_service.ensure_professor_data(professor_name, university)
        
        # Get professor from database
        professor = await supabase_service.get_professor_by_name(professor_name, university)
        
        if not professor:
            return {
                'success': False,
                'error': 'Could not retrieve professor data',
                'professor_name': professor_name
            }
        
        return {
            'success': True,
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
        }
    
    except Exception as e:
        logger.error(f"Error getting professor grade: {e}")
        return {
            'success': False,
            'error': str(e)
        }


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
    try:
        logger.info(f"Comparing {len(professor_names)} professors")
        
        professors_data = []
        
        for name in professor_names:
            prof_grade = await _get_professor_grade_impl(name, university, course_code)
            if prof_grade['success']:
                professors_data.append(prof_grade)
        
        if not professors_data:
            return {
                'success': False,
                'error': 'No professor data found'
            }
        
        # Sort by grade
        professors_data.sort(key=lambda p: p.get('composite_score', 0), reverse=True)
        
        # Generate recommendation
        best_prof = professors_data[0]
        recommendation = f"Based on ratings and reviews, {best_prof['professor_name']} " \
                        f"(Grade: {best_prof['grade_letter']}) is recommended."
        
        return {
            'success': True,
            'total_professors': len(professors_data),
            'professors': professors_data,
            'recommendation': recommendation,
            'course_code': course_code
        }
    
    except Exception as e:
        logger.error(f"Error comparing professors: {e}")
        return {
            'success': False,
            'error': str(e)
        }


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
    try:
        from uuid import UUID
        
        # Fetch sections
        sections = []
        for section_id in section_ids:
            section = await supabase_service.get_section_by_id(section_id)
            if section:
                sections.append(section)
            else:
                logger.warning(f"Section {section_id} not found during conflict check")
        
        # Detect conflicts
        conflicts = schedule_optimizer.detect_conflicts(sections)
        
        return {
            'success': True,
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
        }
    
    except Exception as e:
        logger.error(f"Error checking conflicts: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# Export MCP server instance
__all__ = ['mcp']
