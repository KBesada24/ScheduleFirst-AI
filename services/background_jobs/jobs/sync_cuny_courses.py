"""
Background job to sync CUNY courses from Global Search
"""
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from mcp_server.services.cuny_ingestion_orchestrator import cuny_ingestion_orchestrator
from mcp_server.services.supabase_service import supabase_service
from mcp_server.utils.logger import get_logger
from mcp_server.utils.metrics import metrics_collector


logger = get_logger(__name__)


async def sync_courses_job(
    semester: Optional[str] = None, 
    university: Optional[str] = None,
    subject_code: Optional[str] = None,
    force: bool = False
) -> Dict[str, Any]:
    """
    Sync courses from CUNY Global Search
    
    Args:
        semester: Optional specific semester to sync
        university: Optional specific university to sync
        subject_code: Optional subject code to limit scraping (e.g., "CSC")
        force: Force sync even if fresh (handled by caller usually)
    """
    logger.info("=" * 60)
    logger.info(f"STARTING: CUNY Course Sync Job (Semester: {semester or 'All'})")
    logger.info("=" * 60)
    
    start_time = time.perf_counter()
    
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
        warnings: List[str] = []
        final_source = "none"
        fallback_used = False
        
        for sem in semesters:
            logger.info(f"Syncing semester: {sem}")
            
            try:
                ingestion_result = await cuny_ingestion_orchestrator.fetch_courses(
                    sem,
                    university=university,
                    subject_code=subject_code,
                )
                courses = ingestion_result.courses
                final_source = ingestion_result.source
                fallback_used = ingestion_result.fallback_used
                if ingestion_result.warnings:
                    warnings.extend(ingestion_result.warnings)

                if not ingestion_result.success and not courses:
                    raise RuntimeError(ingestion_result.error or "Course ingestion failed")
                
                # Record scraping success
                await metrics_collector.record_scraping("cuny_courses", success=True)
                
                if not courses:
                    logger.warning(f"No courses found for {sem}" +
                                    (f" at {university}" if university else ""))
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
                
                # Record scraping failure
                await metrics_collector.record_scraping("cuny_courses", success=False)
                
                # Mark as failed
                target_uni = university or "all" # This is imperfect but...
                await supabase_service.update_sync_metadata(
                    "courses", sem, target_uni, "failed", str(e)
                )
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        duration_seconds = duration_ms / 1000
        
        logger.info("=" * 60)
        logger.info("COMPLETED: CUNY Course Sync Job")
        logger.info(f"Total courses synced: {total_courses}")
        logger.info(f"Total sections synced: {total_sections}")
        logger.info(f"Duration: {duration_seconds:.2f} seconds")
        logger.info("=" * 60)
        
        # Record job execution metrics
        success = len(errors) == 0
        await metrics_collector.record_job_execution(
            job_name="sync_cuny_courses",
            success=success,
            duration_ms=duration_ms,
            details={
                "courses_synced": total_courses,
                "sections_synced": total_sections,
                "semesters": semesters,
            }
        )
        
        return {
            'success': success,
            'courses_synced': total_courses,
            'sections_synced': total_sections,
            'duration_seconds': duration_seconds,
            'errors': errors,
            'warnings': warnings,
            'source': final_source,
            'fallback_used': fallback_used,
        }
    
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"Error in course sync job: {e}", exc_info=True)
        
        # Record job failure
        await metrics_collector.record_job_execution(
            job_name="sync_cuny_courses",
            success=False,
            duration_ms=duration_ms,
            details={"error": str(e)}
        )
        
        return {
            'success': False,
            'error': str(e)
        }
    
    finally:
        # Cleanup
        cuny_ingestion_orchestrator.close()


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
