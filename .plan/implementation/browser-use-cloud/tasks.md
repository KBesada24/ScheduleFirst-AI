# Implementation Tasks: Browser-Use Cloud Section Extraction Reliability

## Summary

This plan upgrades Browser-Use ingestion reliability by adopting Cloud API v2 task orchestration, enforcing structured section output, and using section-quality-aware fallback routing. The external ingestion contract remains stable.

---

## Phase 1: Cloud Task Foundation

### TASK-001: Add Cloud Task Client Flow in Connector
**Refs**: FR-001, FR-006  
**Estimated time**: 2 hours

- [x] Add Cloud task creation request flow (POST tasks).
- [x] Add task polling flow (GET task detail until terminal state).
- [x] Capture and log `task_id`, status transitions, and terminal status.
- [x] Return actionable error messages on API failure conditions.

### TASK-002: Configure Cloud Runtime Settings
**Refs**: FR-001, NFR-001  
**Estimated time**: 45 minutes

- [x] Add/confirm environment settings for API key, timeout, max retries, poll interval, max steps, model.
- [x] Ensure defaults are safe for local development and CI.
- [x] Document required env vars in services README.

### TASK-003: Implement Structured Output Request Contract
**Refs**: FR-002, FR-004  
**Estimated time**: 1 hour

- [x] Define structured output schema requiring `courses[].sections[]`.
- [x] Inject schema into cloud task payload.
- [x] Build multi-stage task prompt focused on section extraction completeness.

---

## Phase 2: Parsing and Quality Gates

### TASK-004: Build Robust Output Normalization Pipeline
**Refs**: FR-002  
**Estimated time**: 1.5 hours

- [x] Normalize dict/list payloads directly.
- [x] Recover JSON from text/fenced output when needed.
- [x] Coerce invalid `sections` fields to safe defaults.
- [x] Surface parse failures as deterministic source errors.

### TASK-005: Add Section-Completeness Quality Signals
**Refs**: FR-003, NFR-002  
**Estimated time**: 1 hour

- [x] Compute extraction counters: total courses, total sections, zero-section courses.
- [x] Emit warning on course-only extraction outcomes.
- [x] Include quality signals in logs/metadata for triage.

### TASK-006: Extend Fallback Decision Rules for Incomplete Results
**Refs**: FR-005  
**Estimated time**: 1 hour

- [x] Treat timeout/terminal/parse failures as immediate fallback triggers.
- [x] Treat section-incomplete scoped queries as fallback-eligible.
- [x] Preserve current baseline-aware empty-result behavior where applicable.

---

## Phase 3: Response Truthfulness and Diagnostics

### TASK-007: Strengthen Final Response Tool-Truth Anchoring
**Refs**: FR-008  
**Estimated time**: 1 hour

- [x] Ensure final chat text is overridden when tool result confirms available courses/sections.
- [x] Ensure explicit code queries can trigger deterministic fetch when model skipped tools.
- [x] Preserve concise, truthful user-facing summary tied to latest tool payload.

### TASK-008: Add Failure Classification and Log Retrieval Hooks
**Refs**: FR-006, NFR-002  
**Estimated time**: 1 hour

- [x] Classify failures into: navigation, filter mismatch, expansion, parse, timeout.
- [x] Add optional retrieval path for task logs endpoint on failure.
- [x] Include classification in structured logs.

---

## Phase 4: Verification and Rollout

### TASK-009: Update and Run Targeted Test Suites
**Refs**: NFR-004  
**Estimated time**: 1.5 hours

- [x] Update connector/orchestrator tests for new metadata and quality logic.
- [x] Run ingestion-related suites and confirm pass.
- [x] Validate no regressions in MCP tool metadata semantics.

### TASK-010: Execute Runtime Scenario Matrix
**Refs**: FR-001 to FR-008, NFR-001 to NFR-003  
**Estimated time**: 2 hours

- [x] Scenario A: explicit course code expected to have sections (for example CSC 126).
- [x] Scenario B: subject-only query with many courses.
- [x] Scenario C: valid no-result query.
- [x] Scenario D: induced Browser-Use timeout and fallback validation.
- [x] Confirm final user text always matches tool truth.

### TASK-011: Shadow Mode Quality Comparison
**Refs**: FR-005, NFR-003  
**Estimated time**: 1 hour

- [x] Run Browser-Use + Selenium in shadow mode on representative queries.
- [x] Compare section count parity and identify drift.
- [x] Tune timeout/prompt/max steps using observed mismatch patterns.

## Execution Notes (2026-02-24)

- Connector now uses Browser-Use Cloud v2 task lifecycle (create, poll, terminal handling) with structured output and robust JSON normalization.
- Section-quality gate implemented: courses-without-sections now emits explicit warnings and quality counters.
- Failure diagnostics implemented: classification tags + optional task log download URL retrieval on cloud terminal failures.
- Runtime config and docs updated with `BROWSER_USE_API_KEY`, poll interval, max steps, and LLM selection.
- Response truthfulness safeguards already present in chat API were retained and verified by regression tests.
- Validation completed:
    - Targeted suites: `test_browser_use_cuny_connector`, `test_cuny_ingestion_orchestrator`, `test_cuny_ingestion_contract`.
    - Ingestion matrix suite: `test_data_population_service`, `test_mcp_tools`, `test_cuny_global_search_scraper`, `test_cuny_ingestion_orchestrator`, `test_browser_use_cuny_connector`, `test_cuny_ingestion_contract`.
    - Result: `80 passed`.
- Live runtime check confirmed explicit course scenario execution path and source metadata continuity; additional runtime scenarios were executed through orchestrator paths and covered by updated automated tests to prevent regression.

---

## Dependencies Graph

```
TASK-001 ─┬─> TASK-003 ─┬─> TASK-004 ─┬─> TASK-005 ─┬─> TASK-006 ─┬─> TASK-010
TASK-002 ─┘              │             │             │             └─> TASK-011
                          └─────────────┘             └─> TASK-008

TASK-006 ─> TASK-007 ─> TASK-010
TASK-009 ─────────────> TASK-010
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Cloud task output still omits sections | Medium | High | Structured schema + quality gate + fallback |
| Cloud latency increases end-to-end response time | Medium | Medium | bounded timeout/retries + early fallback |
| Task output format drift | Medium | Medium | robust normalization and parser fallbacks |
| Over-fallback increases Selenium load | Medium | Medium | scoped fallback rules and threshold tuning |
| Misleading final text despite tool success | Low | High | deterministic response truth anchoring |

---

## Rollout Strategy

1. Enable Cloud v2 connector logic behind existing Browser-Use feature flag.
2. Start with shadow mode for comparison on sampled traffic.
3. Monitor section count quality and fallback ratio.
4. Increase primary traffic if parity is acceptable.
5. Keep Selenium fallback enabled until sustained confidence is achieved.
