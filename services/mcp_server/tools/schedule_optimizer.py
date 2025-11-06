"""
MCP Tools for CUNY Schedule Optimizer
FastMCP tool definitions for schedule optimization and professor evaluation
"""
from typing import List, Dict, Optional
from fastmcp import FastMCP

from ..services.supabase_service import supabase_service
from ..services.constraint_solver import schedule_optimizer
from ..services.ratemyprof_scraper import ratemyprof_scraper
from ..services.sentiment_analyzer import sentiment_analyzer
from ..models.schedule import ScheduleConstraints, ScheduleOptimizationRequest
from ..models.professor import ProfessorGradeMetrics
from ..utils.logger import get_logger
from ..config import settings


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
        
        for course_code in course_codes:
            # Get course
            if not university:
                # Search across all universities
                courses = await supabase_service.search_courses({
                    'course_code': course_code,
                    'semester': semester
                })
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
            'courses': sections_data
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
        
        # Create constraints
        constraints = ScheduleConstraints(
            required_course_codes=required_courses,
            preferred_days=preferred_days,
            earliest_start_time=earliest_start_time,
            latest_end_time=latest_end_time,
            min_professor_rating=min_professor_rating
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
    try:
        logger.info(f"Fetching grade for {professor_name}")
        
        # Check if professor exists in database
        professor = await supabase_service.get_professor_by_name(professor_name, university)
        
        # If not in DB or data is stale, scrape new data
        if not professor or (professor.last_updated and 
                            (datetime.now() - professor.last_updated).days > 7):
            logger.info("Scraping fresh professor data from RateMyProfessors")
            
            # Scrape professor data
            prof_data = await ratemyprof_scraper.scrape_professor_data(
                professor_name, university
            )
            
            if not prof_data:
                return {
                    'success': False,
                    'error': 'Professor not found on RateMyProfessors',
                    'professor_name': professor_name
                }
            
            # Analyze reviews with sentiment analysis
            reviews = prof_data['reviews']
            metrics = sentiment_analyzer.generate_professor_metrics(reviews)
            composite_score = sentiment_analyzer.calculate_composite_score(metrics)
            grade_letter = sentiment_analyzer.score_to_grade(composite_score)
            
            # Update or create professor in database
            prof_info = prof_data['professor']
            if professor:
                # Update existing
                await supabase_service.update_professor_grades(
                    professor.id,
                    grade_letter,
                    composite_score,
                    prof_info.get('avgRating', 0),
                    prof_info.get('avgDifficulty', 0),
                    prof_info.get('numRatings', 0)
                )
            else:
                # Create new
                from ..models.professor import ProfessorCreate
                professor = await supabase_service.insert_professor(
                    ProfessorCreate(
                        name=professor_name,
                        university=university,
                        ratemyprof_id=prof_info.get('legacyId'),
                        average_rating=prof_info.get('avgRating'),
                        average_difficulty=prof_info.get('avgDifficulty'),
                        review_count=prof_info.get('numRatings'),
                        grade_letter=grade_letter,
                        composite_score=composite_score
                    )
                )
        
        if not professor:
            return {
                'success': False,
                'error': 'Could not retrieve professor data'
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
            'last_updated': professor.last_updated.isoformat() if professor.last_updated else None
        }
    
    except Exception as e:
        logger.error(f"Error getting professor grade: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@mcp.tool()
async def compare_professors(
    professor_names: List[str],
    university: str,
    course_code: Optional[str] = None
) -> Dict:
    """
    Compare multiple professors side-by-side
    
    Args:
        professor_names: List of professor names to compare
        university: CUNY school name
        course_code: Optional course code for context
    
    Returns:
        Comparison data with metrics and AI recommendation
    """
    try:
        logger.info(f"Comparing {len(professor_names)} professors")
        
        professors_data = []
        
        for name in professor_names:
            prof_grade = await get_professor_grade(name, university, course_code)
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
            # TODO: Implement get_section_by_id in supabase_service
            pass
        
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
