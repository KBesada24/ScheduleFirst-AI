"""
Background job to sync CUNY courses from Global Search
"""
from datetime import datetime
from typing import List, Dict, Any

from ...mcp_server.services.cuny_global_search_scraper import cuny_scraper
from ...mcp_server.services.supabase_service import supabase_service
from ...mcp_server.utils.logger import get_logger


logger = get_logger(__name__)


async def sync_courses_job(
    semester: Optional[str] = None, 
    university: Optional[str] = None,
    force: bool = False
) -> Dict[str, Any]:
    """
    Sync courses from CUNY Global Search
    
    Args:
        semester: Optional specific semester to sync
        university: Optional specific university to sync (not used by scraper yet, but good for future)
        force: Force sync even if fresh (handled by caller usually)
    """
    logger.info("=" * 60)
    logger.info(f"STARTING: CUNY Course Sync Job (Semester: {semester or 'All'})")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Determine semesters to sync
        if semester:
            semesters = [semester]
        else:
            semesters = _get_semesters_to_sync()
            
        logger.info(f"Syncing {len(semesters)} semesters: {', '.join(semesters)}")
        
        total_courses = 0
        total_sections = 0
        errors = []
        
        for sem in semesters:
            logger.info(f"Syncing semester: {sem}")
            
            try:
                # Scrape courses
                # Note: cuny_scraper currently scrapes all universities for a semester
                # If we want to filter by university, we'd need to update the scraper or filter results here
                courses = await cuny_scraper.scrape_semester_courses(sem)
                
                if not courses:
                    logger.warning(f"No courses found for {sem}")
                    continue
                
                # Filter by university if specified
                if university:
                    courses = [c for c in courses if c.get('university') == university]
                    if not courses:
                        logger.info(f"No courses found for {university} in {sem}")
                        continue
                
                # Prepare data for bulk insert
                courses_data = []
                sections_data = []
                
                for course in courses:
                    # Extract sections
                    sections = course.pop('sections', [])
                    
                    courses_data.append(course)
                    
                    # Add course_id to sections (will be resolved after insert)
                    for section in sections:
                        sections_data.append(section)
                
                # Insert courses
                courses_inserted = await supabase_service.insert_courses(courses_data)
                logger.info(f"Inserted {courses_inserted} courses for {sem}")
                
                # Insert sections
                if sections_data:
                    sections_inserted = await supabase_service.insert_sections(sections_data)
                    logger.info(f"Inserted {sections_inserted} sections for {sem}")
                    total_sections += sections_inserted
                
                total_courses += courses_inserted
                
                # Update sync metadata
                # We update for the specific university if provided, or "all" (or iterate all unis?)
                # For now, if university is None, we assume we synced all universities for this semester
                target_uni = university or "all" 
                # Ideally we should update metadata for each university found in the data
                # But for simplicity/MVP:
                
                # If we synced all, we might want to mark all unis as synced? 
                # Or just use a special "all" marker? 
                # The DataFreshnessService checks specific university.
                
                # Let's extract unique universities from the data and mark them
                synced_unis = set(c.get('university') for c in courses_data)
                for uni in synced_unis:
                     await supabase_service.update_sync_metadata(
                        "courses", sem, uni, "success"
                    )
                
            except Exception as e:
                logger.error(f"Error syncing semester {sem}: {e}")
                errors.append(f"{sem}: {str(e)}")
                # Mark as failed
                target_uni = university or "all" # This is imperfect but...
                await supabase_service.update_sync_metadata(
                    "courses", sem, target_uni, "failed", str(e)
                )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("COMPLETED: CUNY Course Sync Job")
        logger.info(f"Total courses synced: {total_courses}")
        logger.info(f"Total sections synced: {total_sections}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 60)
        
        return {
            'success': len(errors) == 0,
            'courses_synced': total_courses,
            'sections_synced': total_sections,
            'duration_seconds': duration,
            'errors': errors
        }
    
    except Exception as e:
        logger.error(f"Error in course sync job: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
    
    finally:
        # Cleanup
        cuny_scraper.close()


def _get_semesters_to_sync() -> List[str]:
    """Determine which semesters to sync"""
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    semesters = []
    
    # Determine current and upcoming semesters
    if current_month < 6:  # Jan-May
        semesters.append(f"Spring {current_year}")
        semesters.append(f"Summer {current_year}")
        semesters.append(f"Fall {current_year}")
    elif current_month < 8:  # Jun-Jul
        semesters.append(f"Summer {current_year}")
        semesters.append(f"Fall {current_year}")
        semesters.append(f"Spring {current_year + 1}")
    else:  # Aug-Dec
        semesters.append(f"Fall {current_year}")
        semesters.append(f"Spring {current_year + 1}")
        semesters.append(f"Summer {current_year + 1}")
    
    return semesters
