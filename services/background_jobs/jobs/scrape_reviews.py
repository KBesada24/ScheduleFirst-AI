"""
Background job to scrape professor reviews from RateMyProfessors
"""
import time
from datetime import datetime
from typing import Optional, Dict, Any

from mcp_server.services.supabase_service import supabase_service
from mcp_server.services.ratemyprof_scraper import ratemyprof_scraper
from mcp_server.utils.logger import get_logger
from mcp_server.utils.metrics import metrics_collector


logger = get_logger(__name__)


async def scrape_reviews_job(
    professor_name: Optional[str] = None,
    university: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scrape professor reviews from RateMyProfessors
    
    Args:
        professor_name: Optional specific professor to scrape
        university: Optional specific university (required if professor_name is provided)
    """
    logger.info("=" * 60)
    logger.info(f"STARTING: Professor Reviews Scrape Job (Prof: {professor_name or 'All'})")
    logger.info("=" * 60)
    
    start_time = time.perf_counter()
    
    try:
        # Determine universities to scrape
        if university:
            universities = [university]
        else:
            universities = [
                "City College", "Hunter College", "Queens College", "Baruch College",
                "Brooklyn College", "Lehman College", "York College"
            ]
        
        total_professors = 0
        total_reviews = 0
        
        for uni in universities:
            logger.info(f"Scraping reviews for {uni}")
            
            # Get professors
            if professor_name and university == uni:
                # If specific professor requested
                prof = await supabase_service.get_professor_by_name(professor_name, uni)
                
                if prof:
                    professors = [prof]
                else:
                    # Professor not in DB, try to scrape and create
                    logger.info(f"Professor {professor_name} not found in DB, attempting to scrape and create")
                    try:
                        # Scrape professor data
                        prof_data = await ratemyprof_scraper.scrape_professor_data(
                            professor_name,
                            uni
                        )
                        
                        if prof_data:
                            # Record scraping success only when data is retrieved
                            await metrics_collector.record_scraping("ratemyprof", success=True)
                            
                            # Create new professor
                            # Create new professor
                            from mcp_server.models.professor import ProfessorCreate
                            prof_info = prof_data['professor']
                            
                            new_prof = await supabase_service.insert_professor(
                                ProfessorCreate(
                                    name=professor_name,
                                    university=uni,
                                    department=prof_info.get('department', 'Unknown'),
                                    ratemyprof_id=prof_info.get('legacyId'),
                                    average_rating=prof_info.get('avgRating'),
                                    average_difficulty=prof_info.get('avgDifficulty'),
                                    review_count=prof_info.get('numRatings'),
                                    grade_letter=None,
                                    composite_score=None
                                )
                            )
                            
                            if new_prof:
                                logger.info(f"Created new professor record for {professor_name}")
                                professors = [new_prof]
                            else:
                                logger.error(f"Failed to create professor record for {professor_name}")
                                professors = []
                        else:
                            logger.warning(f"Professor {professor_name} not found on RateMyProfessors")
                            professors = []
                    except Exception as e:
                        logger.error(f"Error scraping/creating professor {professor_name}: {e}")
                        await metrics_collector.record_scraping("ratemyprof", success=False)
                        professors = []
            else:
                professors = await supabase_service.get_professors_by_university(uni)
            
            for professor in professors:
                try:
                    # Scrape reviews (if we just created the prof, we technically already scraped, 
                    # but ratemyprof_scraper might not cache the full response or we might need to re-parse.
                    # Ideally we should pass the already scraped data if available, but for simplicity/robustness
                    # we'll call scrape again (it should be cached by the scraper service if implemented, 
                    # or we can optimize later). 
                    # Actually, let's just call scrape again to keep the loop clean.
                    
                    prof_data = await ratemyprof_scraper.scrape_professor_data(
                        professor.name,
                        uni
                    )
                    
                    if not prof_data:
                        continue
                    
                    # Record scraping success only after confirming valid data
                    await metrics_collector.record_scraping("ratemyprof", success=True)
                    
                    reviews = prof_data['reviews']
                    
                    # Prepare review data
                    reviews_data = []
                    for review in reviews:
                        reviews_data.append({
                            'professor_id': str(professor.id),
                            'rating': review.get('clarityRating', 0),
                            'difficulty': review.get('difficultyRating', 0),
                            'comment': review.get('comment', ''),
                            'course_code': review.get('class', ''),
                            'would_take_again': review.get('wouldTakeAgain'),
                            'tags': review.get('ratingTags', []),
                            'scraped_at': datetime.now().isoformat()
                        })
                    
                    # Insert reviews
                    inserted = await supabase_service.insert_reviews(reviews_data)
                    total_reviews += inserted
                    
                    total_professors += 1
                    logger.debug(f"Scraped {len(reviews)} reviews for {professor.name}")
                    
                except Exception as e:
                    logger.error(f"Error scraping {professor.name}: {e}")
                    await metrics_collector.record_scraping("ratemyprof", success=False)
                    continue
            
            # Update university-level sync status
            await supabase_service.update_sync_metadata(
                "reviews", "all", uni, "success"
            )
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        duration_seconds = duration_ms / 1000
        
        logger.info("=" * 60)
        logger.info("COMPLETED: Professor Reviews Scrape Job")
        logger.info(f"Professors scraped: {total_professors}")
        logger.info(f"Reviews collected: {total_reviews}")
        logger.info(f"Duration: {duration_seconds:.2f} seconds")
        logger.info("=" * 60)
        
        # Record job execution metrics
        await metrics_collector.record_job_execution(
            job_name="scrape_reviews",
            success=True,
            duration_ms=duration_ms,
            details={
                "professors_scraped": total_professors,
                "reviews_collected": total_reviews,
            }
        )
        
        return {
            'success': True,
            'professors_scraped': total_professors,
            'reviews_collected': total_reviews,
            'duration_seconds': duration_seconds
        }
    
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"Error in reviews scrape job: {e}", exc_info=True)
        
        # Record job failure
        await metrics_collector.record_job_execution(
            job_name="scrape_reviews",
            success=False,
            duration_ms=duration_ms,
            details={"error": str(e)}
        )
        
        return {
            'success': False,
            'error': str(e)
        }
