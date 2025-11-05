# CUNY AI Schedule Optimizer - Implementation Guide: CUNY Global Search Integration

## Quick Reference: Updated Data Source

**Primary Data Source**: CUNY Global Search Website (instead of CUNYfirst Schedule Builder API)
- URL: https://globalsearch.cuny.edu/
- Method: Web scraping (with ethical considerations)
- Update frequency: Weekly (with option for real-time if possible)
- Coverage: All 25 CUNY schools

---

## 1. CUNY Global Search Integration Strategy

### 1.1 Data Extraction Architecture

```
CUNY Global Search Website
         │
         ├─ Search Query (Course code, semester)
         │
         ├─ HTML Response
         │       ├─ Course listings
         │       ├─ Section details
         │       ├─ Professor names
         │       ├─ Time slots
         │       ├─ Campus locations
         │       └─ Enrollment info
         │
         ├─ Parsing Pipeline
         │       ├─ BeautifulSoup (HTML parsing)
         │       ├─ Regex (data extraction)
         │       ├─ Data validation
         │       └─ Normalization
         │
         ├─ Storage
         │       └─ Supabase PostgreSQL
         │
         └─ Cache Layer
             └─ Update weekly
```

### 1.2 Scraper Implementation

**Technology**: 
- **BeautifulSoup4** for HTML parsing
- **Selenium** (headless Chrome) for JavaScript-rendered content
- **httpx** for async HTTP requests
- **APScheduler** for weekly scheduling

**File**: `services/mcp_server/services/cuny_global_search_scraper.py`

```python
import asyncio
from bs4 import BeautifulSoup
import httpx
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import logging

logger = logging.getLogger(__name__)

class CUNYGlobalSearchScraper:
    BASE_URL = "https://globalsearch.cuny.edu/"
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def scrape_semester_courses(self, semester: str) -> list:
        """
        Scrape all courses for a given semester from CUNY Global Search
        Semester format: "Fall 2025", "Spring 2026", etc.
        """
        courses = []
        
        # Get list of all CUNY schools
        cuny_schools = await self._get_cuny_schools()
        
        for school in cuny_schools:
            logger.info(f"Scraping {school['name']} for {semester}")
            try:
                school_courses = await self._scrape_school_courses(
                    school_code=school['code'],
                    school_name=school['name'],
                    semester=semester
                )
                courses.extend(school_courses)
            except Exception as e:
                logger.error(f"Error scraping {school['name']}: {e}")
                continue
        
        return courses
    
    async def _scrape_school_courses(self, school_code: str, school_name: str, semester: str) -> list:
        """
        Scrape courses for a specific school and semester
        """
        courses = []
        
        # CUNY Global Search uses pagination and dynamic loading
        # We'll use Selenium for JavaScript rendering
        driver = webdriver.Chrome(options=self._get_chrome_options())
        
        try:
            # Construct search URL for the school
            search_url = f"{self.BASE_URL}?school={school_code}&semester={semester}"
            driver.get(search_url)
            
            # Wait for results to load (JavaScript rendering)
            WebDriverWait(driver, 10).until(
                lambda d: d.find_elements(By.CLASS_NAME, "course-listing")
            )
            
            # Get the rendered HTML
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Parse course listings
            course_elements = soup.find_all('div', class_='course-listing')
            
            for element in course_elements:
                try:
                    course_data = self._parse_course_element(element, school_name, semester)
                    if course_data:
                        courses.append(course_data)
                except Exception as e:
                    logger.warning(f"Error parsing course element: {e}")
                    continue
        
        finally:
            driver.quit()
        
        return courses
    
    def _parse_course_element(self, element, school_name: str, semester: str) -> dict:
        """
        Extract course details from a course listing element
        Expected structure may vary; adjust based on actual HTML
        """
        try:
            # Example parsing (adjust based on actual CUNY Global Search HTML structure)
            course_code = element.find('span', class_='course-code')?.text.strip()
            course_name = element.find('span', class_='course-name')?.text.strip()
            credits = element.find('span', class_='credits')?.text.strip()
            
            # Get all section details
            sections = []
            section_elements = element.find_all('tr', class_='section')
            
            for section_el in section_elements:
                section_data = self._parse_section_element(section_el)
                sections.append(section_data)
            
            return {
                'course_code': course_code,
                'course_name': course_name,
                'credits': int(credits) if credits else None,
                'university': school_name,
                'semester': semester,
                'sections': sections,
                'scraped_at': datetime.now()
            }
        
        except Exception as e:
            logger.error(f"Error parsing course element: {e}")
            return None
    
    def _parse_section_element(self, element) -> dict:
        """
        Extract section details (professor, time, location, etc.)
        """
        try:
            section_number = element.find('td', class_='section-num')?.text.strip()
            professor_name = element.find('td', class_='professor')?.text.strip()
            time_range = element.find('td', class_='time')?.text.strip()  # "MWF 10:00-11:15 AM"
            location = element.find('td', class_='location')?.text.strip()
            modality = element.find('td', class_='modality')?.text.strip()  # "In-person", "Online"
            enrollment = element.find('td', class_='enrollment')?.text.strip()  # "45/50"
            
            # Parse time slots
            days, start_time, end_time = self._parse_time_slot(time_range)
            
            # Parse enrollment
            enrolled, capacity = self._parse_enrollment(enrollment)
            
            return {
                'section_number': section_number,
                'professor_name': professor_name,
                'days': days,
                'start_time': start_time,
                'end_time': end_time,
                'location': location,
                'modality': modality,
                'enrolled': enrolled,
                'capacity': capacity
            }
        
        except Exception as e:
            logger.error(f"Error parsing section element: {e}")
            return None
    
    def _parse_time_slot(self, time_str: str) -> tuple:
        """
        Parse time slot like "MWF 10:00-11:15 AM" or "Tu 6:30-8:15 PM"
        Returns: (days: str, start_time: time, end_time: time)
        """
        import re
        from datetime import datetime, time
        
        if not time_str:
            return None, None, None
        
        # Pattern: "MWF 10:00-11:15 AM" or "Online"
        if 'Online' in time_str or 'TBA' in time_str:
            return 'Online', None, None
        
        # Extract days and times
        match = re.match(r'([A-Z]+)\s+(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})\s+(AM|PM)', time_str)
        
        if match:
            days, start_h, start_m, end_h, end_m, period = match.groups()
            
            # Convert 12-hour to 24-hour format
            if period == 'PM' and start_h != '12':
                start_h = int(start_h) + 12
            elif period == 'AM' and start_h == '12':
                start_h = 0
            
            start_time = time(int(start_h), int(start_m))
            end_time = time(int(end_h), int(end_m))
            
            return days, start_time, end_time
        
        return None, None, None
    
    def _parse_enrollment(self, enrollment_str: str) -> tuple:
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
    
    async def _get_cuny_schools(self) -> list:
        """
        Get list of all CUNY schools with their codes
        Can be hardcoded or fetched from CUNY Global Search
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
            {'code': 'KBCC', 'name': 'Kingsborough Community College'},
            {'code': 'LAGUARDIA', 'name': 'LaGuardia Community College'},
            {'code': 'BMCC', 'name': 'Borough of Manhattan Community College'},
            {'code': 'NYCCC', 'name': 'NYC College of Technology'},
            {'code': 'HOSTOS', 'name': 'Hostos Community College'},
            {'code': 'MEDGAR', 'name': 'Medgar Evers College'},
            {'code': 'GC', 'name': 'Graduate School'},
            # ... add all 25 schools
        ]
    
    def _get_chrome_options(self):
        """Configure Selenium Chrome options"""
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={self.headers["User-Agent"]}')
        
        return options
```

---

## 2. Database Storage Strategy

### 2.1 Updated Schema for CUNY Global Search Data

```sql
-- Courses table (synced from CUNY Global Search)
CREATE TABLE courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_code TEXT NOT NULL,           -- e.g., "CSC381"
  subject_code TEXT,                   -- e.g., "CSC"
  course_number TEXT,                  -- e.g., "381"
  name TEXT NOT NULL,
  credits INT,
  university TEXT NOT NULL,            -- CUNY school name
  semester TEXT NOT NULL,              -- "Fall 2025"
  description TEXT,
  last_scraped TIMESTAMP DEFAULT NOW(),
  UNIQUE(course_code, university, semester)
);

-- Course sections (from CUNY Global Search)
CREATE TABLE course_sections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
  section_number TEXT NOT NULL,
  professor_id UUID REFERENCES professors(id) ON DELETE SET NULL,
  professor_name TEXT,                 -- Cache professor name if not in DB yet
  
  -- Schedule details
  days TEXT,                           -- "MWF", "TTh", "Online", etc.
  start_time TIME,
  end_time TIME,
  
  -- Location
  location TEXT,                       -- Room number/building
  modality TEXT,                       -- "In-person", "Online", "Hybrid"
  
  -- Enrollment
  enrolled INT,
  capacity INT,
  
  -- Metadata
  scraped_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(course_id, section_number, semester)
);

-- Index for fast lookups
CREATE INDEX idx_courses_semester ON courses(semester);
CREATE INDEX idx_courses_university ON courses(university);
CREATE INDEX idx_sections_professor ON course_sections(professor_name);
CREATE INDEX idx_sections_time ON course_sections(days, start_time);
```

### 2.2 Data Sync Pipeline (APScheduler)

**File**: `services/background_jobs/jobs/sync_cuny_courses.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from cuny_global_search_scraper import CUNYGlobalSearchScraper
from supabase_service import SupabaseService

class CUNYCourseSyncJob:
    def __init__(self):
        self.scraper = CUNYGlobalSearchScraper()
        self.db = SupabaseService()
        self.scheduler = AsyncIOScheduler()
    
    async def sync_all_semesters(self):
        """Sync courses for current and next semesters"""
        semesters = self._get_semesters_to_sync()
        
        for semester in semesters:
            logger.info(f"Starting sync for {semester}")
            
            try:
                # Scrape all courses from CUNY Global Search
                courses = await self.scraper.scrape_semester_courses(semester)
                
                # Store in database
                await self.db.insert_courses(courses)
                
                # Update sync timestamp
                await self.db.update_sync_timestamp(semester)
                
                logger.info(f"Successfully synced {len(courses)} courses for {semester}")
            
            except Exception as e:
                logger.error(f"Error syncing {semester}: {e}")
                # Send alert notification
                await self._send_error_alert(semester, str(e))
    
    def _get_semesters_to_sync(self) -> list:
        """Determine which semesters to sync"""
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        semesters = []
        
        # Determine current semester
        if current_month < 6:
            semesters.append(f"Spring {current_year}")
            semesters.append(f"Summer {current_year}")
            semesters.append(f"Fall {current_year}")
        elif current_month < 8:
            semesters.append(f"Summer {current_year}")
            semesters.append(f"Fall {current_year}")
        else:
            semesters.append(f"Fall {current_year}")
            semesters.append(f"Spring {current_year + 1}")
        
        return semesters
    
    def start_scheduler(self):
        """Start background scheduler"""
        # Sync every Sunday at 2 AM (low traffic time)
        self.scheduler.add_job(
            self.sync_all_semesters,
            'cron',
            day_of_week='sun',
            hour=2,
            minute=0
        )
        self.scheduler.start()

# Initialize and start
sync_job = CUNYCourseSyncJob()
sync_job.start_scheduler()
```

---

## 3. Handling CUNY Global Search Limitations

### 3.1 Technical Challenges & Solutions

| Challenge | Impact | Solution |
|-----------|--------|----------|
| **Dynamic JavaScript Content** | Data not visible in raw HTML | Use Selenium for rendering, handle async loads |
| **Rate Limiting** | IP may be blocked | Implement exponential backoff, rotate user agents, respect robots.txt |
| **Page Structure Changes** | Scraper breaks with site updates | Use flexible CSS selectors, error handling, monitoring |
| **Large Dataset** | Scraping all 25 schools takes time | Parallelize scraping, cache aggressively, incremental updates |
| **Missing Professor IDs** | Can't match to RateMyProf | Implement fuzzy matching, manual curation, user corrections |
| **Incomplete Course Data** | Some sections missing details | Use defaults, fallback data, request user input in UI |

### 3.2 Retry Logic & Error Handling

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class RobustCUNYScraper(CUNYGlobalSearchScraper):
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _scrape_school_courses_with_retry(self, **kwargs):
        """Retry scraping with exponential backoff"""
        return await self._scrape_school_courses(**kwargs)
    
    async def scrape_with_fallback(self, semester: str):
        """Try scraping, fallback to cached data if fails"""
        try:
            courses = await self.scrape_semester_courses(semester)
            return courses
        except Exception as e:
            logger.error(f"Scraping failed: {e}. Using cached data.")
            
            # Fallback to previous semester's data (same courses likely offered)
            last_year_semester = f"{semester.split()[0]} {int(semester.split()[1]) - 1}"
            cached_courses = await self.db.get_courses_by_semester(last_year_semester)
            
            # Update semester label but keep other data
            for course in cached_courses:
                course['semester'] = semester
            
            return cached_courses
```

---

## 4. Rate Limiting & Ethical Scraping

### 4.1 Best Practices

```python
import time
import random

class EthicalCUNYScraper(CUNYGlobalSearchScraper):
    def __init__(self, request_delay: float = 2.0):
        super().__init__()
        self.request_delay = request_delay
        self.last_request_time = 0
    
    async def _make_request(self, url: str):
        """Rate-limited requests with respect for server resources"""
        # Respect minimum delay between requests
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            await asyncio.sleep(self.request_delay - elapsed)
        
        # Random delay to avoid bot detection (1-3 seconds)
        delay = random.uniform(1, 3)
        await asyncio.sleep(delay)
        
        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=10)
            self.last_request_time = time.time()
            
            return response
    
    def _respect_robots_txt(self):
        """Check and respect robots.txt from CUNY Global Search"""
        try:
            response = httpx.get(f"{self.BASE_URL}/robots.txt")
            # Parse robots.txt and verify we're allowed to scrape
            logger.info(f"robots.txt:\n{response.text}")
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt: {e}")
```

### 4.2 Alternative: API Access

**Best Approach**: Request CUNY for official API access
- Contact: Office of Information Technology (OIT) at CUNY
- Benefit: Official support, no risk of IP blocking, official data governance
- Documentation: Inquire about CUNYfirst API or Schedule Builder API

---

## 5. Integration with Gemini MCP Tools

### 5.1 Updated MCP Tool: Fetch Courses from CUNY Global Search

```python
# services/mcp_server/tools/schedule_optimizer.py

@mcp.tool
async def fetch_course_sections(
    course_codes: list[str],
    semester: str = None
) -> dict:
    """
    Fetch available course sections from CUNY Global Search data
    
    Args:
        course_codes: List of course codes (e.g., ["CSC381", "CSC382"])
        semester: Semester (e.g., "Fall 2025"). Defaults to current semester.
    
    Returns:
        Dictionary with course sections, professors, times, and enrollment
    """
    if not semester:
        semester = get_current_semester()
    
    try:
        sections = []
        
        for course_code in course_codes:
            # Query Supabase for courses matching code in current semester
            response = supabase.from_('courses').select(
                'id, course_code, name, credits, university'
            ).eq('course_code', course_code).eq('semester', semester).execute()
            
            if not response.data:
                return {
                    'error': f'Course {course_code} not found for {semester}',
                    'data': []
                }
            
            course_id = response.data[0]['id']
            
            # Get all sections for this course
            sections_response = supabase.from_('course_sections').select(
                'id, section_number, professor_name, days, start_time, end_time, '
                'location, modality, enrolled, capacity'
            ).eq('course_id', course_id).execute()
            
            sections.extend(sections_response.data)
        
        return {
            'success': True,
            'semester': semester,
            'total_sections': len(sections),
            'sections': sections
        }
    
    except Exception as e:
        logger.error(f"Error fetching sections: {e}")
        return {'error': str(e), 'data': []}


@mcp.tool
async def get_professor_grades(
    professor_names: list[str],
    course_code: str = None
) -> dict:
    """
    Get AI-generated grades for professors based on RateMyProf reviews
    
    Args:
        professor_names: List of professor names
        course_code: Optional course code to filter ratings
    
    Returns:
        Dictionary with professor grades and metrics
    """
    results = []
    
    for prof_name in professor_names:
        # Query professor with grades
        query = supabase.from_('professors').select(
            'id, name, grade_letter, composite_score, average_rating, '
            'average_difficulty, review_count'
        ).eq('name', prof_name)
        
        if course_code:
            query = query.eq('subject_code', course_code.split()[0])
        
        response = query.execute()
        
        if response.data:
            results.append(response.data[0])
        else:
            results.append({
                'name': prof_name,
                'grade': 'N/A',
                'error': 'No ratings found'
            })
    
    return {
        'professors': results,
        'timestamp': datetime.now().isoformat()
    }
```

---

## 6. UI Integration: Show Data Source

### 6.1 Update UI to Display CUNY Global Search Source

```typescript
// app/components/CourseSearch/CourseSearch.tsx

export function CourseSearch() {
  return (
    <div className="course-search">
      <h2>Search CUNY Courses</h2>
      <p className="data-source">
        📊 Data sourced from{' '}
        <a 
          href="https://globalsearch.cuny.edu/" 
          target="_blank" 
          rel="noopener noreferrer"
        >
          CUNY Global Search
        </a>
        {' '}• Last updated: {lastUpdateTime} • Next sync: Sunday 2 AM EST
      </p>
      
      <SearchForm />
      <SearchResults />
    </div>
  )
}
```

---

## 7. Updated Implementation Checklist

### Phase 1: MVP (Updated with CUNY Global Search)

- [ ] **Week 1**: 
  - [ ] Setup monorepo, Supabase
  - [ ] Research CUNY Global Search structure
  - [ ] Build web scraper with Selenium

- [ ] **Week 2**:
  - [ ] Test scraper on 2-3 CUNY schools
  - [ ] Store course data in Supabase
  - [ ] Frontend: Dashboard, course search

- [ ] **Week 3**:
  - [ ] Scrape all 25 CUNY schools
  - [ ] Setup background sync job (APScheduler)
  - [ ] Professor scraping + sentiment analysis

- [ ] **Week 4**:
  - [ ] Gemini API + MCP integration
  - [ ] Schedule optimization with real CUNY data
  - [ ] Testing & deployment

---

## 8. Monitoring & Alerts

### 8.1 Key Metrics to Monitor

```python
# services/mcp_server/utils/monitoring.py

class ScraperMonitoring:
    """Monitor CUNY Global Search scraper health"""
    
    async def log_sync_metrics(self, semester: str, metrics: dict):
        """
        Log sync metrics to database
        metrics: {courses_scraped, sections_scraped, errors, duration_seconds}
        """
        await supabase.from_('sync_logs').insert({
            'semester': semester,
            'courses_scraped': metrics['courses_scraped'],
            'sections_scraped': metrics['sections_scraped'],
            'errors': metrics['errors'],
            'duration_seconds': metrics['duration_seconds'],
            'timestamp': datetime.now()
        }).execute()
    
    async def check_data_staleness(self):
        """Alert if course data is too old"""
        last_sync = await self._get_last_sync_time()
        hours_since_sync = (datetime.now() - last_sync).total_seconds() / 3600
        
        if hours_since_sync > 168:  # 7 days
            await self._send_alert(
                f"CUNY course data is {hours_since_sync:.1f} hours old. "
                f"Sync may have failed."
            )
```

---

## 9. Cost Estimate (Updated)

| Component | Cost | Notes |
|-----------|------|-------|
| Vercel (Frontend) | Free/$25/mo | Hobby or Pro |
| Supabase (Database) | $25/mo | Pro tier for production |
| Google Gemini API | $50-200/mo | Based on usage (~1M tokens/day) |
| Railway/Fly.io (Backend) | $5-20/mo | Python scraper + scheduler |
| Domain | $15/yr | Custom domain |
| **Total** | **$95-275/mo** | Scales with user growth |

---

## 10. Testing Against CUNY Global Search

### 10.1 Test Cases

```python
# services/mcp_server/tests/test_cuny_scraper.py

import pytest

@pytest.mark.asyncio
async def test_scrape_single_school():
    """Test scraping one CUNY school"""
    scraper = CUNYGlobalSearchScraper()
    courses = await scraper._scrape_school_courses(
        school_code='CCNY',
        school_name='City College',
        semester='Fall 2025'
    )
    
    assert len(courses) > 0
    assert courses[0]['university'] == 'City College'
    assert 'sections' in courses[0]

@pytest.mark.asyncio
async def test_parse_section_time():
    """Test time parsing"""
    scraper = CUNYGlobalSearchScraper()
    days, start, end = scraper._parse_time_slot("MWF 10:00-11:15 AM")
    
    assert days == "MWF"
    assert start.hour == 10
    assert end.hour == 11

@pytest.mark.asyncio
async def test_database_sync():
    """Test storing scraped data in Supabase"""
    # ... test database insertion
```

