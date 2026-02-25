# Technical Design: Browser-Use Primary Ingestion with Selenium Fallback

## Architecture Overview

This design introduces Browser-Use as the primary automation engine for CUNY course ingestion while preserving the current service boundaries and data contracts. Selenium remains a fallback path during rollout and as a safety valve.

```
AI Chat → fetch_course_sections (MCP Tool)
              └── DataPopulationService.ensure_course_data()
                      └── sync_courses_job()
                              └── CUNY Ingestion Orchestrator (new)
                                      ├── [PRIMARY] BrowserUseCunyConnector
                                      │       └── Browser-Use agent workflow:
                                      │            search.jsp → Step 1 → Step 2 → results
                                      │
                                      ├── Quality Gate
                                      │       ├── accept result
                                      │       └── trigger fallback
                                      │
                                      └── [FALLBACK] CUNYGlobalSearchScraper (existing Selenium)
```

### Why this architecture

- Minimal caller impact: no public interface changes
- Safer rollout: fallback path already exists and is battle-tested in current codebase
- Better operational control: feature flags select primary/fallback behavior at runtime

---

## Component Breakdown

### Modified Files

| File | Change | Purpose |
|------|--------|---------|
| `mcp_server/services/data_population_service.py` | Add connector selection and fallback orchestration | Route ingestion through Browser-Use primary with Selenium fallback |
| `background_jobs/jobs/sync_cuny_courses.py` | Replace direct scraper call with orchestrator call | Keep job contract unchanged while changing source strategy |
| `mcp_server/config.py` | Add Browser-Use and rollout flags | Runtime control over new behavior |
| `mcp_server/tools/schedule_optimizer.py` | Add source metadata propagation | Visibility into which source produced results |
| `requirements/base.txt` | Add Browser-Use dependency | Enable runtime support |

### New Files

| File | Purpose |
|------|---------|
| `mcp_server/services/browser_use_cuny_connector.py` | Browser-Use based school/term/subject navigation and extraction |
| `mcp_server/services/cuny_ingestion_orchestrator.py` | Primary/fallback orchestration and quality gate |
| `mcp_server/tests/test_cuny_ingestion_orchestrator.py` | Unit tests for source routing and fallback decisions |
| `mcp_server/tests/test_browser_use_cuny_connector.py` | Unit tests for connector behavior with mocks |

### Unchanged Files

| File | Why unchanged |
|------|---------------|
| `mcp_server/services/cuny_global_search_scraper.py` | Retained as fallback implementation |
| `mcp_server/services/supabase_service.py` | Data insert/update contract unchanged |
| DB migrations / Supabase schema | No data model changes required |

---

## Data Flow and Contracts

### Existing ingestion contract (preserved)

`sync_courses_job` expects:
- `semester: Optional[str]`
- `university: Optional[str]`
- `subject_code: Optional[str]`

and receives:
- `courses: List[Dict[str, Any]]` where each course contains optional `sections` list

This remains unchanged.

### New internal connector contract

```python
class IngestionSourceResult:
    success: bool
    source: str                    # "browser_use" | "selenium"
    courses: List[Dict[str, Any]]
    warnings: List[str]
    error: Optional[str]


class CunyIngestionConnector(Protocol):
    async def fetch_courses(
        self,
        semester: str,
        university: Optional[str] = None,
        subject_code: Optional[str] = None,
    ) -> IngestionSourceResult:
        ...
```

The orchestrator consumes this contract and returns a normalized result compatible with existing job flow.

---

## Browser-Use Connector Design

### Core responsibilities

1. Initialize browser/session using Browser-Use runtime
2. Navigate CUNY Global Search form steps
3. Apply school/term/subject selection
4. Extract course and section data from result tables
5. Normalize output to existing schema
6. Return structured warnings/errors (no uncaught exceptions)

### Navigation outline

```
1) Open search.jsp
2) Select university checkbox/label
3) Resolve and select term from #t_pd
4) Click Next (#search_new_spin)
5) Resolve subject list from #subject_ld
6) Apply subject filter if provided
7) Click Search
8) Parse classinfo tables + accordion sections
```

### Parsing strategy

- Reuse current extraction schema assumptions from Selenium implementation
- Prefer robust selector lookup with graceful missing-field handling
- Keep parser tolerant: partial row parse emits warnings, not full failure

---

## Fallback and Quality Gate

### Trigger rules

Fallback is invoked if any of the following occur on Browser-Use primary:

- hard failure (exception/timeout)
- explicit unsuccessful result
- empty result in subject-scoped request with positive baseline history

### Non-trigger cases

- empty result with unknown baseline (warn, return primary result)
- fallback disabled by config

### Fallback flow

```
primary = browser_use.fetch_courses(...)
if should_fallback(primary):
    fallback = selenium.fetch_courses(...)
    if fallback.success:
        return fallback with warnings(primary.error)
return primary
```

---

## Feature Flags and Configuration

Additions in `Settings`:

| Env Var | Type | Default | Purpose |
|--------|------|---------|---------|
| `CUNY_BROWSER_USE_ENABLED` | bool | `false` | Enables Browser-Use primary |
| `CUNY_SELENIUM_FALLBACK_ENABLED` | bool | `true` | Enables Selenium fallback |
| `CUNY_SHADOW_MODE` | bool | `false` | Runs Browser-Use and Selenium for comparison |
| `CUNY_BROWSER_USE_TIMEOUT` | int | `45` | Connector timeout seconds |
| `CUNY_BROWSER_USE_MAX_RETRIES` | int | `1` | Retry count before fallback |

---

## Logging, Metrics, and Metadata

### Logging additions

- Log source attempt start/end
- Log fallback decision with reason
- Log source used in final result

### Response metadata additions

`fetch_course_sections` metadata gains:

```json
{
  "source": "browser_use",
  "fallback_used": false,
  "auto_populated": true
}
```

Possible values:
- `browser_use`
- `selenium_fallback`
- `browser_use+selenium`
- `none` (degraded all-source failure)

---

## Testing Strategy

### Unit tests (new)

- Orchestrator:
  - primary success, no fallback
  - primary failure, fallback success
  - both fail → degraded result
  - fallback disabled behavior
  - quality gate behavior for empty datasets

- Browser-Use connector:
  - successful extraction path (mocked browser interactions)
  - timeout path
  - subject filter no-match path

### Regression tests (existing)

- Keep `test_data_population_service.py` passing by preserving method signatures and return shape
- Keep `test_mcp_tools.py` behavior stable for degraded/success outcomes

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Browser-Use interaction drift on CUNY UI changes | Medium | High | Keep Selenium fallback + robust selector strategy |
| Runtime dependency complexity | Medium | Medium | Feature-flag rollout + canary environment |
| Increased request latency in fallback cases | Medium | Medium | Strict timeout/retry budgets and single fallback attempt |
| Inconsistent extraction shape | Low | High | Enforce normalization contract and parser unit tests |

---

## Rollback Plan

1. Set `CUNY_BROWSER_USE_ENABLED=false`
2. Keep `CUNY_SELENIUM_FALLBACK_ENABLED=true`
3. Restart services

This immediately restores Selenium-only ingestion path with no code rollback or database changes.
