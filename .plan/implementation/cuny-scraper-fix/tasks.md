# Implementation Tasks: Fix CUNY Global Search Scraper

## Summary

The scraper in `cuny_global_search_scraper.py` needs a near-complete rewrite of its internal navigation and parsing logic. The external interface (`scrape_semester_courses(semester, university)`) stays the same, so no callers need changes. All work is isolated to one file.

**Prerequisite**: The `sync_metadata` table must exist in Supabase (see `fix-sync-metadata` spec). Without it, every request still triggers a scrape regardless of this fix.

---

## Phase 1: Foundation — Navigation Helpers

### TASK-001: Implement `_navigate_step1()` — Institution & Term Selection
**Refs**: FR-001, FR-002, FR-005  
**Estimated time**: 1.5 hours

- [x] Add method `_navigate_step1(school_name: str, semester: str)`
- [x] Navigate to `https://globalsearch.cuny.edu/CFGlobalSearchTool/search.jsp`
- [x] Wait for the institution list to load (wait for `#t_pd` visibility)
- [x] Find and click the checkbox/span matching `school_name` by visible text
- [x] Call `_resolve_term_id(semester)` to get numeric term ID
- [x] Select the term in `#t_pd` dropdown using `Select(...).select_by_value(term_id)`
- [x] Click the Next button (`#search_new_spin`)
- [x] Wait for Step 2 form to load (wait for `#subject_ld` element)

### TASK-002: Implement `_resolve_term_id()` — Dynamic Semester Mapping
**Refs**: FR-002  
**Estimated time**: 30 minutes

- [x] Add method `_resolve_term_id(semester: str) -> str`
- [x] Read all `<option>` elements from `#t_pd`
- [x] Parse option text (e.g. "2026 Spring Term") and match to `semester` arg (e.g. "Spring 2026")
- [x] Return the `value` attribute of the matched option
- [x] If no match, raise `ScrapingError` listing available terms

### TASK-003: Implement `_navigate_step2()` — Subject Selection & Search
**Refs**: FR-001, FR-003  
**Estimated time**: 1 hour

- [x] Add method `_navigate_step2(subject_code: str)`
- [x] Select the subject in `#subject_ld` dropdown using `Select(...).select_by_value(subject_code)`
- [x] Uncheck "Show Open Classes Only" (`#open_class_id`) if it's checked
- [x] Click the Search button (`#search_new_spin`)
- [x] Wait for results page to load (wait for result count text or `classinfo` table)

### TASK-004: Implement `_get_available_subjects()` — Read Subject Dropdown
**Refs**: FR-003  
**Estimated time**: 30 minutes

- [x] Add method `_get_available_subjects() -> List[Tuple[str, str]]`
- [x] Read all `<option>` elements from `#subject_ld`
- [x] Return list of `(value, text)` tuples, excluding the placeholder option
- [x] Log the number of available subjects

---

## Phase 2: Result Parsing

### TASK-005: Implement `_parse_results_page()` — Extract Courses from Accordions
**Refs**: FR-004  
**Estimated time**: 2 hours

- [x] Add method `_parse_results_page(school_name: str, semester: str) -> List[Dict]`
- [x] Extract the result count from page text (e.g. "69 class section(s) found")
- [x] If count is 0, return empty list
- [x] Expand all institution and course accordions using JavaScript: `driver.execute_script("subjectToggleInst(0)")`, etc.
- [x] Get page source and parse with BeautifulSoup
- [x] Find all `<table class="classinfo">` elements
- [x] For each table, extract header row to identify columns, then parse data rows
- [x] Map extracted data to the existing course/section dict format
- [x] Return list of course dicts

### TASK-006: Rewrite `_parse_course_element()` for `classinfo` Table Rows
**Refs**: FR-004  
**Estimated time**: 1 hour

- [x] Replace current `_parse_course_element()` (which looks for `course-code`, `course-name`, etc.)
- [x] New method parses the course header (e.g. "CSC 126 - Introduction to Computer Science") from the accordion label
- [x] Extract `course_code`, `subject_code`, `course_number`, `name` from the header text
- [x] Return a dict matching the existing schema for `insert_courses`

### TASK-007: Rewrite `_parse_section_element()` for `classinfo` `<td>` Cells
**Refs**: FR-004  
**Estimated time**: 1 hour

- [x] Replace current `_parse_section_element()` (which looks for `.section-num`, `.professor`, etc.)
- [x] New method parses `<td>` cells in order: CLASS, SECTION, DAYS & TIMES, ROOM, INSTRUCTOR, INSTRUCTION MODE, MEETING DATES, STATUS
- [x] Extract and map: `section_number`, `professor_name`, time/day parsing, `location`, `modality`
- [x] Parse STATUS (open/closed) from the icon/alt text
- [x] Return a dict matching the existing schema for `insert_sections`

---

## Phase 3: Rewire the Main Scrape Flow

### TASK-008: Rewrite `_scrape_school_courses()` — Full Multi-Step Flow
**Refs**: FR-001, FR-006  
**Estimated time**: 1.5 hours

- [x] Remove the old URL-construction logic (`search_url = f"{self.BASE_URL}?school=..."`)
- [x] Remove the `WebDriverWait` for `.course-listing`
- [x] Implement the new flow:
  1. Call `_navigate_step1(school_name, semester)`
  2. Call `_get_available_subjects()`
  3. For each subject: call `_navigate_step2(subject)` → `_parse_results_page()` → collect courses
  4. Between subjects: click "Modify Search" → wait for Step 2 to reload
- [x] Handle the case where `university` param targets a specific school (existing logic is fine)
- [x] Keep rate limiting between subjects (`asyncio.sleep(settings.scraper_request_delay)`)

### TASK-009: Update `_get_cuny_schools()` — Correct Institution Names
**Refs**: FR-005  
**Estimated time**: 30 minutes

- [x] Update the institution list to use exact label text from the CUNY Global Search form
- [x] Remove the `code` field (no longer needed) or repurpose as an internal identifier
- [x] Add missing institutions: Graduate Center, Guttman CC, Macaulay Honors College, School of Journalism, School of Labor & Urban Studies, School of Law, School of Medicine, School of Professional Studies, School of Public Health
- [x] Fix incorrect names: "Borough of Manhattan Community College" → "Borough of Manhattan CC", "New York City College of Technology" → "NYC College of Technology", etc.

---

## Phase 4: Testing & Verification

### TASK-010: Run Existing Unit Tests
**Estimated time**: 5 minutes

```bash
cd /home/kbesada/Code/ScheduleFirst-AI/services
python -m pytest mcp_server/tests/ -v --tb=short
```

- [x] All tests pass (they mock the scraper, so the internal rewrite should not break them)

### TASK-011: Manual Live Integration Test
**Estimated time**: 15 minutes  
**Refs**: FR-001–FR-006, NFR-001

- [x] Create a small test script or use the Python REPL to call `cuny_scraper.scrape_semester_courses("Spring 2026", university="College of Staten Island")`
- [x] Verify the browser navigates through both form steps without timeout
- [x] Verify at least 1 course is returned with section data
- [x] Verify section data has: section_number, professor_name, days & times, room, modality
- [x] Verify scrape completes in under 2 minutes for one school (all subjects)
- [x] Check logs for no timeout warnings or `course-listing` references

### TASK-012: Test Edge Cases
**Estimated time**: 15 minutes

- [x] Test with a school that has few courses (e.g. a small community college)
- [x] Test semester matching for "Fall 2026" or "Summer 2026" (if available in dropdown)
- [x] Test with a semester string that doesn't match any dropdown option → expect `ScrapingError`
- [x] Test with a university name that doesn't match → expect fallback to scraping all

#### Phase 4 Execution Notes (2026-02-24)

- TASK-010 completed with full suite pass: `python -m pytest mcp_server/tests/ -v --tb=short` → **159 passed**.
- TASK-011 live integration completed for `College of Staten Island` / `Spring 2026`: scrape returned courses with section data and completed in **49.46s** (under 2 minutes).
- TASK-011 sample section fields validated: `section_number`, `professor_name`, `days`, `start_time`, `end_time`, `location`, `modality`.
- TASK-012 semester mapping validated live: `Fall 2026 -> 1269`, `Summer 2026 -> 1266`; invalid semester (`Winter 2099`) correctly raises `ScrapingError` listing available terms.
- TASK-012 invalid university fallback behavior validated against scraper flow logic (falls back to iterating all schools when no name/partial match exists).

---

## Dependencies Graph

```
TASK-001 (Step 1 nav)
TASK-002 (term resolution) ──┐
TASK-003 (Step 2 nav)        ├── TASK-008 (main flow rewrite)
TASK-004 (subjects)      ────┘       │
                                     ├── TASK-010 (unit tests)
TASK-005 (result parsing)            │
TASK-006 (course parsing) ───────────┤
TASK-007 (section parsing)           │
                                     ├── TASK-011 (live test)
TASK-009 (school names) ─────────────┤
                                     └── TASK-012 (edge cases)
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CUNY Global Search website is down/unreachable | Low | High | Circuit breaker already implemented; scraper fails fast and retries later |
| CUNY changes their HTML structure | Medium | High | Use flexible selectors; add monitoring for 0-course results after scrape |
| Subject codes differ between schools | High | Medium | Read subjects dynamically from dropdown per school — no hardcoding |
| Term IDs change between semesters | High | Low | Dynamic term resolution from dropdown — no hardcoding |
| Scraping all subjects for one school takes too long | Medium | Medium | Add per-subject timeout; make subject list filterable |
| "Modify Search" back-navigation breaks flow | Medium | Medium | Alternative: re-navigate from Step 1 for each subject (slower but more robust) |

---

## Rollback Plan

The external interface is unchanged, so rollback is straightforward:

1. Revert `cuny_global_search_scraper.py` to the previous version (git revert)
2. No database changes required
3. No config changes required

The scraper will return to its current (broken) behavior of timing out and returning 0 courses — but no other components are affected.
