# Requirements: Browser-Use Primary Ingestion with Selenium Fallback

## Overview

The current course ingestion flow relies on Selenium and is sensitive to UI drift, timing, and school/subject selection edge cases. This spec replaces the primary scraping path with a Browser-Use powered workflow while preserving the current system interfaces (`ensure_course_data`, `sync_courses_job`, MCP tool responses). Selenium remains as a controlled fallback for resilience and rollback safety.

The intent is to reduce operational fragility and speed up iteration by using an LLM-oriented browser automation framework, without forcing schema changes, tool contract changes, or broad caller rewrites.

**How discovered**: On-demand requests intermittently return empty datasets with degraded quality even when requests succeed operationally. Existing logs show subject-scope mismatches and browser interaction brittleness as primary causes.

---

## Functional Requirements

### FR-001: Primary Browser-Use Connector
**Type**: Ubiquitous  
**Statement**: The system SHALL implement a Browser-Use based connector as the primary course ingestion engine for CUNY Global Search.  
**Acceptance Criteria**:
- [ ] A new Browser-Use connector exists under `mcp_server/services` and supports `semester`, `university`, and optional `subject_code`
- [ ] The connector returns course/section data in the same shape currently expected by `sync_courses_job`
- [ ] The connector can complete Step 1 (school/term), Step 2 (subject), and results extraction for at least one target school in staging
- [ ] The connector has configurable timeout and retry settings

### FR-002: Interface Compatibility
**Type**: Ubiquitous  
**Statement**: The system SHALL preserve existing upstream and downstream interfaces while swapping the ingestion engine.  
**Acceptance Criteria**:
- [ ] `DataPopulationService.ensure_course_data()` signature is unchanged
- [ ] `sync_courses_job()` signature is unchanged
- [ ] `fetch_course_sections` tool response structure remains unchanged
- [ ] No Supabase schema migration is required

### FR-003: Selenium Fallback Path
**Type**: Event-driven  
**Statement**: WHEN Browser-Use ingestion fails, times out, or returns a suspect empty result, the system SHALL invoke the existing Selenium scraper as fallback (if enabled).  
**Acceptance Criteria**:
- [ ] Fallback trigger conditions are explicit and centralized
- [ ] Fallback execution is skipped when disabled by config
- [ ] Fallback outcome is captured in response metadata/warnings
- [ ] If fallback succeeds, ingestion is treated as successful with warning context

### FR-004: Quality Gate for Empty Results
**Type**: State-driven  
**Statement**: WHILE validating Browser-Use results, the system SHALL apply a quality gate before accepting empty outputs for subject-scoped requests.  
**Acceptance Criteria**:
- [ ] Empty result + known historical baseline > 0 triggers fallback
- [ ] Empty result + unknown baseline does not hard-fail (returns warning path)
- [ ] Quality gate behavior is unit-testable and isolated from connector internals

### FR-005: Feature-Flagged Rollout
**Type**: State-driven  
**Statement**: WHILE Browser-Use rollout is in progress, the system SHALL use feature flags to control primary path, fallback path, and shadow comparison mode.  
**Acceptance Criteria**:
- [ ] `CUNY_BROWSER_USE_ENABLED` controls Browser-Use primary path
- [ ] `CUNY_SELENIUM_FALLBACK_ENABLED` controls fallback availability
- [ ] `CUNY_SHADOW_MODE` enables side-by-side comparison without changing primary response source
- [ ] Flags are loaded from environment via existing settings system

### FR-006: Source Attribution and Warnings
**Type**: Ubiquitous  
**Statement**: The system SHALL include ingestion-source attribution and warning context in downstream tool metadata.  
**Acceptance Criteria**:
- [ ] Metadata includes source (`browser_use`, `selenium_fallback`, `browser_use+selenium`)
- [ ] Metadata includes `fallback_used` boolean
- [ ] Warning text identifies primary/fallback failure reasons when degraded

### FR-007: Graceful Degradation
**Type**: Unwanted behavior  
**Statement**: IF both Browser-Use and Selenium fallback fail, THEN the system SHALL return a valid degraded response rather than an uncaught exception.  
**Acceptance Criteria**:
- [ ] Request returns structured result with `data_quality: degraded`
- [ ] Error context appears in warnings/errors without stack traces leaking to users
- [ ] API endpoint remains healthy (HTTP 200 for tool call envelope)

---

## Non-Functional Requirements

### NFR-001: Reliability
**Statement**: Browser-Use primary path shall reduce empty-result incidents caused by UI interaction brittleness versus current Selenium-only baseline.  
**Acceptance Criteria**:
- [ ] Over a staged sample run, Browser-Use primary has fewer empty-result anomalies than Selenium-only baseline
- [ ] No increase in total tool-call error rate

### NFR-002: Performance
**Statement**: Browser-Use primary path shall maintain acceptable latency for on-demand requests.  
**Acceptance Criteria**:
- [ ] Subject-scoped requests complete within configured timeout budget
- [ ] Fallback is only invoked when needed to avoid unnecessary double work

### NFR-003: Observability
**Statement**: Ingestion source and failure mode shall be observable in logs and metrics.  
**Acceptance Criteria**:
- [ ] Logs include primary source outcome, fallback decision, and final source used
- [ ] Existing job/request metrics remain intact
- [ ] Slow path and degraded responses are clearly detectable

### NFR-004: Testability
**Statement**: The new orchestration and connector behavior shall be covered by unit tests without requiring live browser runs.  
**Acceptance Criteria**:
- [ ] Connector interfaces are mockable in tests
- [ ] Fallback decisions are covered by unit tests
- [ ] Existing tests around `ensure_course_data` and tool calls continue passing

---

## Constraints

- Must keep existing public service/tool interfaces stable
- Must not require database schema changes
- Must preserve compatibility with existing background job orchestration
- Must support rollback by config (disable Browser-Use path)
- Must not remove Selenium path during initial rollout

---

## Dependencies

- `browser-use` Python package and runtime prerequisites
- Existing Selenium scraper implementation for fallback
- Existing `DataPopulationService`, `sync_courses_job`, and Supabase insert pipeline
- Existing logging, circuit breaker, and metrics infrastructure

---

## Out of Scope

- Rebuilding the entire ingestion architecture into a new microservice
- Supabase schema redesign
- Frontend changes
- Replacing all scraping logic for unrelated sources (e.g., professor/reviews)
- Removing Selenium fallback in the first implementation wave
