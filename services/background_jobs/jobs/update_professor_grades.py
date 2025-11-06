"""
Background job to update professor grades based on sentiment analysis
"""
from datetime import datetime

from ...mcp_server.services.supabase_service import supabase_service
from ...mcp_server.services.sentiment_analyzer import sentiment_analyzer
from ...mcp_server.utils.logger import get_logger


logger = get_logger(__name__)


async def update_grades_job():
    """Update professor grades based on sentiment analysis of reviews"""
    logger.info("=" * 60)
    logger.info("STARTING: Professor Grades Update Job")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Get all CUNY universities
        universities = [
            "City College", "Hunter College", "Queens College", "Baruch College",
            "Brooklyn College", "Lehman College", "York College"
        ]
        
        total_updated = 0
        
        for university in universities:
            logger.info(f"Updating grades for {university}")
            
            # Get all professors
            professors = await supabase_service.get_professors_by_university(university)
            
            for professor in professors:
                try:
                    # Get reviews
                    reviews = await supabase_service.get_reviews_by_professor(professor.id)
                    
                    if not reviews or len(reviews) < 3:
                        logger.debug(f"Insufficient reviews for {professor.name}")
                        continue
                    
                    # Convert to dict format for analysis
                    reviews_dict = [
                        {
                            'comment': r.comment,
                            'rating': r.rating,
                            'difficulty': r.difficulty
                        }
                        for r in reviews
                    ]
                    
                    # Generate metrics
                    metrics = sentiment_analyzer.generate_professor_metrics(reviews_dict)
                    
                    if not metrics:
                        continue
                    
                    # Calculate composite score and grade
                    composite_score = sentiment_analyzer.calculate_composite_score(metrics)
                    grade_letter = sentiment_analyzer.score_to_grade(composite_score)
                    
                    # Calculate averages
                    avg_rating = sum(r.rating for r in reviews) / len(reviews)
                    avg_difficulty = sum(r.difficulty for r in reviews) / len(reviews)
                    
                    # Update professor
                    success = await supabase_service.update_professor_grades(
                        professor.id,
                        grade_letter,
                        composite_score,
                        avg_rating,
                        avg_difficulty,
                        len(reviews)
                    )
                    
                    if success:
                        total_updated += 1
                        logger.debug(f"Updated {professor.name}: Grade {grade_letter} ({composite_score})")
                
                except Exception as e:
                    logger.error(f"Error updating {professor.name}: {e}")
                    continue
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("COMPLETED: Professor Grades Update Job")
        logger.info(f"Professors updated: {total_updated}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 60)
        
        return {
            'success': True,
            'professors_updated': total_updated,
            'duration_seconds': duration
        }
    
    except Exception as e:
        logger.error(f"Error in grades update job: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
