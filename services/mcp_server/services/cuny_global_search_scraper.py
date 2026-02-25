"""
CUNY Global Search web scraper with circuit breaker and structured error handling
Scrapes course data from CUNY Global Search website via multi-step form navigation.

The real CUNY Global Search site (globalsearch.cuny.edu) is a JSP form application:
  Step 1: Select institution checkbox(es) + term dropdown → click "Next"
  Step 2: Select subject dropdown + options → click "Search"
  Results: Accordion-style sections with <table class="classinfo"> elements
"""
import asyncio
import re
from datetime import datetime, time
from typing import List, Dict, Optional, Any, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException as SeleniumTimeout,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
)
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from ..config import settings
from ..utils.logger import get_logger
from ..utils.validators import parse_time_string, normalize_professor_name
from ..utils.exceptions import ScrapingError, ExternalServiceError
from ..utils.circuit_breaker import circuit_breaker_registry


logger = get_logger(__name__)

# Get the CUNY scraper circuit breaker
cuny_breaker = circuit_breaker_registry.get("cuny_scraper")

# Constants
SEARCH_JSP_URL = "https://globalsearch.cuny.edu/CFGlobalSearchTool/search.jsp"
STEP_TIMEOUT = 15  # seconds to wait for each form step to load
RESULTS_TIMEOUT = 30  # seconds to wait for results page


class CUNYGlobalSearchScraper:
    """Scraper for CUNY Global Search course data with resilience patterns.
    
    Navigates the real multi-step JSP form:
      1. search.jsp → select institution + term → "Next"
      2. Search criteria → select subject → "Search"
      3. Results page → parse <table class="classinfo"> elements
    """
    
    BASE_URL = settings.cuny_global_search_url
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self._driver_lock = asyncio.Lock()
        logger.info("CUNY Global Search Scraper initialized with circuit breaker")
    
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
        """
        Initialize Selenium WebDriver.
        
        Raises:
            ScrapingError: If WebDriver initialization fails
        """
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self._get_chrome_options())
            driver.implicitly_wait(5)
            logger.info("Chrome WebDriver initialized")
            return driver
        except WebDriverException as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise ScrapingError(
                source="CUNY Global Search",
                reason=f"WebDriver initialization failed: {e}",
            )
        except Exception as e:
            logger.error(f"Unexpected error initializing WebDriver: {e}")
            raise ScrapingError(
                source="CUNY Global Search",
                reason=f"WebDriver setup error: {e}",
            )
    
    # ================================================================
    # Navigation Methods (Step 1 → Step 2 → Results)
    # ================================================================
    
    def _navigate_step1(self, school_name: str, semester: str) -> None:
        """
        Step 1: Navigate to search.jsp, select institution and term, click Next.
        
        Args:
            school_name: Institution name matching checkbox label (e.g. "College of Staten Island")
            semester: Semester string like "Spring 2026"
            
        Raises:
            ScrapingError: If navigation or element interaction fails
        """
        logger.info(f"Step 1: Selecting institution '{school_name}' and term '{semester}'")
        
        # Navigate to the search form
        self.driver.get(SEARCH_JSP_URL)
        
        # Wait for institution list and term dropdown to load
        try:
            WebDriverWait(self.driver, STEP_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, "t_pd"))
            )
        except SeleniumTimeout:
            raise ScrapingError(
                source="CUNY Global Search",
                reason="Timeout waiting for search form to load (search.jsp)",
            )
        
        # Select institution checkbox by matching label text
        self._select_institution_checkbox(school_name)
        
        # Resolve and select semester term
        term_id = self._resolve_term_id(semester)
        try:
            term_select = Select(self.driver.find_element(By.ID, "t_pd"))
            term_select.select_by_value(term_id)
            logger.debug(f"Selected term '{semester}' (ID: {term_id})")
        except NoSuchElementException:
            raise ScrapingError(
                source="CUNY Global Search",
                reason=f"Could not find term dropdown (#t_pd)",
            )
        
        # Click the "Next" button
        try:
            next_btn = self.driver.find_element(By.ID, "search_new_spin")
            next_btn.click()
        except NoSuchElementException:
            raise ScrapingError(
                source="CUNY Global Search",
                reason="Could not find 'Next' button (#search_new_spin)",
            )
        
        # Wait for Step 2 form to load (subject dropdown appears)
        try:
            WebDriverWait(self.driver, STEP_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, "subject_ld"))
            )
            logger.info("Step 1 complete — Step 2 form loaded")
        except SeleniumTimeout:
            raise ScrapingError(
                source="CUNY Global Search",
                reason="Timeout waiting for Step 2 form to load after clicking 'Next'",
            )
    
    def _select_institution_checkbox(self, school_name: str) -> None:
        """
        Find and click the institution checkbox by matching visible label text.
        
        The CUNY form uses custom-styled checkboxes with span/label elements.
        We find the element whose visible text matches the school name.
        """
        try:
            # Find all clickable institution labels/spans on the page
            # The institution list contains spans with the school names
            institution_elements = self.driver.find_elements(
                By.XPATH,
                f"//span[contains(text(), '{school_name}')] | "
                f"//label[contains(text(), '{school_name}')]"
            )
            
            if not institution_elements:
                # Try a more flexible match — partial text
                institution_elements = self.driver.find_elements(
                    By.XPATH,
                    f"//*[contains(normalize-space(text()), '{school_name}')]"
                )
            
            if not institution_elements:
                available = self._get_available_institutions()
                raise ScrapingError(
                    source="CUNY Global Search",
                    reason=(
                        f"Institution '{school_name}' not found on form. "
                        f"Available: {', '.join(available)}"
                    ),
                )
            
            # Click the first matching element
            institution_elements[0].click()
            logger.debug(f"Selected institution: {school_name}")
            
        except ScrapingError:
            raise
        except Exception as e:
            raise ScrapingError(
                source="CUNY Global Search",
                reason=f"Error selecting institution '{school_name}': {e}",
            )
    
    def _get_available_institutions(self) -> List[str]:
        """Read all institution names currently visible on the Step 1 form."""
        try:
            # Institution names are typically in spans within a list
            elements = self.driver.find_elements(By.CSS_SELECTOR, "span")
            names = []
            for el in elements:
                text = el.text.strip()
                # Filter to likely institution names (contain "College", "CC", "School", etc.)
                if text and any(
                    kw in text for kw in ["College", "CC", "Center", "School", "University"]
                ):
                    names.append(text)
            return names
        except Exception:
            return []
    
    def _resolve_term_id(self, semester: str) -> str:
        """
        Dynamically read the #t_pd dropdown and find the term ID matching the semester.
        
        Args:
            semester: e.g. "Spring 2026", "Fall 2025", "Summer 2026"
            
        Returns:
            The value attribute of the matching option (e.g. "1262")
            
        Raises:
            ScrapingError: If no matching term is found
        """
        try:
            term_select_el = self.driver.find_element(By.ID, "t_pd")
            options = term_select_el.find_elements(By.TAG_NAME, "option")
        except NoSuchElementException:
            raise ScrapingError(
                source="CUNY Global Search",
                reason="Could not find term dropdown (#t_pd) for term resolution",
            )
        
        # Parse semester string: "Spring 2026" → season="Spring", year="2026"
        parts = semester.strip().split()
        if len(parts) != 2:
            raise ScrapingError(
                source="CUNY Global Search",
                reason=f"Invalid semester format: '{semester}'. Expected 'Season Year' (e.g. 'Spring 2026')",
            )
        season, year = parts[0].lower(), parts[1]
        
        # Build available terms for error messages
        available_terms = []
        
        for option in options:
            value = option.get_attribute("value")
            text = option.text.strip().lower()
            
            if not value or value == "":
                continue  # Skip placeholder option
            
            available_terms.append(option.text.strip())
            
            # Match: option text like "2026 Spring Term" to semester "Spring 2026"
            if year in text and season in text:
                logger.info(f"Resolved semester '{semester}' to term ID '{value}' ('{option.text.strip()}')")
                return value
        
        raise ScrapingError(
            source="CUNY Global Search",
            reason=(
                f"No matching term found for '{semester}'. "
                f"Available terms: {', '.join(available_terms)}"
            ),
        )
    
    def _navigate_step2(self, subject_code: str) -> None:
        """
        Step 2: Select subject, uncheck "Open Only", and click Search.
        
        Args:
            subject_code: Subject code from #subject_ld dropdown (e.g. "CMSC")
        """
        logger.debug(f"Step 2: Selecting subject '{subject_code}' and searching")
        
        # Select subject
        try:
            subject_select = Select(self.driver.find_element(By.ID, "subject_ld"))
            subject_select.select_by_value(subject_code)
        except NoSuchElementException:
            raise ScrapingError(
                source="CUNY Global Search",
                reason=f"Could not find subject dropdown (#subject_ld)",
            )
        except Exception as e:
            raise ScrapingError(
                source="CUNY Global Search",
                reason=f"Error selecting subject '{subject_code}': {e}",
            )
        
        # Uncheck "Show Open Classes Only" if it's checked
        try:
            open_checkbox = self.driver.find_element(By.ID, "open_class_id")
            if open_checkbox.is_selected():
                open_checkbox.click()
                logger.debug("Unchecked 'Show Open Classes Only'")
        except NoSuchElementException:
            logger.debug("'Show Open Classes Only' checkbox not found — skipping")
        except Exception as e:
            logger.debug(f"Could not toggle open-classes checkbox: {e}")
        
        # Click the Search button (same ID as Next button)
        try:
            search_btn = self.driver.find_element(By.ID, "search_new_spin")
            search_btn.click()
        except NoSuchElementException:
            raise ScrapingError(
                source="CUNY Global Search",
                reason="Could not find 'Search' button (#search_new_spin)",
            )
        
        # Wait for results page to load
        try:
            WebDriverWait(self.driver, RESULTS_TIMEOUT).until(
                lambda d: (
                    # Wait until results text appears OR a classinfo table appears
                    "class section" in d.page_source.lower()
                    or d.find_elements(By.CLASS_NAME, "classinfo")
                    or "no classes found" in d.page_source.lower()
                )
            )
            logger.debug("Results page loaded")
        except SeleniumTimeout:
            logger.warning(f"Timeout waiting for results for subject '{subject_code}'")
    
    def _get_available_subjects(self) -> List[Tuple[str, str]]:
        """
        Read all subject options from the #subject_ld dropdown.
        
        Returns:
            List of (value, text) tuples, e.g. [("CMSC", "Computer Science"), ...]
        """
        try:
            subject_el = self.driver.find_element(By.ID, "subject_ld")
            options = subject_el.find_elements(By.TAG_NAME, "option")
            
            subjects = []
            for option in options:
                value = option.get_attribute("value")
                text = option.text.strip()
                # Skip placeholder/empty options
                if value and value.strip() and text:
                    subjects.append((value, text))
            
            logger.info(f"Found {len(subjects)} available subjects")
            logger.info(
                "Subject options discovered",
                extra={
                    "subject_count": len(subjects),
                    "subjects": [{"code": code, "name": name} for code, name in subjects],
                },
            )
            return subjects
            
        except NoSuchElementException:
            raise ScrapingError(
                source="CUNY Global Search",
                reason="Could not find subject dropdown (#subject_ld)",
            )
    
    # ================================================================
    # Result Parsing
    # ================================================================
    
    def _parse_results_page(
        self, school_name: str, semester: str, subject_name: str
    ) -> List[Dict[str, Any]]:
        """
        Parse the results page after a search. Expands accordions and extracts
        course data from <table class="classinfo"> elements.
        
        Returns:
            List of course dicts with 'sections' sub-lists
        """
        courses: List[Dict[str, Any]] = []
        
        # Check if any results exist
        page_source = self.driver.page_source
        if "no classes found" in page_source.lower():
            logger.debug(f"No classes found for subject '{subject_name}'")
            return courses
        
        # Extract result count
        count_match = re.search(r'(\d+)\s+class section', page_source, re.IGNORECASE)
        if count_match:
            logger.debug(f"Found {count_match.group(1)} class sections for '{subject_name}'")
        
        # Expand all accordion sections (institutions and courses)
        self._expand_all_accordions()
        
        # Re-read page source after accordion expansion
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # The page structure uses accordion toggles for courses.
        # Course names appear as clickable headers, and sections are in classinfo tables.
        # We need to identify each course group and its associated classinfo table.
        
        # Strategy: find all classinfo tables and the course header above each one
        classinfo_tables = soup.find_all('table', class_='classinfo')
        logger.debug(f"Found {len(classinfo_tables)} classinfo tables")
        
        if not classinfo_tables:
            logger.debug(f"No classinfo tables found for '{subject_name}'")
            return courses
        
        # Find course headers — these are typically bold text or links near the tables
        # The CUNY site groups courses in toggle sections. Each section has a header
        # and then a classinfo table with rows for each section offering.
        
        # We'll look for toggle/header elements that precede classinfo tables.
        # The toggled course sections typically have IDs like contentDiv0, contentDiv1, etc.
        content_divs = soup.find_all('div', id=re.compile(r'^contentDiv\d+$'))
        
        if content_divs:
            # Each content div contains a classinfo table and corresponds to one course
            for div in content_divs:
                table = div.find('table', class_='classinfo')
                if not table:
                    continue
                
                # Try to find the course name from the toggle header
                # The header is usually in a sibling or parent element
                course_name_text = self._extract_course_name_from_context(div, soup)
                
                course_data = self._parse_classinfo_table(
                    table, course_name_text, school_name, semester
                )
                if course_data:
                    courses.append(course_data)
        else:
            # Fallback: parse all classinfo tables without course context
            for table in classinfo_tables:
                course_name_text = self._extract_course_name_from_context(table, soup)
                course_data = self._parse_classinfo_table(
                    table, course_name_text, school_name, semester
                )
                if course_data:
                    courses.append(course_data)
        
        logger.info(f"Parsed {len(courses)} courses for subject '{subject_name}'")
        return courses
    
    def _expand_all_accordions(self) -> None:
        """Expand all accordion sections on the results page using JavaScript."""
        try:
            # Try to expand institution-level accordions
            self.driver.execute_script("""
                // Expand all institution toggles
                var instImgs = document.querySelectorAll('[id^="contentDivImg_inst"]');
                for (var i = 0; i < instImgs.length; i++) {
                    try { subjectToggleInst(i); } catch(e) {}
                }
                
                // Expand all course toggles
                for (var j = 0; j < 200; j++) {
                    try { subjectToggle(j); } catch(e) { break; }
                }
            """)
            # Brief pause to let DOM update
            import time as time_mod
            time_mod.sleep(1)
            logger.debug("Expanded accordion sections")
        except Exception as e:
            logger.debug(f"Could not expand accordions via JS: {e}")
            # Not fatal — tables may already be visible or we parse what we can
    
    def _extract_course_name_from_context(
        self, element: Any, soup: BeautifulSoup
    ) -> Optional[str]:
        """
        Try to extract the course name/code from the context around a classinfo table.
        
        Looks for text like "CSC 126 - Introduction to Computer Science" in nearby
        toggle headers or parent elements.
        """
        try:
            course_pattern = re.compile(r'\b[A-Z]{2,5}\s*\d{3,4}\b')

            def _extract_candidate(text: Optional[str]) -> Optional[str]:
                if not text:
                    return None
                normalized = " ".join(text.split())
                if course_pattern.search(normalized):
                    return normalized
                return None

            # Look for the toggle image/header element that precedes this div
            # These typically have IDs like contentDivImg0, contentDivImg1, etc.
            div_id = element.get('id', '')
            if div_id and div_id.startswith('contentDiv'):
                # Extract the number suffix
                num_match = re.search(r'(\d+)$', div_id)
                if num_match:
                    idx = num_match.group(1)
                    # Look for the toggle header with that index
                    toggle_id = f"contentDivImg{idx}"
                    toggle_el = soup.find(id=toggle_id)
                    if toggle_el:
                        # The course name is usually in the parent or nearby text
                        parent = toggle_el.parent
                        if parent:
                            candidate = _extract_candidate(parent.get_text(" ", strip=True))
                            if candidate:
                                return candidate

            # Look through previous siblings/elements that often contain course headers
            for prev in element.find_all_previous(['div', 'span', 'td', 'b', 'strong', 'h3', 'h4', 'a', 'label'], limit=12):
                candidate = _extract_candidate(prev.get_text(" ", strip=True))
                if candidate:
                    return candidate
            
            # Fallback: look for any bold or header text preceding the element
            prev = element.find_previous(['b', 'strong', 'h3', 'h4', 'a'])
            if prev:
                text = prev.get_text(strip=True)
                # Check if it looks like a course code
                if re.search(r'[A-Z]{2,}\s*\d{3}', text):
                    return text
            
            return None
            
        except Exception:
            return None
    
    def _parse_classinfo_table(
        self,
        table: Any,
        course_name_text: Optional[str],
        school_name: str,
        semester: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a <table class="classinfo"> element into a course dict with sections.
        
        Args:
            table: BeautifulSoup table element with class="classinfo"
            course_name_text: Course header text like "CSC 126 - Introduction to CS"
            school_name: University name
            semester: Semester string
        """
        try:
            # Parse course code and name from header text
            course_code = None
            course_name = None
            subject_code = None
            course_number = None
            
            if course_name_text:
                # Try to extract course code from patterns like:
                # "CSC 126 - Introduction to Computer Science"
                # "CMSC 126 - Intro to CS"
                code_match = re.search(r'([A-Z]{2,})\s*(\d{3,4})', course_name_text)
                if code_match:
                    subject_code = code_match.group(1)
                    course_number = code_match.group(2)
                    course_code = f"{subject_code} {course_number}"
                
                # Extract course name (after the dash or after the code)
                name_match = re.search(r'[-–]\s*(.+)', course_name_text)
                if name_match:
                    course_name = name_match.group(1).strip()
                elif course_code:
                    # Use text after the course code
                    remaining = course_name_text[course_name_text.index(course_number) + len(course_number):]
                    course_name = remaining.strip().lstrip('-–').strip()
            
            # Parse section rows from the table
            sections = []
            rows = table.find_all('tr')
            
            # Skip the header row(s) — find data rows
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 5:
                    continue  # Skip header or malformed rows
                
                section_data = self._parse_classinfo_row(cells)
                if section_data:
                    sections.append(section_data)
            
            if not sections and not course_code:
                return None  # Nothing useful parsed
            
            return {
                'course_code': course_code or 'UNKNOWN',
                'subject_code': subject_code,
                'course_number': course_number,
                'name': course_name or course_name_text or 'Unknown Course',
                'credits': None,  # Credits not shown in classinfo tables
                'university': school_name,
                'semester': semester,
                'description': None,
                'last_scraped': datetime.now().isoformat(),
                'sections': sections,
            }
            
        except Exception as e:
            logger.debug(f"Error parsing classinfo table: {e}")
            return None
    
    def _parse_classinfo_row(self, cells: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a single row from a classinfo table.
        
        Expected columns (in order):
        CLASS | SECTION | DAYS & TIMES | ROOM | INSTRUCTOR | INSTRUCTION MODE | MEETING DATES | STATUS | COURSE TOPIC
        
        The number of columns may vary — we handle gracefully.
        """
        try:
            # Extract cell text, defaulting to empty string
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # Map by position (some pages may have fewer columns)
            class_id = cell_texts[0] if len(cell_texts) > 0 else None
            section_number = cell_texts[1] if len(cell_texts) > 1 else None
            days_times = cell_texts[2] if len(cell_texts) > 2 else None
            room = cell_texts[3] if len(cell_texts) > 3 else None
            instructor = cell_texts[4] if len(cell_texts) > 4 else None
            instruction_mode = cell_texts[5] if len(cell_texts) > 5 else None
            meeting_dates = cell_texts[6] if len(cell_texts) > 6 else None
            
            # Check status — look for open/closed icon alt text
            status = None
            if len(cells) > 7:
                status_cell = cells[7]
                img = status_cell.find('img')
                if img:
                    status = img.get('alt', '').strip()
                else:
                    status = status_cell.get_text(strip=True)
            
            # Skip header rows or empty rows
            if not class_id or not class_id.strip():
                return None
            # Skip if class_id looks like a header (e.g. "CLASS")
            if class_id.upper() == 'CLASS' or not any(c.isdigit() for c in class_id):
                return None
            
            # Normalize instructor name
            professor_name = instructor
            if professor_name and professor_name.strip():
                try:
                    professor_name = normalize_professor_name(professor_name)
                except Exception:
                    pass  # Keep original name if normalization fails
            
            # Parse days & times
            days, start_time, end_time = self._parse_time_slot(days_times) if days_times else (None, None, None)
            
            # Map instruction mode to modality
            modality = instruction_mode if instruction_mode else 'In-person'
            
            return {
                'section_number': section_number or class_id,
                'professor_name': professor_name,
                'days': days,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'location': room,
                'modality': modality,
                'enrolled': None,  # Enrollment not shown in classinfo table
                'capacity': None,
                'scraped_at': datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.debug(f"Error parsing classinfo row: {e}")
            return None
    
    # ================================================================
    # Main Scraping Flow
    # ================================================================
    
    @cuny_breaker.protected
    async def scrape_semester_courses(
        self,
        semester: str,
        university: Optional[str] = None,
        subject_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape courses for a given semester from CUNY Global Search.
        
        When `university` is provided, only that school is scraped (fast path).
        When `university` is None, all CUNY schools are scraped (batch mode).
        
        Args:
            semester: Semester string like "Fall 2025", "Spring 2026"
            university: Optional school name to scrape only that school
        
        Raises:
            ScrapingError: If scraping fails
            ExternalServiceError: If CUNY service is unavailable
        """
        logger.info(f"Starting scrape for semester: {semester}" +
                     (f", university: {university}" if university else " (all schools)"))
        courses: List[Dict[str, Any]] = []
        failed_schools: List[str] = []
        
        # Get list of schools to scrape
        all_schools = self._get_cuny_schools()
        
        if university:
            # Filter to only the requested school
            cuny_schools = [s for s in all_schools if s['name'] == university]
            if not cuny_schools:
                # Try case-insensitive partial match as fallback
                uni_lower = university.lower()
                cuny_schools = [s for s in all_schools if uni_lower in s['name'].lower()]
            if not cuny_schools:
                logger.warning(f"University '{university}' not found in CUNY schools list, scraping all")
                cuny_schools = all_schools
        else:
            cuny_schools = all_schools
        
        for school in cuny_schools:
            logger.info(f"Scraping {school['name']} for {semester}")
            try:
                school_courses = await self._scrape_school_courses(
                    school_name=school['name'],
                    semester=semester,
                    subject_code=subject_code,
                )
                courses.extend(school_courses)
                
                # Rate limiting - delay between schools (skip if only one school)
                if len(cuny_schools) > 1:
                    await asyncio.sleep(settings.scraper_request_delay)
            
            except ScrapingError as e:
                logger.warning(f"Failed to scrape {school['name']}: {e}")
                failed_schools.append(school['name'])
                continue
            except Exception as e:
                logger.error(f"Unexpected error scraping {school['name']}: {e}")
                failed_schools.append(school['name'])
                continue
        
        # Log summary
        if failed_schools:
            logger.warning(
                f"Scraping completed with errors. "
                f"Successful: {len(cuny_schools) - len(failed_schools)}, "
                f"Failed: {len(failed_schools)} ({', '.join(failed_schools)})"
            )
        else:
            logger.info(f"Completed scraping successfully. Total courses: {len(courses)}")
        
        # If all schools failed, raise error
        if len(failed_schools) == len(cuny_schools):
            raise ExternalServiceError(
                service="CUNY Global Search",
                operation="scrape_semester_courses",
                details={"semester": semester, "failed_schools": failed_schools},
            )
        
        return courses
    
    async def _scrape_school_courses(
        self,
        school_name: str,
        semester: str,
        subject_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scrape courses for a specific school and semester using the multi-step form.
        
        Flow:
          1. Navigate Step 1 (select institution + term)
          2. Get available subjects from Step 2 dropdown
          3. For each subject: search → parse results → go back → next subject
          
        Raises:
            ScrapingError: If scraping fails for this school
        """
        courses: List[Dict[str, Any]] = []
        
        async with self._driver_lock:
            try:
                # Initialize driver if not already done
                if not self.driver:
                    self.driver = self._init_driver()
                
                # Step 1: Select institution and term
                self._navigate_step1(school_name, semester)
                
                # Get all available subjects for this school/term
                subjects = self._get_available_subjects()

                if subject_code:
                    requested_subject = subject_code.upper().strip()
                    subject_code_aliases = {
                        "CSC": "CMSC",
                        "CS": "CMSC",
                        "PSY": "PSYC",
                    }
                    subject_name_aliases = {
                        "CSC": "COMPUTER SCIENCE",
                        "CS": "COMPUTER SCIENCE",
                        "PSY": "PSYCHOLOGY",
                    }
                    normalized_subject = subject_code_aliases.get(requested_subject, requested_subject)
                    subject_name_hint = subject_name_aliases.get(requested_subject, "")
                    available_subject_codes = [code for code, _ in subjects]
                    available_subject_names = [name for _, name in subjects]
                    near_code_matches = [
                        code
                        for code in available_subject_codes
                        if normalized_subject in code.upper() or code.upper() in normalized_subject
                    ]
                    near_name_matches = [
                        name
                        for name in available_subject_names
                        if subject_name_hint and subject_name_hint in name.upper()
                    ]

                    exact_code_subjects = [
                        (code, name)
                        for code, name in subjects
                        if code.upper().strip() == normalized_subject
                    ]
                    code_family_subjects = [
                        (code, name)
                        for code, name in subjects
                        if normalized_subject in code.upper().strip()
                        or code.upper().strip() in normalized_subject
                    ]
                    name_subjects = [
                        (code, name)
                        for code, name in subjects
                        if subject_name_hint and subject_name_hint in name.upper().strip()
                    ]

                    if exact_code_subjects:
                        subjects = exact_code_subjects
                        subject_match_strategy = "exact_code"
                    elif code_family_subjects:
                        subjects = code_family_subjects
                        subject_match_strategy = "code_family"
                    elif name_subjects:
                        subjects = name_subjects
                        subject_match_strategy = "name_contains"
                    else:
                        subjects = []
                        subject_match_strategy = "none"

                    logger.info(
                        f"Subject-scoped scrape enabled for {school_name}: {requested_subject} "
                        f"({len(subjects)} matching subject options, strategy={subject_match_strategy})"
                    )
                    if not subjects:
                        logger.warning(
                            "No exact subject-code match found for requested subject",
                            extra={
                                "requested_subject": requested_subject,
                                "normalized_subject": normalized_subject,
                                "subject_name_hint": subject_name_hint,
                                "available_subject_codes": available_subject_codes,
                                "near_code_matches": near_code_matches,
                                "near_name_matches": near_name_matches,
                            },
                        )
                
                if not subjects:
                    logger.warning(f"No subjects available for {school_name} in {semester}")
                    return courses
                
                # Iterate over each subject
                for idx, (subject_code, subject_name) in enumerate(subjects):
                    logger.debug(
                        f"Scraping subject {idx + 1}/{len(subjects)}: "
                        f"{subject_name} ({subject_code})"
                    )
                    
                    try:
                        # Step 2: Select subject and search
                        self._navigate_step2(subject_code)
                        
                        # Parse results
                        subject_courses = self._parse_results_page(
                            school_name, semester, subject_name
                        )
                        courses.extend(subject_courses)
                        logger.info(
                            "Subject scrape complete",
                            extra={
                                "school": school_name,
                                "semester": semester,
                                "subject_code": subject_code,
                                "subject_name": subject_name,
                                "courses_found": len(subject_courses),
                                "running_total_courses": len(courses),
                            },
                        )
                        
                        # Navigate back to Step 2 for the next subject
                        if idx < len(subjects) - 1:
                            self._navigate_back_to_step2()
                            # Rate limiting between subjects
                            await asyncio.sleep(settings.scraper_request_delay)
                    
                    except ScrapingError as e:
                        logger.warning(
                            f"Error scraping subject '{subject_name}' at {school_name}: {e}"
                        )
                        # Try to recover by re-navigating from Step 1
                        try:
                            self._navigate_step1(school_name, semester)
                        except Exception:
                            logger.error(f"Could not recover after subject error, stopping {school_name}")
                            break
                        continue
                    except Exception as e:
                        logger.warning(f"Unexpected error on subject '{subject_name}': {e}")
                        continue
                
            except WebDriverException as e:
                # Reset driver on WebDriver errors
                self._safe_close_driver()
                raise ScrapingError(
                    source="CUNY Global Search",
                    reason=f"WebDriver error for {school_name}: {e}",
                )
            except ScrapingError:
                raise
            except Exception as e:
                logger.error(f"Error in _scrape_school_courses: {e}", exc_info=True)
                raise ScrapingError(
                    source="CUNY Global Search",
                    reason=f"Failed to scrape {school_name}: {e}",
                )
        
        return courses
    
    def _navigate_back_to_step2(self) -> None:
        """Navigate back from results page to Step 2 (search criteria) for the next subject."""
        try:
            def _wait_for_step2() -> bool:
                try:
                    WebDriverWait(self.driver, STEP_TIMEOUT).until(
                        EC.presence_of_element_located((By.ID, "subject_ld"))
                    )
                    return True
                except SeleniumTimeout:
                    return False

            # Look for CUNY "Search Criteria" controls first, then generic modify/new search controls.
            modify_btn = None

            css_selectors = [
                "a#searchlink",               # CUNY results page control
                "a[name='searchlink']",
                "input#searchlink",
                "a[id*='search'][id*='link']",
                "input[name*='search'][value*='Search']",
            ]
            for selector in css_selectors:
                try:
                    modify_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            # Try common selectors for the back/modify button
            if not modify_btn:
                for selector in [
                    "//input[@value='Modify Search']",
                    "//input[contains(@value, 'Modify Search')]",
                    "//input[contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'modify search')]",
                    "//button[contains(text(), 'Modify Search')]",
                    "//a[contains(text(), 'Modify Search')]",
                    "//button[contains(translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'modify search')]",
                    "//a[contains(translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'modify search')]",
                    "//*[contains(translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'modify search') or contains(translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'search criteria')]",
                    "//input[@value='New Search']",
                ]:
                    try:
                        modify_btn = self.driver.find_element(By.XPATH, selector)
                        break
                    except NoSuchElementException:
                        continue
            
            if modify_btn:
                try:
                    modify_btn.click()
                except Exception:
                    # Some controls are hidden/styled; JS click is often more reliable.
                    self.driver.execute_script("arguments[0].click();", modify_btn)
                if _wait_for_step2():
                    logger.debug("Navigated back to Step 2")
                    return

            # Try common JS handlers used by older CUNY pages
            js_handlers = [
                "modifySearch", "modSearch", "newSearch", "searchCriteria",
                "goBackToSearch", "returnToSearch", "searchAgain"
            ]
            for handler in js_handlers:
                try:
                    exists = self.driver.execute_script(
                        "return typeof window[arguments[0]] === 'function';", handler
                    )
                    if exists:
                        self.driver.execute_script("window[arguments[0]]();", handler)
                        if _wait_for_step2():
                            logger.debug(f"Navigated back to Step 2 via JS handler: {handler}")
                            return
                except Exception:
                    continue

            # Generic JS-based browser history fallback
            try:
                self.driver.execute_script("window.history.back();")
            except Exception:
                self.driver.back()

            if _wait_for_step2():
                logger.debug("Navigated back to Step 2 via browser history")
                return

            raise SeleniumTimeout("Could not return to Step 2")
                
        except SeleniumTimeout:
            logger.debug("Timeout navigating back to Step 2")
            raise ScrapingError(
                source="CUNY Global Search",
                reason="Could not navigate back to search criteria from results page",
            )
        except Exception as e:
            logger.warning(f"Error navigating back to Step 2: {e}")
            raise ScrapingError(
                source="CUNY Global Search",
                reason=f"Error navigating back: {e}",
            )
    
    # ================================================================
    # Utility Methods
    # ================================================================
    
    def _safe_close_driver(self) -> None:
        """Safely close the WebDriver, ignoring errors"""
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        finally:
            self.driver = None
    
    def _parse_time_slot(self, time_str: str) -> Tuple[Optional[str], Optional[time], Optional[time]]:
        """
        Parse time slot from CUNY results.
        
        Handles formats like:
          "MoWeFr 10:00AM - 10:50AM"
          "TuTh 6:30PM - 8:10PM"
          "MoWe 11:00AM - 12:15PM"
          "TBA"
          "ONLINE"
        
        Returns: (days: str, start_time: time, end_time: time)
        """
        if not time_str:
            return None, None, None
        
        time_str = time_str.strip()
        
        # Handle online/TBA cases
        if any(keyword in time_str.upper() for keyword in ['ONLINE', 'TBA', 'ARRANGED', 'HOURS ARR']):
            return 'Online', None, None
        
        # Pattern for CUNY format: "MoWeFr 10:00AM - 10:50AM" or "TuTh 6:30PM - 8:10PM"
        match = re.match(
            r'([A-Za-z]+)\s+(\d{1,2}):(\d{2})\s*(AM|PM)\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)',
            time_str,
            re.IGNORECASE
        )
        
        if match:
            days_raw, start_h, start_m, start_period, end_h, end_m, end_period = match.groups()
            
            # Convert to 24-hour format
            start_hour = int(start_h)
            end_hour = int(end_h)
            
            if start_period.upper() == 'PM' and start_hour != 12:
                start_hour += 12
            elif start_period.upper() == 'AM' and start_hour == 12:
                start_hour = 0
            
            if end_period.upper() == 'PM' and end_hour != 12:
                end_hour += 12
            elif end_period.upper() == 'AM' and end_hour == 12:
                end_hour = 0
            
            start_time_val = time(start_hour, int(start_m))
            end_time_val = time(end_hour, int(end_m))
            
            # Normalize day abbreviations: MoWeFr → MWF, TuTh → TTh
            days = self._normalize_days(days_raw)
            
            return days, start_time_val, end_time_val
        
        # Fallback: try the old format "MWF 10:00-11:15 AM"
        match2 = re.match(
            r'([A-Za-z]+)\s+(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})\s*(AM|PM)',
            time_str
        )
        
        if match2:
            days, start_h, start_m, end_h, end_m, period = match2.groups()
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
            
            start_time_val = time(start_hour, int(start_m))
            end_time_val = time(end_hour, int(end_m))
            
            return days, start_time_val, end_time_val
        
        logger.debug(f"Could not parse time slot: {time_str}")
        return None, None, None
    
    def _normalize_days(self, days_raw: str) -> str:
        """
        Normalize CUNY day abbreviations to compact form.
        
        CUNY uses: Mo, Tu, We, Th, Fr, Sa, Su
        Converts to: M, Tu, W, Th, F, Sa, Su (or MWF, TTh style)
        """
        day_map = {
            'Mo': 'M', 'Tu': 'Tu', 'We': 'W', 'Th': 'Th',
            'Fr': 'F', 'Sa': 'Sa', 'Su': 'Su'
        }
        
        result = days_raw
        for long_form, short_form in day_map.items():
            result = result.replace(long_form, short_form)
        
        return result
    
    def _parse_enrollment(self, enrollment_str: str) -> Tuple[Optional[int], Optional[int]]:
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
        Get list of all CUNY schools.
        
        Names MUST match the checkbox labels on the CUNY Global Search form exactly.
        The 'code' field is kept as an internal identifier but is NOT used for navigation.
        """
        return [
            {'code': 'BAR', 'name': 'Baruch College'},
            {'code': 'BMCC', 'name': 'Borough of Manhattan CC'},
            {'code': 'BCC', 'name': 'Bronx CC'},
            {'code': 'BC', 'name': 'Brooklyn College'},
            {'code': 'CCNY', 'name': 'City College'},
            {'code': 'CSI', 'name': 'College of Staten Island'},
            {'code': 'GC', 'name': 'Graduate Center'},
            {'code': 'GCC', 'name': 'Guttman CC'},
            {'code': 'HOS', 'name': 'Hostos CC'},
            {'code': 'HC', 'name': 'Hunter College'},
            {'code': 'JJC', 'name': 'John Jay College'},
            {'code': 'KBCC', 'name': 'Kingsborough CC'},
            {'code': 'LAGCC', 'name': 'LaGuardia CC'},
            {'code': 'LC', 'name': 'Lehman College'},
            {'code': 'MHC', 'name': 'Macaulay Honors College'},
            {'code': 'MEC', 'name': 'Medgar Evers College'},
            {'code': 'NYCCT', 'name': 'NYC College of Technology'},
            {'code': 'QC', 'name': 'Queens College'},
            {'code': 'QCC', 'name': 'Queensborough CC'},
            {'code': 'SOJ', 'name': 'School of Journalism'},
            {'code': 'SLUS', 'name': 'School of Labor&Urban Studies'},
            {'code': 'SOL', 'name': 'School of Law'},
            {'code': 'SOM', 'name': 'School of Medicine'},
            {'code': 'SPS', 'name': 'School of Professional Studies'},
            {'code': 'SPH', 'name': 'School of Public Health'},
            {'code': 'YC', 'name': 'York College'},
        ]
    
    def close(self) -> None:
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.debug(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
                logger.info("WebDriver closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()


# Singleton instance
cuny_scraper = CUNYGlobalSearchScraper()
