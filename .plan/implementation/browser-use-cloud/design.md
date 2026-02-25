# Technical Design: Browser-Use Cloud Section Extraction Reliability

## Architecture Overview

This design upgrades the current Browser-Use connector from a local SDK-first execution model to a Cloud v2 task lifecycle model with structured output enforcement and reliability guardrails.

```
AI Chat Request
  └── MCP Tool: fetch_course_sections
      └── DataPopulationService.ensure_course_data()
          └── CunyIngestionOrchestrator.fetch_courses()
              ├── Primary: BrowserUseCunyConnector (Cloud v2)
              │    1) POST /api/v2/tasks
              │    2) Poll GET /api/v2/tasks/{task_id}
              │    3) Parse structured output
              │    4) Emit source result + quality signals
              │
              └── Fallback: Selenium CUNY Scraper
                   (trigger on timeout/failure/incomplete sections)
```

Core design principle: course-level detection is not enough; section-level completeness drives quality decisions.

---

## Data Model

### Ingestion Source Result (Existing Contract, Extended Usage)

```python
IngestionSourceResult:
  success: bool
  source: str
  courses: List[Dict[str, Any]]
  warnings: List[str]
  error: Optional[str]
  fallback_used: bool
```

No schema break is required; section-quality and cloud diagnostics are represented via warnings and orchestration metadata.

### Structured Output Target (Cloud Task)

```json
{
  "courses": [
    {
      "course_code": "CSC 126",
      "title": "Introduction to Computer Science",
      "college": "College of Staten Island",
      "term": "Spring 2026",
      "sections": [
        {
          "section_number": "01",
          "class_number": "33047",
          "instruction_mode": "In Person",
          "professor": "Jane Doe",
          "days": "MW",
          "time": "10:10 AM - 11:25 AM",
          "location": "2N-217",
          "status": "Open"
        }
      ]
    }
  ]
}
```

---

## Workflow Design

### 1) Task Creation

Create Browser-Use Cloud task with:
- `task`: multi-stage extraction instructions.
- `startUrl`: CUNY Global Search URL.
- `allowedDomains`: restricted to CUNY domain.
- `structuredOutput`: strict schema for courses and sections.
- tuned options: `maxSteps`, LLM choice, vision mode.

### 2) Task Polling

Poll task detail endpoint until terminal state:
- terminal success path: `status=finished`.
- terminal failure path: `status=stopped` or timeout.

### 3) Output Normalization

Normalization strategy:
- accept native dict/list JSON output.
- recover JSON from fenced/plain text where possible.
- coerce/clean course and section arrays.
- compute extraction quality signals:
  - total courses
  - total sections
  - courses_with_zero_sections

### 4) Quality Gate and Fallback Decision

Primary Browser-Use result categories:
- **Healthy**: courses found and sections found.
- **Empty-valid**: no courses found (subject truly unavailable).
- **Incomplete**: courses found but sections all empty.
- **Failed**: timeout, terminal stop, parse failure, API error.

Fallback policy:
- Always fallback on failed category when enabled.
- Fallback on incomplete category for scoped queries (course code/subject).
- Preserve warning chain and explicit fallback reason.

### 5) Response Consistency Layer

At chat response assembly:
- trust latest successful tool payload over unconstrained model narrative.
- when explicit course-code query has no tool call, invoke deterministic fetch guard.
- ensure final text never contradicts tool-truth.

---

## Component Breakdown

### services/mcp_server/services/browser_use_cuny_connector.py

Responsibilities:
- Build Cloud v2 task request.
- Poll task completion.
- Retrieve output and normalize to ingestion course format.
- Emit warnings for section-incomplete outcomes.

Key design updates:
- Cloud-first execution path when API key exists.
- bounded retry + timeout handling.
- robust JSON recovery parser for cloud output text edge-cases.

### services/mcp_server/services/cuny_ingestion_orchestrator.py

Responsibilities:
- source arbitration (Browser-Use primary, Selenium fallback).
- fallback trigger logic based on success + quality signals.

Key design updates:
- include section-quality aware fallback reasoning.
- preserve current metadata propagation behavior.

### services/mcp_server/services/data_population_service.py

Responsibilities:
- execute ingestion orchestration and persist courses/sections.
- propagate source/warnings/fallback metadata.

Key design updates:
- include section-count and cloud task context in debug logging.

### services/mcp_server/tools/schedule_optimizer.py

Responsibilities:
- expose fetch tool output to model and chat layer.

Key design updates:
- ensure metadata includes source truth and warnings for downstream response synthesis.

### services/api_server.py

Responsibilities:
- final user-facing response text generation.

Key design updates:
- deterministic anti-contradiction behavior anchored to latest tool result.
- optional auto-fetch fallback for explicit code queries with zero tool calls.

---

## Error Handling Strategy

| Failure Mode | Detection | Handling | Fallback |
|---|---|---|---|
| Cloud task create fails | non-2xx POST response | mark Browser-Use failed with error text | Yes |
| Poll timeout | elapsed > configured timeout | mark failed (`timeout`) | Yes |
| Task stopped/unsuccessful | terminal status != finished | mark failed (`terminal_status`) | Yes |
| Output parse failure | JSON normalization failure | mark failed (`parse_failure`) | Yes |
| Courses with zero sections | quality gate | mark incomplete + warning | Conditional (Yes for scoped queries) |

---

## Security Considerations

- Browser-Use API key must come from environment configuration only.
- Do not log raw secrets.
- Restrict Browser-Use task domain via `allowedDomains`.
- Avoid embedding user credentials in prompts.

---

## Performance Considerations

- Poll interval should be configurable to balance API load vs responsiveness.
- Task timeout should be tuned for CUNY multi-step extraction complexity.
- One retry maximum by default to contain latency and cost.
- Fallback should trigger early on clearly incomplete extraction patterns.

---

## Testing Strategy

### Unit Tests

- Connector success path with structured output payload.
- Connector timeout/terminal failure path.
- Connector malformed output parsing path.
- Incomplete sections warning path.

### Orchestrator Tests

- fallback on Browser-Use failure.
- fallback on section-incomplete scoped query.
- no fallback for accepted empty baseline case.

### Tool/Response Tests

- metadata propagation includes source/warnings/fallback flags.
- final chat text does not contradict successful section results.

### Runtime Validation

- Execute representative queries (`CSC 126`, subject-only, no-result control).
- Compare Browser-Use section counts against Selenium in shadow mode.
- Confirm fallback reason visibility in logs.
