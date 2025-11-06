"""
Background job to scrape professor reviews from RateMyProfessors
"""
from datetime import datetime

from ...mcp_server.services.supabase_service import supabase_service
from ...mcp_server.services.ratemyprof_scraper import ratemyprof_scraper
from ...mcp_server.utils.logger import get_logger


logger = get_logger(__name__)


async def scrape_reviews_job():
    """Scrape professor reviews from RateMyProfessors"""
    logger.info("=" * 60)
    logger.info("STARTING: Professor Reviews Scrape Job")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Get all CUNY universities
        universities = [
            "City College", "Hunter College", "Queens College", "Baruch College",
            "Brooklyn College", "Lehman College", "York College"
        ]
        
        total_professors = 0
        total_reviews = 0
        
        for university in universities:
            logger.info(f"Scraping reviews for {university}")
            
            # Get all professors from this university
            professors = await supabase_service.get_professors_by_university(university)
            
            for professor in professors:
                try:
                    # Scrape reviews
                    prof_data = await ratemyprof_scraper.scrape_professor_data(
                        professor.name,
                        university
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
                
                except Exception as e:
                    logger.error(f"Error scraping {professor.name}: {e}")
                    continue
        
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
