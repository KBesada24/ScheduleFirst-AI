"""
Background job to scrape professor reviews from RateMyProfessors
"""
from datetime import datetime

from ...mcp_server.services.supabase_service import supabase_service
from ...mcp_server.services.ratemyprof_scraper import ratemyprof_scraper
from ...mcp_server.utils.logger import get_logger


logger = get_logger(__name__)


from typing import Optional, Dict, Any

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
    
    start_time = datetime.now()
    
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
                professors = [prof] if prof else []
                if not professors:
                    logger.warning(f"Professor {professor_name} not found in DB for {uni}")
                    # Try to scrape anyway? No, we need DB record to link reviews
                    # Actually, if we are scraping to populate, maybe we should create the prof record?
                    # For now, assume prof record exists (created by course sync)
            else:
                professors = await supabase_service.get_professors_by_university(uni)
            
            for professor in professors:
                try:
                    # Scrape reviews
                    prof_data = await ratemyprof_scraper.scrape_professor_data(
                        professor.name,
                        uni
                    )
                    
                    if not prof_data:
                        continue
                    
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
                    
                    # Update sync metadata for this professor
                    # Note: We don't have a per-professor sync metadata table yet
                    # But we update the professor's last_updated field in the model/DB
                    # We can also update the 'reviews' entity type in sync_metadata for the university
                    
                except Exception as e:
                    logger.error(f"Error scraping {professor.name}: {e}")
                    continue
            
            # Update university-level sync status
            await supabase_service.update_sync_metadata(
                "reviews", "all", uni, "success"
            )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("COMPLETED: Professor Reviews Scrape Job")
        logger.info(f"Professors scraped: {total_professors}")
        logger.info(f"Reviews collected: {total_reviews}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 60)
        
        return {
            'success': True,
            'professors_scraped': total_professors,
            'reviews_collected': total_reviews,
            'duration_seconds': duration
        }
    
    except Exception as e:
        logger.error(f"Error in reviews scrape job: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
