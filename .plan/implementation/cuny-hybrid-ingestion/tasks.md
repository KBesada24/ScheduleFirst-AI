# Implementation Tasks: Browser-Use Primary Ingestion with Selenium Fallback

## Summary

This plan introduces Browser-Use as the primary CUNY ingestion path while preserving existing interfaces and using Selenium as fallback. The implementation is staged behind feature flags so rollout and rollback are operationally safe.

No database schema changes are required. Existing MCP tool and service signatures remain stable.

---

## Phase 1: Foundation and Runtime Controls

### TASK-001: Add Browser-Use Dependency
**Refs**: FR-001, Dependencies  
**Estimated time**: 20 minutes

- [x] Add `browser-use` to `services/requirements/base.txt`
- [x] Update dependency lock/source file as needed by project workflow
- [x] Verify import in venv: `from browser_use import Agent, Browser`
- [x] Confirm no conflicts with existing Selenium dependencies

### TASK-002: Add Feature Flags in Configuration
**Refs**: FR-005, NFR-004  
**Estimated time**: 30 minutes

- [x] Add `CUNY_BROWSER_USE_ENABLED` setting (default `false`)
- [x] Add `CUNY_SELENIUM_FALLBACK_ENABLED` setting (default `true`)
- [x] Add `CUNY_SHADOW_MODE` setting (default `false`)
- [x] Add `CUNY_BROWSER_USE_TIMEOUT` setting (default `45`)
- [x] Add `CUNY_BROWSER_USE_MAX_RETRIES` setting (default `1`)
- [x] Update deployment/env docs with new vars

### TASK-003: Define Internal Connector Result Contract
**Refs**: FR-002, Design contract section  
**Estimated time**: 30 minutes

- [x] Create a typed result model/class for source outputs (`success`, `source`, `courses`, `warnings`, `error`)
- [x] Ensure contract maps cleanly to current sync/data population behavior
- [x] Add lightweight unit tests for result object defaults/serialization

---

## Phase 2: Browser-Use Connector

### TASK-004: Implement Browser-Use Connector Skeleton
**Refs**: FR-001  
**Estimated time**: 1.5 hours

- [x] Create `mcp_server/services/browser_use_cuny_connector.py`
- [x] Implement class with `fetch_courses(semester, university, subject_code=None)`
- [x] Add timeout wrapper and structured exception handling
- [x] Return contract-compliant result on all code paths (success/failure)

### TASK-005: Implement CUNY Form Navigation with Browser-Use
**Refs**: FR-001  
**Estimated time**: 2 hours

- [x] Navigate to `search.jsp`
- [x] Select institution and term
- [x] Progress to Step 2 and select subject(s)
- [x] Trigger search and wait for result page stability
- [x] Add retries within configured retry budget

### TASK-006: Implement Result Extraction and Normalization
**Refs**: FR-001, FR-002  
**Estimated time**: 2 hours

- [x] Extract course and section fields from results page structures
- [x] Normalize to current `sync_courses_job` expected schema
- [x] Preserve support for subject-scoped and full-subject iteration paths
- [x] Emit warnings for partial row parse failures instead of aborting run

### TASK-007: Add Connector Unit Tests (Mocked)
**Refs**: NFR-004  
**Estimated time**: 1.5 hours

- [x] Success path test
- [x] Timeout path test
- [x] Subject no-match test
- [x] Empty-result with warning path test

---

## Phase 3: Orchestration and Fallback

### TASK-008: Implement Ingestion Orchestrator
**Refs**: FR-003, FR-004, FR-007  
**Estimated time**: 2 hours

- [x] Create `mcp_server/services/cuny_ingestion_orchestrator.py`
- [x] Wire primary call to Browser-Use connector
- [x] Add explicit fallback trigger rules
- [x] Add single fallback attempt budget
- [x] Return normalized source result

### TASK-009: Integrate Selenium as Fallback Source
**Refs**: FR-003  
**Estimated time**: 1 hour

- [x] Reuse existing `CUNYGlobalSearchScraper` path as fallback
- [x] Map fallback output to shared connector result contract
- [x] Add warning metadata when fallback is used
- [x] Respect `CUNY_SELENIUM_FALLBACK_ENABLED`

### TASK-010: Add Empty-Result Quality Gate
**Refs**: FR-004  
**Estimated time**: 1 hour

- [x] Add helper to evaluate empty Browser-Use results
- [x] Use baseline/history where available
- [x] Trigger fallback only on defined suspect-empty conditions
- [x] Unit test quality-gate decision matrix

---

## Phase 4: Service and Job Integration

### TASK-011: Wire Orchestrator into `sync_courses_job`
**Refs**: FR-002  
**Estimated time**: 1 hour

- [x] Replace direct scraper call with orchestrator call
- [x] Preserve function signature and return payload
- [x] Preserve existing insert/update metadata behavior
- [x] Ensure cleanup semantics remain valid

### TASK-012: Wire Feature Flag Path in `DataPopulationService`
**Refs**: FR-002, FR-005  
**Estimated time**: 1 hour

- [x] Route course sync through Browser-Use path when enabled
- [x] Keep legacy behavior when disabled
- [x] Preserve existing lock/cache/freshness behavior
- [x] Keep `PopulationResult` contract unchanged

### TASK-013: Propagate Source Metadata to Tool Responses
**Refs**: FR-006  
**Estimated time**: 30 minutes

- [x] Extend metadata in `fetch_course_sections` response
- [x] Add fields for source and fallback usage
- [x] Confirm downstream compatibility with current API clients

---

## Phase 5: Testing and Validation

### TASK-014: Update/Add Service-Level Tests
**Refs**: NFR-004  
**Estimated time**: 1.5 hours

- [x] Add tests for Browser-Use primary success path
- [x] Add tests for fallback-on-failure behavior
- [x] Add tests for fallback-disabled degraded path
- [x] Keep existing `test_data_population_service` expectations passing

### TASK-015: Regression Suite Run
**Estimated time**: 10 minutes

- [x] Run targeted suite for data population, mcp tools, and scraper-related tests
- [x] Confirm no regressions in existing degraded-success semantics

### TASK-016: Staging Smoke Validation
**Estimated time**: 30–60 minutes

- [ ] Enable Browser-Use in staging only
- [ ] Execute representative queries (single subject + mixed subjects)
- [ ] Confirm metadata source attribution and fallback behavior in logs
- [ ] Validate non-zero course retrieval for known available subjects

---

## Phase 6: Rollout

### TASK-017: Shadow Mode Comparison (Optional but Recommended)
**Refs**: FR-005  
**Estimated time**: 1 day observation

- [ ] Enable `CUNY_SHADOW_MODE=true` in staging
- [ ] Collect parity metrics between Browser-Use and Selenium results
- [ ] Investigate significant extraction deltas before full cutover

### TASK-018: Production Cutover
**Estimated time**: 30 minutes

- [ ] Set `CUNY_BROWSER_USE_ENABLED=true`
- [ ] Keep Selenium fallback enabled initially
- [ ] Monitor degraded responses, timeout rates, and source mix

### TASK-019: Stabilization and Decision Gate
**Estimated time**: 2–3 days observation

- [ ] Evaluate whether fallback invocation rate is acceptable
- [ ] Decide whether to keep dual-path permanently or make Selenium emergency-only

---

## Dependencies Graph

```
TASK-001 ─┐
TASK-002 ─┼── TASK-004 ─┬── TASK-005 ─┬── TASK-006 ─┬── TASK-008 ─┬── TASK-011 ─┬── TASK-014 ─┬── TASK-015 ─┬── TASK-016
TASK-003 ─┘             │             │             │             │             │             │             │
                        └─────────────┴─────────────┴── TASK-007  │             │             │             └── TASK-018
                                                                  └── TASK-009 ─┘             └── TASK-013 ───────┘

TASK-010 depends on TASK-008 and TASK-009
TASK-012 depends on TASK-008 and TASK-011
TASK-017 depends on TASK-016
TASK-019 depends on TASK-018
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Browser-Use cannot reliably interact with specific CUNY controls | Medium | High | Keep Selenium fallback enabled and feature-flagged rollback |
| New dependency introduces runtime/environment friction | Medium | Medium | Stage-first rollout and strict health checks |
| Empty-result false positives trigger unnecessary fallback | Medium | Medium | Tune quality gate with baseline-aware logic |
| Increased latency due to dual-path fallback | Medium | Medium | Single fallback attempt + strict timeouts |
| Test instability due to browser tooling mocks | Medium | Low | Isolate connector tests with deterministic mocks |

---

## Rollback Plan

1. Set `CUNY_BROWSER_USE_ENABLED=false`
2. Keep `CUNY_SELENIUM_FALLBACK_ENABLED=true`
3. Restart API/background workers

This immediately restores Selenium-only behavior without code revert or DB changes.
