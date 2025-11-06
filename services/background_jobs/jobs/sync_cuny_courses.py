"""
Background job to sync CUNY courses from Global Search
"""
from datetime import datetime
from typing import List, Dict, Any

from ...mcp_server.services.cuny_global_search_scraper import cuny_scraper
from ...mcp_server.services.supabase_service import supabase_service
from ...mcp_server.utils.logger import get_logger


logger = get_logger(__name__)


async def sync_courses_job():
    """Sync courses from CUNY Global Search"""
    logger.info("=" * 60)
    logger.info("STARTING: CUNY Course Sync Job")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Determine semesters to sync
        semesters = _get_semesters_to_sync()
        logger.info(f"Syncing {len(semesters)} semesters: {', '.join(semesters)}")
        
        total_courses = 0
        total_sections = 0
        
        for semester in semesters:
            logger.info(f"Syncing semester: {semester}")
            
            # Scrape courses
            courses = await cuny_scraper.scrape_semester_courses(semester)
            
            if not courses:
                logger.warning(f"No courses found for {semester}")
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
            logger.info(f"Inserted {courses_inserted} courses for {semester}")
            
            # Insert sections
            if sections_data:
                sections_inserted = await supabase_service.insert_sections(sections_data)
                logger.info(f"Inserted {sections_inserted} sections for {semester}")
                total_sections += sections_inserted
            
            total_courses += courses_inserted
            
            # Update sync timestamp
            await supabase_service.update_sync_timestamp(semester)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("COMPLETED: CUNY Course Sync Job")
        logger.info(f"Total courses synced: {total_courses}")
        logger.info(f"Total sections synced: {total_sections}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 60)
        
        return {
            'success': True,
            'courses_synced': total_courses,
            'sections_synced': total_sections,
            'duration_seconds': duration
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
