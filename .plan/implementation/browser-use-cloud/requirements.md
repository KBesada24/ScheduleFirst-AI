# Requirements: Browser-Use Cloud Section Extraction Reliability

## Overview

The current Browser-Use ingestion path can detect course codes but often returns zero sections, even when sections are available on CUNY Global Search. This creates false negatives and degrades user trust. This specification defines requirements to make Browser-Use Cloud task execution deterministic, section-focused, and observable, while preserving Selenium fallback as a reliability safety net.

**Problem signals observed**:
- Browser-Use primary path frequently returns courses with empty sections.
- Task outcomes are not consistently validated against section-level completeness.
- Cloud task diagnostics (task state, steps, logs) are underutilized for triage and retry decisions.

---

## Functional Requirements

### FR-001: Cloud v2 Task Lifecycle Orchestration
**Type**: Ubiquitous  
**Statement**: The ingestion connector SHALL execute Browser-Use through Cloud API v2 task lifecycle calls, including task creation, status polling, and task detail retrieval.  
**Acceptance Criteria**:
- [ ] Connector creates tasks via POST `/api/v2/tasks` with authenticated API key.
- [ ] Connector polls task status via GET `/api/v2/tasks/{task_id}` until terminal state.
- [ ] Connector handles terminal states (`finished`, `stopped`) explicitly.
- [ ] Connector records task identifiers and terminal status in logs/metadata.

### FR-002: Structured Output Contract for Course + Sections
**Type**: Ubiquitous  
**Statement**: The Browser-Use task SHALL request and validate a structured output contract containing course-level and section-level data.  
**Acceptance Criteria**:
- [ ] Task request includes a structured output schema requiring `courses[]` with `sections[]`.
- [ ] Parsed output is normalized into existing internal course/section format.
- [ ] If output is non-JSON or malformed JSON, connector attempts controlled recovery parsing.
- [ ] If parsing fails, connector returns an unsuccessful source result with actionable error text.

### FR-003: Section-Completeness Success Gate
**Type**: State-driven  
**Statement**: WHILE Browser-Use reports matched courses, the ingestion layer SHALL treat zero extracted sections as incomplete unless explicit no-section evidence is present.  
**Acceptance Criteria**:
- [ ] Source result includes a warning when courses are present but all `sections` arrays are empty.
- [ ] Orchestrator can use section-completeness signals in fallback decisions.
- [ ] Metadata includes section count totals for downstream response consistency.

### FR-004: Prompted Multi-Stage Extraction Behavior
**Type**: Event-driven  
**Statement**: WHEN a Browser-Use task is created, the task prompt SHALL instruct the agent to complete multi-stage extraction: filter → enumerate courses → expand courses → extract all section rows.  
**Acceptance Criteria**:
- [ ] Prompt explicitly requires opening/expanding course rows before completion.
- [ ] Prompt explicitly forbids stopping at course-code-only extraction.
- [ ] Prompt instructs return of only structured JSON output.

### FR-005: Cloud-Aware Retry and Fallback Triggering
**Type**: Event-driven  
**Statement**: WHEN Browser-Use fails by timeout, terminal stop, malformed output, or section-incomplete result, the orchestrator SHALL trigger Selenium fallback according to configured policy.  
**Acceptance Criteria**:
- [ ] Timeout and cloud terminal failures map to deterministic fallback reasons.
- [ ] Section-incomplete outcomes can trigger fallback for subject-scoped queries.
- [ ] Fallback metadata is propagated to MCP tool responses.

### FR-006: Task Diagnostics Retrieval for Triage
**Type**: Event-driven  
**Statement**: WHEN Browser-Use task execution fails or is flagged incomplete, the system SHALL be able to retrieve cloud task diagnostics for investigation.  
**Acceptance Criteria**:
- [ ] Task ID is persisted in logs and metadata for each run.
- [ ] Failure path supports retrieval of task logs via GET `/api/v2/tasks/{task_id}/logs`.
- [ ] Failure classification includes one of: navigation failure, filter mismatch, expansion failure, parse failure, timeout.

### FR-007: Subject/Query Normalization Compatibility
**Type**: Optional  
**Statement**: WHERE subject aliases are used (for example CSC vs CMSC), the Browser-Use request context SHALL include normalized hints to improve section discovery.  
**Acceptance Criteria**:
- [ ] Query context includes both original and normalized subject hints where applicable.
- [ ] Logs identify normalized subject used for task construction.
- [ ] Behavior remains backward-compatible for exact subject codes.

### FR-008: User-Facing Response Truthfulness
**Type**: Ubiquitous  
**Statement**: The chat response layer SHALL align final user-visible conclusions with latest successful tool result, not model-only narrative.  
**Acceptance Criteria**:
- [ ] If tool result indicates courses/sections found, final text does not claim none are available.
- [ ] If no tool call occurred on explicit course-code query, backend can trigger deterministic fetch before final response.
- [ ] Response metadata includes source and fallback usage for transparency.

---

## Non-Functional Requirements

### NFR-001: End-to-End Latency Budget
**Statement**: The Browser-Use primary path SHALL complete within configured SLA bounds and fail fast enough to preserve acceptable request latency with fallback.  
**Acceptance Criteria**:
- [ ] Cloud task polling timeout is configurable and enforced.
- [ ] Timeout values are externally configurable via environment settings.
- [ ] Fallback activation does not create indefinite hangs.

### NFR-002: Observability and Auditability
**Statement**: The ingestion path SHALL emit structured logs sufficient to reconstruct Cloud task behavior and decision points.  
**Acceptance Criteria**:
- [ ] Logs include: query inputs, task ID, status progression, extracted course count, extracted section count.
- [ ] Logs include fallback decision reason when fallback is used.
- [ ] Log messages are machine-filterable for incident triage.

### NFR-003: Reliability Under External Variability
**Statement**: The system SHALL remain robust to transient cloud/API failures and CUNY UI variability.  
**Acceptance Criteria**:
- [ ] Retry policy is bounded by max retries.
- [ ] Connector degrades gracefully to unsuccessful result rather than crashing process.
- [ ] Selenium fallback remains available when enabled.

### NFR-004: Backward Compatibility
**Statement**: The implementation SHALL preserve existing external interfaces used by data population and MCP tools.  
**Acceptance Criteria**:
- [ ] `IngestionSourceResult` contract remains compatible with current callers.
- [ ] No breaking change to MCP tool function signatures.
- [ ] Existing test suites for orchestration/tools continue to pass after adaptation.

---

## Constraints

- Must use Browser-Use Cloud API v2 endpoints and API key authentication.
- Must preserve current orchestrator contract and fallback capability.
- Must not require frontend changes for baseline reliability improvements.
- Must remain compatible with current Supabase insert/upsert path.

---

## Dependencies

- Valid Browser-Use Cloud account with credits.
- `BROWSER_USE_API_KEY` configured in runtime environment.
- Network access to `https://api.browser-use.com` and CUNY Global Search.
- Existing Selenium fallback scraper operational.
- Existing metadata propagation path in data population and MCP tool responses.

---

## Out of Scope

- Replacing Selenium fallback implementation.
- Redesigning frontend UX beyond truthful text consistency.
- Building a separate scheduling recommendation model.
- Cost optimization across Browser-Use billing plans.
- Full migration to CDP-only custom browser automation.
