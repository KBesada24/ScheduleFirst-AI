# Technical Design: Fix CUNY Global Search Scraper

## Architecture Overview

The CUNY Global Search scraper sits in the data pipeline between user requests and the Supabase database. The current flow is broken because the scraper uses fabricated assumptions about the website. The fix rewrites the scraper's internal mechanics while preserving its external interface.

```
AI Chat → fetch_course_sections (MCP Tool)
              └── DataPopulationService.ensure_course_data()
                      └── sync_courses_job()
                              └── CUNYGlobalSearchScraper.scrape_semester_courses()
                                      ├── [BROKEN] ✗ GET ?school=CSI&semester=Spring+2026
                                      │            ✗ Wait for .course-listing (doesn't exist)
                                      │            ✗ Return 0 courses after 22s timeout
                                      │
                                      └── [FIXED]  ✓ Navigate to search.jsp
                                                   ✓ Select institution checkbox by label
                                                   ✓ Select term from #t_pd dropdown
                                                   ✓ Click "Next", wait for Step 2
                                                   ✓ Select subject from #subject_ld dropdown
                                                   ✓ Click "Search", wait for results
                                                   ✓ Parse <table class="classinfo"> rows
```

---

## Real CUNY Global Search Site Structure

### Step 1: Institution & Term Selection (`search.jsp`)

| Element | Type | HTML ID / Selector | Notes |
|---------|------|--------------------|-------|
| Institution | Checkboxes | `<span>` labels inside a list | Click by matching visible text |
| Term | Select dropdown | `#t_pd` / name: `term_name` | Values are numeric IDs (e.g. `1262` = 2026 Spring) |
| Next button | Button | `#search_new_spin` | Triggers POST to `CFSearchToolController` |

### Step 2: Search Criteria (loaded after Step 1 POST)

| Element | Type | HTML ID / Selector | Notes |
|---------|------|--------------------|-------|
| Subject | Select dropdown | `#subject_ld` / name: `subject_name` | Values are department codes (e.g. `CMSC`) |
| Course Career | Select dropdown | `#courseCareerId` / name: `courseCareer` | `UGRD`, `GRAD`, `DOCT` |
| Open Classes Only | Checkbox | `#open_class_id` / name: `open_class` | Checked by default |
| Search button | Button | `#search_new_spin` | Same ID, triggers search POST |
| Instructor | Text input | `#instructorNameId` | Under "Additional Search Criteria" accordion |
| Start/End Time | Text inputs | `#meetingStartTextId` | Under "Additional Search Criteria" accordion |

### Step 3: Results Page

Results display in an accordion pattern:

```
"69 class section(s) found"
  └── [Institution] College of Staten Island  (contentDivImg_inst0)
        └── [Course] CSC 126 - Introduction to Computer Science  (contentDivImg0)
              └── <table class="classinfo">
                    <tr>
                      <td>CLASS (section ID like 33047)</td>
                      <td>SECTION</td>
                      <td>DAYS & TIMES</td>
                      <td>ROOM</td>
                      <td>INSTRUCTOR</td>
                      <td>INSTRUCTION MODE</td>
                      <td>MEETING DATES</td>
                      <td>STATUS (Open/Closed icon)</td>
                      <td>COURSE TOPIC</td>
                    </tr>
              </table>
```

- Institutions are collapsed by default → expand via `subjectToggleInst(N)` JavaScript
- Courses within institutions are also collapsed → expand via `subjectToggle(N)` JavaScript
- Section links (CLASS column) are clickable `<a>` tags with detailed info

---

## Component Breakdown

### Modified File

**[`cuny_global_search_scraper.py`](file:///home/kbesada/Code/ScheduleFirst-AI/services/mcp_server/services/cuny_global_search_scraper.py)**

#### New/Modified Methods

| Method | Change | Purpose |
|--------|--------|---------|
| `_navigate_step1()` | **New** | Navigate to search.jsp, select institution checkbox, select term, click Next |
| `_navigate_step2()` | **New** | Select subject dropdown, uncheck "Open Only", click Search |
| `_resolve_term_id()` | **New** | Read `#t_pd` options and match semester string to term ID |
| `_get_available_subjects()` | **New** | Read `#subject_ld` options for the current school/term |
| `_parse_results_page()` | **New** | Expand accordions, find `.classinfo` tables, extract sections |
| `_scrape_school_courses()` | **Modified** | Replace URL-based navigation with Step 1 → Step 2 → parse flow |
| `_parse_course_element()` | **Replaced** | Rewrite to parse `classinfo` table rows instead of `course-listing` divs |
| `_parse_section_element()` | **Replaced** | Rewrite to parse `classinfo` `<td>` cells instead of fabricated selectors |
| `_get_cuny_schools()` | **Modified** | Update institution names to match real form labels |
| `scrape_semester_courses()` | **Minor changes** | Keep interface, adjust internal call flow |

#### Unchanged Methods (behavioral compatibility)

| Method | Why unchanged |
|--------|---------------|
| `_get_chrome_options()` | Chrome config is correct |
| `_safe_close_driver()` | Cleanup logic is correct |
| `_parse_time_slot()` | Time parsing regex is reusable (format may differ slightly) |
| `_parse_enrollment()` | Enrollment parsing may still apply |
| `close()` | Cleanup is correct |

### Unchanged Files

| File | Why unchanged |
|------|---------------|
| `sync_cuny_courses.py` | Calls `scrape_semester_courses(semester, university)` — interface stays the same |
| `data_population_service.py` | Calls `sync_courses_job()` — interface stays the same |
| `data_freshness_service.py` | Only checks `sync_metadata` — unrelated |
| `schedule_optimizer.py` | MCP tool entry point — unrelated |
| `supabase_service.py` | DB operations — unrelated |
| All test files | Tests mock the scraper — they test the caller logic, not the scraper internals |

---

## New Navigation Flow (Pseudocode)

```python
async def _scrape_school_courses(self, school_name, semester):
    # 1. Navigate to search.jsp
    self.driver.get("https://globalsearch.cuny.edu/CFGlobalSearchTool/search.jsp")
    
    # 2. Step 1: Select institution
    checkbox = find_checkbox_by_label(school_name)
    checkbox.click()
    
    # 3. Step 1: Select term
    term_id = self._resolve_term_id(semester)  # "Spring 2026" → "1262"
    Select(driver.find_element(By.ID, "t_pd")).select_by_value(term_id)
    
    # 4. Click Next
    driver.find_element(By.ID, "search_new_spin").click()
    wait_for_step2_to_load()
    
    # 5. Step 2: Get available subjects
    subjects = self._get_available_subjects()
    
    all_courses = []
    for subject_code, subject_name in subjects:
        # 6. Select subject
        Select(driver.find_element(By.ID, "subject_ld")).select_by_value(subject_code)
        
        # 7. Uncheck "Open Classes Only"
        open_checkbox = driver.find_element(By.ID, "open_class_id")
        if open_checkbox.is_selected():
            open_checkbox.click()
        
        # 8. Click Search
        driver.find_element(By.ID, "search_new_spin").click()
        wait_for_results()
        
        # 9. Parse results
        courses = self._parse_results_page(school_name, semester)
        all_courses.extend(courses)
        
        # 10. Go back via "Modify Search" for next subject
        driver.find_element(By.ID, "modify_search_btn_or_link").click()
        wait_for_step2_to_reload()
    
    return all_courses
```

---

## Institution Name Mapping

The `_get_cuny_schools()` method must return names exactly matching the checkbox labels on the search.jsp page:

| Current (Wrong) | Correct Label |
|-----------------|---------------|
| City College | City College |
| Hunter College | Hunter College |
| Queens College | Queens College |
| Baruch College | Baruch College |
| Brooklyn College | Brooklyn College |
| Lehman College | Lehman College |
| York College | York College |
| College of Staten Island | College of Staten Island |
| John Jay College | John Jay College |
| Medgar Evers College | Medgar Evers College |
| New York City College of Technology | NYC College of Technology |
| Borough of Manhattan Community College | Borough of Manhattan CC |
| Bronx Community College | Bronx CC |
| Hostos Community College | Hostos CC |
| Kingsborough Community College | Kingsborough CC |
| LaGuardia Community College | LaGuardia CC |
| Queensborough Community College | Queensborough CC |
| *(missing)* | Graduate Center |
| *(missing)* | Guttman CC |
| *(missing)* | Macaulay Honors College |
| *(missing)* | School of Journalism |
| *(missing)* | School of Labor & Urban Studies |
| *(missing)* | School of Law |
| *(missing)* | School of Medicine |
| *(missing)* | School of Professional Studies |
| *(missing)* | School of Public Health |

> [!IMPORTANT]
> The school codes (`CCNY`, `HUNTER`, `CSI`, etc.) in `_get_cuny_schools()` are no longer needed — institution selection is done via checkbox label text, not URL parameters. The `code` field can be removed or repurposed as an internal identifier.

---

## Error Handling Strategy

| Scenario | Handling |
|----------|----------|
| Institution checkbox not found | Log warning, raise `ScrapingError` with available institutions |
| Term not found in dropdown | Log warning, raise `ScrapingError` with available terms |
| Subject dropdown has no options | Log warning, return empty list (school may have no courses for term) |
| Results page fails to load (timeout) | Log warning, return empty list for this subject, continue to next |
| Accordion expand fails | Try JavaScript `subjectToggle()` calls, fall back to parsing page source |
| `classinfo` table structure unexpected | Log parse error, skip row, continue |
| WebDriver crash | Close driver, reset to `None`, raise `ScrapingError` |

---

## Performance Considerations

- **Subject-level granularity**: Scraping all subjects for one school requires N form submissions (one per subject). This is slower than a hypothetical "all subjects" search but matches site behavior.
- **Rate limiting**: Maintain existing `scraper_request_delay` (2 seconds) between subject searches.
- **WebDriver reuse**: Reuse the same WebDriver session across subjects within a school to avoid Chrome startup overhead.
- **Timeout tuning**: Set per-step timeouts (10s for form loads, 30s for results) rather than one 15s global timeout.

---

## Testing Strategy

### Existing Unit Tests (no changes needed)
All tests in `mcp_server/tests/` mock the scraper at the interface level. They test the caller logic (data population, freshness, MCP tools), not the scraper internals:
```bash
python -m pytest mcp_server/tests/ -v --tb=short
```

### Manual Integration Test
After the rewrite, test against the live CUNY Global Search:
1. Run a scrape for `College of Staten Island`, `Spring 2026`, one subject (e.g. Computer Science)
2. Verify > 0 courses returned with section data
3. Verify section data includes: instructor name, days/times, room, instruction mode
4. Check logs for clean navigation with no timeout warnings
