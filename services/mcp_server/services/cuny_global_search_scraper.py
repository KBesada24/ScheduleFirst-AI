"""
CUNY Global Search web scraper
Scrapes course data from CUNY Global Search website
"""
import asyncio
import re
from datetime import datetime, time
from typing import List, Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from ..config import settings
from ..utils.logger import get_logger
from ..utils.validators import parse_time_string, normalize_professor_name


logger = get_logger(__name__)


class CUNYGlobalSearchScraper:
    """Scraper for CUNY Global Search course data"""
    
    BASE_URL = settings.cuny_global_search_url
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        logger.info("CUNY Global Search Scraper initialized")
    
    def _get_chrome_options(self) -> Options:
        """Configure Selenium Chrome options"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument(f'user-agent={settings.scraper_user_agent}')
        options.add_argument('--window-size=1920,1080')
        return options
    
    def _init_driver(self) -> webdriver.Chrome:
        """Initialize Selenium WebDriver"""
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self._get_chrome_options())
            driver.implicitly_wait(10)
            logger.info("Chrome WebDriver initialized")
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    async def scrape_semester_courses(self, semester: str) -> List[Dict[str, Any]]:
        """
        Scrape all courses for a given semester from CUNY Global Search
        Semester format: "Fall 2025", "Spring 2026", etc.
        """
        logger.info(f"Starting scrape for semester: {semester}")
        courses: List[Dict[str, Any]] = []
        
        # Get list of all CUNY schools
        cuny_schools = self._get_cuny_schools()
        
        for school in cuny_schools:
            logger.info(f"Scraping {school['name']} for {semester}")
            try:
                school_courses = await self._scrape_school_courses(
                    school_code=school['code'],
                    school_name=school['name'],
                    semester=semester
                )
                courses.extend(school_courses)
                
                # Rate limiting - delay between schools
                await asyncio.sleep(settings.scraper_request_delay)
            
            except Exception as e:
                logger.error(f"Error scraping {school['name']}: {e}")
                continue
        
        logger.info(f"Completed scraping. Total courses: {len(courses)}")
        return courses
    
    async def _scrape_school_courses(
        self,
        school_code: str,
        school_name: str,
        semester: str
    ) -> List[Dict[str, Any]]:
        """Scrape courses for a specific school and semester"""
        courses: List[Dict[str, Any]] = []
        
        try:
            # Initialize driver if not already done
            if not self.driver:
                self.driver = self._init_driver()
            
            # Construct search URL (adjust based on actual CUNY Global Search URL structure)
            search_url = f"{self.BASE_URL}?school={school_code}&semester={semester}"
            logger.debug(f"Navigating to: {search_url}")
            
            self.driver.get(search_url)
            
            # Wait for results to load (adjust selector based on actual page structure)
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "course-listing"))
                )
            except TimeoutException:
                logger.warning(f"Timeout waiting for course listings on {school_name}")
                return courses
            
            # Get the rendered HTML
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Parse course listings (adjust selectors based on actual page structure)
            course_elements = soup.find_all('div', class_='course-listing')
            logger.debug(f"Found {len(course_elements)} course elements")
            
            for element in course_elements:
                try:
                    course_data = self._parse_course_element(element, school_name, semester)
                    if course_data:
                        courses.append(course_data)
                except Exception as e:
                    logger.warning(f"Error parsing course element: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in _scrape_school_courses: {e}")
        
        return courses
    
    def _parse_course_element(
        self,
        element: Any,
        school_name: str,
        semester: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract course details from a course listing element
        Note: Selectors need to be adjusted based on actual CUNY Global Search HTML
        """
        try:
            # Extract course information (adjust selectors based on actual structure)
            course_code_elem = element.find('span', class_='course-code')
            course_name_elem = element.find('span', class_='course-name')
            credits_elem = element.find('span', class_='credits')
            description_elem = element.find('div', class_='course-description')
            
            if not course_code_elem or not course_name_elem:
                return None
            
            course_code = course_code_elem.text.strip()
            course_name = course_name_elem.text.strip()
            credits_text = credits_elem.text.strip() if credits_elem else None
            description = description_elem.text.strip() if description_elem else None
            
            # Parse credits
            credits = None
            if credits_text:
                match = re.search(r'(\d+)', credits_text)
                if match:
                    credits = int(match.group(1))
            
            # Extract subject and course number
            subject_match = re.match(r'([A-Z]+)\s*(\d+)', course_code)
            subject_code = subject_match.group(1) if subject_match else None
            course_number = subject_match.group(2) if subject_match else None
            
            # Get all section details
            sections = []
            section_elements = element.find_all('tr', class_='section')
            
            for section_el in section_elements:
                section_data = self._parse_section_element(section_el)
                if section_data:
                    sections.append(section_data)
            
            return {
                'course_code': course_code,
                'subject_code': subject_code,
                'course_number': course_number,
                'name': course_name,
                'credits': credits,
                'university': school_name,
                'semester': semester,
                'description': description,
                'last_scraped': datetime.now().isoformat(),
                'sections': sections
            }
        
        except Exception as e:
            logger.error(f"Error parsing course element: {e}")
            return None
    
    def _parse_section_element(self, element: Any) -> Optional[Dict[str, Any]]:
        """
        Extract section details (professor, time, location, etc.)
        Note: Selectors need to be adjusted based on actual HTML structure
        """
        try:
            # Extract section information (adjust selectors)
            section_num_elem = element.find('td', class_='section-num')
            professor_elem = element.find('td', class_='professor')
            time_elem = element.find('td', class_='time')
            location_elem = element.find('td', class_='location')
            modality_elem = element.find('td', class_='modality')
            enrollment_elem = element.find('td', class_='enrollment')
            
            if not section_num_elem:
                return None
            
            section_number = section_num_elem.text.strip()
            professor_name = professor_elem.text.strip() if professor_elem else None
            time_range = time_elem.text.strip() if time_elem else None
            location = location_elem.text.strip() if location_elem else None
            modality = modality_elem.text.strip() if modality_elem else 'In-person'
            enrollment = enrollment_elem.text.strip() if enrollment_elem else None
            
            # Normalize professor name
            if professor_name:
                professor_name = normalize_professor_name(professor_name)
            
            # Parse time slots
            days, start_time, end_time = self._parse_time_slot(time_range) if time_range else (None, None, None)
            
            # Parse enrollment
            enrolled, capacity = self._parse_enrollment(enrollment) if enrollment else (None, None)
            
            return {
                'section_number': section_number,
                'professor_name': professor_name,
                'days': days,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'location': location,
                'modality': modality,
                'enrolled': enrolled,
                'capacity': capacity,
                'scraped_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error parsing section element: {e}")
            return None
    
    def _parse_time_slot(self, time_str: str) -> tuple[Optional[str], Optional[time], Optional[time]]:
        """
        Parse time slot like "MWF 10:00-11:15 AM" or "Tu 6:30-8:15 PM"
        Returns: (days: str, start_time: time, end_time: time)
        """
        if not time_str:
            return None, None, None
        
        # Handle online/TBA cases
        if any(keyword in time_str.upper() for keyword in ['ONLINE', 'TBA', 'ARRANGED']):
            return 'Online', None, None
        
        # Pattern: "MWF 10:00-11:15 AM" or "Tu 6:30-8:15 PM"
        match = re.match(
            r'([A-Za-z]+)\s+(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})\s*(AM|PM)',
            time_str
        )
        
        if match:
            days, start_h, start_m, end_h, end_m, period = match.groups()
            
            # Convert to 24-hour format
            start_hour = int(start_h)
            end_hour = int(end_h)
            
            if period.upper() == 'PM':
                if start_hour != 12:
                    start_hour += 12
                if end_hour != 12:
                    end_hour += 12
            elif period.upper() == 'AM':
                if start_hour == 12:
                    start_hour = 0
                if end_hour == 12:
                    end_hour = 0
            
            start_time = time(start_hour, int(start_m))
            end_time = time(end_hour, int(end_m))
            
            return days, start_time, end_time
        
        logger.debug(f"Could not parse time slot: {time_str}")
        return None, None, None
    
    def _parse_enrollment(self, enrollment_str: str) -> tuple[Optional[int], Optional[int]]:
        """
        Parse enrollment like "45/50"
        Returns: (enrolled: int, capacity: int)
        """
        if not enrollment_str:
            return None, None
        
        match = re.match(r'(\d+)/(\d+)', enrollment_str)
        if match:
            return int(match.group(1)), int(match.group(2))
        
        return None, None
    
    def _get_cuny_schools(self) -> List[Dict[str, str]]:
        """
        Get list of all CUNY schools with their codes
        """
        return [
            {'code': 'CCNY', 'name': 'City College'},
            {'code': 'HUNTER', 'name': 'Hunter College'},
            {'code': 'QC', 'name': 'Queens College'},
            {'code': 'BARUCH', 'name': 'Baruch College'},
            {'code': 'BROOKLYN', 'name': 'Brooklyn College'},
            {'code': 'LEHMAN', 'name': 'Lehman College'},
            {'code': 'YORK', 'name': 'York College'},
            {'code': 'CSI', 'name': 'College of Staten Island'},
            {'code': 'JOHN_JAY', 'name': 'John Jay College'},
            {'code': 'MEDGAR', 'name': 'Medgar Evers College'},
            {'code': 'CITYTECH', 'name': 'New York City College of Technology'},
            {'code': 'BMCC', 'name': 'Borough of Manhattan Community College'},
            {'code': 'BCC', 'name': 'Bronx Community College'},
            {'code': 'HOSTOS', 'name': 'Hostos Community College'},
            {'code': 'KBCC', 'name': 'Kingsborough Community College'},
            {'code': 'LAGCC', 'name': 'LaGuardia Community College'},
            {'code': 'QCC', 'name': 'Queensborough Community College'},
        ]
    
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("WebDriver closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()


# Singleton instance
cuny_scraper = CUNYGlobalSearchScraper()
