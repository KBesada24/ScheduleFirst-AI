# Requirements: Fix CUNY Global Search Scraper Timeout

## Overview

The CUNY Global Search scraper in `cuny_global_search_scraper.py` times out after ~22 seconds and returns 0 courses every time it is invoked. The scraper was written with fabricated assumptions about the CUNY Global Search website — the URL pattern, form interaction model, and CSS selectors are all incorrect. This spec defines the requirements for rewriting the scraper to match the real website structure, so that course data can actually be scraped from CUNY Global Search.

**How discovered**: When the AI agent searches for a class (e.g. "CSC 126 at College of Staten Island"), the system triggers the CUNY scraper, which navigates to a non-existent URL, waits for DOM elements that don't exist, and times out — returning `Total courses: 0`.

---

## Functional Requirements

### FR-001: Multi-Step Form Navigation
**Type**: Ubiquitous  
**Statement**: The scraper SHALL navigate the CUNY Global Search website using its real multi-step form flow: Step 1 (select institution + term) → click "Next" → Step 2 (select subject + options) → click "Search".  
**Acceptance Criteria**:
- [ ] Scraper navigates to `https://globalsearch.cuny.edu/CFGlobalSearchTool/search.jsp`
- [ ] Scraper selects institution(s) using checkbox matching by label text
- [ ] Scraper selects the term from the `#t_pd` dropdown
- [ ] Scraper clicks the "Next" button (`#search_new_spin`) and waits for Step 2 to load
- [ ] Scraper selects the subject from the `#subject_ld` dropdown
- [ ] Scraper clicks the "Search" button and waits for results

### FR-002: Dynamic Semester Code Resolution
**Type**: Event-driven  
**Statement**: WHEN a semester string like "Spring 2026" is provided, the scraper SHALL dynamically read the `#t_pd` dropdown options to resolve the correct numeric term ID (e.g. `1262`), rather than hardcoding term codes.  
**Acceptance Criteria**:
- [ ] Scraper reads all `<option>` elements from the `#t_pd` select element
- [ ] Scraper matches the provided semester string (e.g. "Spring 2026") to the corresponding option text (e.g. "2026 Spring Term")
- [ ] If no match is found, the scraper raises a clear `ScrapingError` with available terms listed
- [ ] No hardcoded term ID values exist in the scraper

### FR-003: Dynamic Subject Code Resolution
**Type**: Event-driven  
**Statement**: WHEN scraping courses for a school, the scraper SHALL read the available subjects from the `#subject_ld` dropdown and select the appropriate one.  
**Acceptance Criteria**:
- [ ] Scraper reads all `<option>` elements from the `#subject_ld` select element
- [ ] When scraping all courses, scraper iterates over all available subjects
- [ ] When a specific subject prefix is requested (e.g. "CSC"), scraper fuzzy-matches to the closest available subject code (e.g. "CMSC")
- [ ] If no match is found, the scraper logs a warning and skips the subject

### FR-004: Correct Result Parsing
**Type**: Event-driven  
**Statement**: WHEN the results page loads, the scraper SHALL parse course data from `<table class="classinfo">` elements inside accordion sections, not from non-existent `course-listing` div elements.  
**Acceptance Criteria**:
- [ ] Scraper waits for the results indicator text (e.g. "N class section(s) found")
- [ ] Scraper expands all accordion sections (institutions and courses) using JavaScript clicks
- [ ] Scraper finds all `<table class="classinfo">` elements
- [ ] For each table, scraper extracts: CLASS (section ID), SECTION, DAYS & TIMES, ROOM, INSTRUCTOR, INSTRUCTION MODE, MEETING DATES, and STATUS
- [ ] Parsed data maps to the existing `CourseCreate` and `CourseSectionCreate` Pydantic models

### FR-005: Correct Institution Selection
**Type**: Ubiquitous  
**Statement**: The scraper SHALL select institutions by matching label text on the Step 1 form, not by appending fabricated school codes to a URL query string.  
**Acceptance Criteria**:
- [ ] The `_get_cuny_schools()` method returns institution names that exactly match the checkbox labels on the CUNY Global Search form (e.g. "College of Staten Island", "Borough of Manhattan CC")
- [ ] Institution selection uses Selenium checkbox clicks, not URL parameters
- [ ] All 26 institutions on the live CUNY Global Search form are represented

### FR-006: Form POST Submission
**Type**: Ubiquitous  
**Statement**: The scraper SHALL interact with the CUNY Global Search via its real POST-based form controller (`/CFGlobalSearchTool/CFSearchToolController`), not via fabricated GET query-string URLs.  
**Acceptance Criteria**:
- [ ] Scraper does not construct URLs with `?school=...&semester=...` query parameters
- [ ] All form submissions occur via Selenium button clicks that trigger the real form POST
- [ ] The scraper handles JavaScript-rendered content by waiting for proper DOM elements

---

## Non-Functional Requirements

### NFR-001: Scrape Latency
**Statement**: A single-school, single-subject scrape SHALL complete in under 30 seconds, and a multi-subject full-school scrape SHALL complete in under 5 minutes.  
**Acceptance Criteria**:
- [ ] Single subject scrape (e.g. Computer Science at CSI) completes in < 30 seconds
- [ ] A timeout is enforced so the scraper never hangs indefinitely
- [ ] Timeout duration is configurable via settings

### NFR-002: Error Resilience
**Statement**: IF a form interaction fails or a page element is missing, the scraper SHALL log the error with context and continue to the next subject/school rather than crashing.  
**Acceptance Criteria**:
- [ ] Missing dropdown options produce a logged warning, not a crash
- [ ] Unchanged form elements from site redesigns produce a `ScrapingError` with helpful context
- [ ] The circuit breaker pattern (already implemented) continues to protect against cascading failures

### NFR-003: WebDriver Lifecycle
**Statement**: The scraper SHALL properly manage the Chrome WebDriver lifecycle — reuse across subjects within a school session, but close on error and recreate as needed.  
**Acceptance Criteria**:
- [ ] WebDriver is initialized once per scrape session (not per subject)
- [ ] WebDriver is closed cleanly on completion or error
- [ ] `_safe_close_driver()` still works correctly

---

## Constraints

- Must use the existing Selenium + BeautifulSoup stack (no framework changes)
- Must remain compatible with the existing `sync_cuny_courses.py` job interface (`scrape_semester_courses(semester, university)`)
- Must not break existing mocked unit tests in `test_data_freshness_service.py`, `test_data_population_service.py`, etc.
- Must respect CUNY server resources — maintain existing rate limiting delays between requests

---

## Dependencies

- Chrome / Chromium + ChromeDriver installed on the host (for Selenium)
- `webdriver_manager` Python package (already in requirements)
- Network access to `https://globalsearch.cuny.edu/`
- CUNY Global Search website availability (external dependency, not under our control)
- `sync_metadata` table in Supabase (addressed by the `fix-sync-metadata` spec — prerequisite)

---

## Out of Scope

- Changing the Supabase schema or Pydantic course/section models
- Modifying the `sync_cuny_courses.py` job orchestration logic
- Adding a CUNY API integration (no official API exists)
- Changing the data freshness TTL values
- Frontend/UI changes
- RateMyProfessors scraper fixes
