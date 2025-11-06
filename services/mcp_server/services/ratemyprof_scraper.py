"""
RateMyProfessors scraper with ethical rate limiting
"""
import asyncio
import httpx
from typing import List, Dict, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..utils.logger import get_logger


logger = get_logger(__name__)


class RateMyProfessorsScraper:
    """Scraper for RateMyProfessors data using GraphQL API"""
    
    def __init__(self):
        self.base_url = settings.ratemyprof_base_url
        self.graphql_url = settings.ratemyprof_graphql_url
        self.headers = {
            'User-Agent': settings.scraper_user_agent,
            'Content-Type': 'application/json',
            'Authorization': 'Basic dGVzdDp0ZXN0'  # May need to update
        }
        self.request_delay = settings.scraper_request_delay
        logger.info("RateMyProfessors Scraper initialized")
    
    @retry(
        stop=stop_after_attempt(settings.scraper_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search_professor(
        self,
        professor_name: str,
        university: str
    ) -> Optional[Dict[str, Any]]:
        """Search for a professor by name and university"""
        try:
            # GraphQL query to search for professor
            query = """
            query NewSearchTeachersQuery($query: TeacherSearchQuery!) {
              newSearch {
                teachers(query: $query) {
                  edges {
                    node {
                      id
                      legacyId
                      firstName
                      lastName
                      school {
                        name
                        id
                      }
                      department
                      avgRating
                      avgDifficulty
                      numRatings
                      wouldTakeAgainPercent
                    }
                  }
                }
              }
            }
            """
            
            variables = {
                "query": {
                    "text": professor_name,
                    "schoolID": self._get_school_id(university)
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.graphql_url,
                    json={"query": query, "variables": variables},
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    teachers = data.get('data', {}).get('newSearch', {}).get('teachers', {}).get('edges', [])
                    
                    if teachers:
                        return teachers[0]['node']  # Return first match
                    return None
                else:
                    logger.error(f"RMP API error: {response.status_code}")
                    return None
        
        except Exception as e:
            logger.error(f"Error searching professor {professor_name}: {e}")
            return None
        
        finally:
            # Rate limiting
            await asyncio.sleep(self.request_delay)
    
    @retry(
        stop=stop_after_attempt(settings.scraper_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_professor_reviews(
        self,
        professor_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get reviews for a professor"""
        try:
            query = """
            query RatingsListQuery($id: ID!, $count: Int!) {
              node(id: $id) {
                ... on Teacher {
                  ratings(first: $count) {
                    edges {
                      node {
                        id
                        comment
                        class
                        date
                        difficultyRating
                        helpfulRating
                        clarityRating
                        wouldTakeAgain
                        thumbsUpTotal
                        thumbsDownTotal
                        ratingTags
                      }
                    }
                  }
                }
              }
            }
            """
            
            variables = {
                "id": professor_id,
                "count": limit
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.graphql_url,
                    json={"query": query, "variables": variables},
                    headers=self.headers,
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ratings = data.get('data', {}).get('node', {}).get('ratings', {}).get('edges', [])
                    return [edge['node'] for edge in ratings]
                else:
                    logger.error(f"RMP API error: {response.status_code}")
                    return []
        
        except Exception as e:
            logger.error(f"Error fetching reviews for professor {professor_id}: {e}")
            return []
        
        finally:
            await asyncio.sleep(self.request_delay)
    
    def _get_school_id(self, university: str) -> str:
        """Map CUNY school name to RateMyProfessors school ID"""
        school_ids = {
            "City College": "U2Nob29sLTk3OA==",
            "Hunter College": "U2Nob29sLTk5NQ==",
            "Queens College": "U2Nob29sLTEwMTE=",
            "Baruch College": "U2Nob29sLTk3Ng==",
            "Brooklyn College": "U2Nob29sLTk3OQ==",
            # Add more mappings as needed
        }
        return school_ids.get(university, "")
    
    async def scrape_professor_data(
        self,
        professor_name: str,
        university: str
    ) -> Optional[Dict[str, Any]]:
        """Complete scrape of professor data including reviews"""
        logger.info(f"Scraping data for {professor_name} at {university}")
        
        # Search for professor
        professor = await self.search_professor(professor_name, university)
        
        if not professor:
            logger.warning(f"Professor {professor_name} not found")
            return None
        
        # Get reviews
        reviews = await self.get_professor_reviews(professor['id'])
        
        return {
            'professor': professor,
            'reviews': reviews,
            'total_reviews': len(reviews)
        }


# Singleton instance
ratemyprof_scraper = RateMyProfessorsScraper()
