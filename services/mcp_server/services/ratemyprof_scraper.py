"""
RateMyProfessors scraper with ethical rate limiting, circuit breaker, and structured errors
"""
import asyncio
import httpx
from typing import List, Dict, Optional, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from ..config import settings
from ..utils.logger import get_logger
from ..utils.exceptions import (
    ScrapingError,
    RateLimitError,
    DataNotFoundError,
    ExternalServiceError,
)
from ..utils.circuit_breaker import ratemyprof_breaker as rmp_breaker


logger = get_logger(__name__)


class RateMyProfessorsScraper:
    """Scraper for RateMyProfessors data using GraphQL API with resilience patterns"""
    
    def __init__(self):
        self.base_url = settings.ratemyprof_base_url
        self.graphql_url = settings.ratemyprof_graphql_url
        self.headers = {
            'User-Agent': settings.scraper_user_agent,
            'Content-Type': 'application/json',
            'Authorization': 'Basic dGVzdDp0ZXN0'  # May need to update
        }
        self.request_delay = settings.scraper_request_delay
        logger.info("RateMyProfessors Scraper initialized with circuit breaker")
    
    def _handle_http_error(self, status_code: int, operation: str) -> None:
        """Handle HTTP error responses with appropriate exceptions"""
        if status_code == 429:
            raise RateLimitError(
                service="RateMyProfessors",
                retry_after=60,  # Default 60 seconds
            )
        elif status_code == 403:
            raise ScrapingError(
                source="RateMyProfessors",
                reason=f"Access forbidden during {operation} - may need auth update",
            )
        elif status_code >= 500:
            raise ExternalServiceError(
                service="RateMyProfessors",
                operation=operation,
                details={"status_code": status_code},
            )
        else:
            raise ScrapingError(
                source="RateMyProfessors",
                reason=f"HTTP {status_code} during {operation}",
            )
    
    @rmp_breaker.protected
    @retry(
        stop=stop_after_attempt(settings.scraper_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, log_level=20),  # INFO level
        reraise=True,
    )
    async def search_professor(
        self,
        professor_name: str,
        university: str
    ) -> Dict[str, Any]:
        """
        Search for a professor by name and university.
        
        Raises:
            DataNotFoundError: If professor not found
            ScrapingError: If scraping fails
            RateLimitError: If rate limited
            ExternalServiceError: If RMP service is down
        """
        operation = f"search_professor({professor_name}, {university})"
        
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
            
            school_id = self._get_school_id(university)
            if not school_id:
                raise ScrapingError(
                    source="RateMyProfessors",
                    reason=f"Unknown university: {university}",
                )
            
            variables = {
                "query": {
                    "text": professor_name,
                    "schoolID": school_id
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.graphql_url,
                    json={"query": query, "variables": variables},
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    self._handle_http_error(response.status_code, operation)
                
                data = response.json()
                
                # Check for GraphQL errors
                if "errors" in data:
                    raise ScrapingError(
                        source="RateMyProfessors",
                        reason=f"GraphQL error: {data['errors']}",
                    )
                
                teachers = (
                    data.get('data', {})
                    .get('newSearch', {})
                    .get('teachers', {})
                    .get('edges', [])
                )
                
                if not teachers:
                    raise DataNotFoundError(
                        entity_type="professor",
                        identifier=professor_name,
                        details={"search_criteria": {"university": university}},
                    )
                
                logger.info(
                    f"Found professor {professor_name}",
                    extra={"matches": len(teachers), "university": university}
                )
                return teachers[0]['node']
        
        except (DataNotFoundError, ScrapingError, RateLimitError, ExternalServiceError):
            raise
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout during {operation}: {e}")
            raise ExternalServiceError(
                service="RateMyProfessors",
                operation=operation,
                details={"error": "timeout"},
            )
        except httpx.NetworkError as e:
            logger.warning(f"Network error during {operation}: {e}")
            raise ExternalServiceError(
                service="RateMyProfessors",
                operation=operation,
                details={"error": "network"},
            )
        except Exception as e:
            logger.error(f"Unexpected error in {operation}: {e}", exc_info=True)
            raise ScrapingError(
                source="RateMyProfessors",
                reason=str(e),
            )
        finally:
            # Rate limiting - always sleep between requests
            await asyncio.sleep(self.request_delay)
    
    @rmp_breaker.protected
    @retry(
        stop=stop_after_attempt(settings.scraper_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, log_level=20),
        reraise=True,
    )
    async def get_professor_reviews(
        self,
        professor_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get reviews for a professor.
        
        Raises:
            ScrapingError: If scraping fails
            RateLimitError: If rate limited
            ExternalServiceError: If RMP service is down
        """
        operation = f"get_professor_reviews({professor_id})"
        
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
                
                if response.status_code != 200:
                    self._handle_http_error(response.status_code, operation)
                
                data = response.json()
                
                # Check for GraphQL errors
                if "errors" in data:
                    raise ScrapingError(
                        source="RateMyProfessors",
                        reason=f"GraphQL error: {data['errors']}",
                    )
                
                ratings = (
                    data.get('data', {})
                    .get('node', {})
                    .get('ratings', {})
                    .get('edges', [])
                )
                
                reviews = [edge['node'] for edge in ratings]
                logger.info(
                    f"Fetched {len(reviews)} reviews for professor",
                    extra={"professor_id": professor_id, "limit": limit}
                )
                return reviews
        
        except (ScrapingError, RateLimitError, ExternalServiceError):
            raise
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout during {operation}: {e}")
            raise ExternalServiceError(
                service="RateMyProfessors",
                operation=operation,
                details={"error": "timeout"},
            )
        except httpx.NetworkError as e:
            logger.warning(f"Network error during {operation}: {e}")
            raise ExternalServiceError(
                service="RateMyProfessors",
                operation=operation,
                details={"error": "network"},
            )
        except Exception as e:
            logger.error(f"Unexpected error in {operation}: {e}", exc_info=True)
            raise ScrapingError(
                source="RateMyProfessors",
                reason=str(e),
            )
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
            "Lehman College": "U2Nob29sLTk5Ng==",
            "John Jay College": "U2Nob29sLTk5NA==",
            "Medgar Evers College": "U2Nob29sLTEwMDA=",
            "College of Staten Island": "U2Nob29sLTk4MQ==",
            "York College": "U2Nob29sLTEwMTY=",
        }
        return school_ids.get(university, "")
    
    async def scrape_professor_data(
        self,
        professor_name: str,
        university: str
    ) -> Dict[str, Any]:
        """
        Complete scrape of professor data including reviews.
        
        Returns:
            Dict with professor info and reviews
            
        Raises:
            DataNotFoundError: If professor not found
            ScrapingError: If scraping fails
            RateLimitError: If rate limited
            ExternalServiceError: If RMP service is down
        """
        logger.info(
            f"Scraping data for {professor_name} at {university}",
            extra={"professor": professor_name, "university": university}
        )
        
        # Search for professor (raises DataNotFoundError if not found)
        professor = await self.search_professor(professor_name, university)
        
        # Get reviews (may return empty list, that's OK)
        try:
            reviews = await self.get_professor_reviews(professor['id'])
        except Exception as e:
            # Log but don't fail if reviews can't be fetched
            logger.warning(
                f"Could not fetch reviews for {professor_name}: {e}",
                extra={"professor_id": professor['id']}
            )
            reviews = []
        
        return {
            'professor': professor,
            'reviews': reviews,
            'total_reviews': len(reviews)
        }
    
    async def scrape_professor_data_safe(
        self,
        professor_name: str,
        university: str
    ) -> Optional[Dict[str, Any]]:
        """
        Safe version that returns None instead of raising exceptions.
        Use this for background jobs where failures should be logged but not fatal.
        """
        try:
            return await self.scrape_professor_data(professor_name, university)
        except DataNotFoundError:
            logger.info(f"Professor not found on RMP: {professor_name}")
            return None
        except Exception as e:
            logger.warning(
                f"Failed to scrape professor data: {e}",
                extra={"professor": professor_name, "university": university}
            )
            return None


# Singleton instance
ratemyprof_scraper = RateMyProfessorsScraper()
