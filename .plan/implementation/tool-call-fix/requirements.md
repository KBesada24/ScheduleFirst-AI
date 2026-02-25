# Requirements: Gemini Tool Call Fix (`thought_signature`)

## Overview

The AI chat endpoint (`POST /api/chat/message`) crashes with a 500 error after a tool call completes. The root cause is a protocol mismatch between the `ollama` Python client library and the Gemini 3 API: the Ollama client strips the `thought_signature` metadata that Gemini requires when sending tool results back in a multi-turn conversation. This spec covers replacing the Ollama client with Google's official `google-genai` SDK, which handles `thought_signature` automatically.

---

## Functional Requirements

### FR-001: Successful Tool Call Round-Trip
**Type**: Event-driven  
**Statement**: WHEN the AI model determines a tool call is necessary, the system SHALL execute the tool AND send the result back to Gemini in a format that preserves `thought_signature` context, resulting in a final natural-language response.  
**Acceptance Criteria**:
- [ ] Sending a message that triggers `fetch_course_sections` returns a text response with course data — no 500 error
- [ ] Sending a message that triggers `generate_optimized_schedule` completes successfully
- [ ] Sending a message that triggers `get_professor_grade` completes successfully
- [ ] Sending a message that triggers `compare_professors` completes successfully

### FR-002: Multi-Turn Tool Call Loop
**Type**: State-driven  
**Statement**: WHILE the model response contains tool calls AND fewer than 6 calls have been made, the system SHALL continue executing tools and feeding results back to the model.  
**Acceptance Criteria**:
- [ ] Up to 6 sequential tool calls resolve without error
- [ ] The final response is always a natural-language string from the model

### FR-003: Context Preservation Across Tool Turns
**Type**: Ubiquitous  
**Statement**: The system SHALL preserve the complete model response object (including `thought_signature`) when building follow-up messages, using `response.candidates[0].content` rather than manually reconstructing message parts.  
**Acceptance Criteria**:
- [ ] No `400 Bad Request — Function call is missing a thought_signature` error occurs
- [ ] Conversation history from prior assistant turns does not trigger signature errors

### FR-004: Existing Tool Dispatch Unchanged
**Type**: Ubiquitous  
**Statement**: The system SHALL preserve all existing tool-routing logic, context defaults (university, semester), and validation rules when migrating to the new SDK.  
**Acceptance Criteria**:
- [ ] `fetch_course_sections` argument normalization (`course_code` → `course_codes`) continues to work
- [ ] Missing university or semester still returns a structured validation error to the model
- [ ] Context defaults (university, semester from history) are still injected correctly

### FR-005: Sentiment Analyzer Compatibility
**Type**: Ubiquitous  
**Statement**: The sentiment analyzer service SHALL use the same `google-genai` SDK for consistency, removing the last dependency on the `ollama` Python client.  
**Acceptance Criteria**:
- [ ] `sentiment_analyzer.py` no longer imports from `ollama`
- [ ] Sentiment analysis of professor reviews continues to produce valid results

### FR-006: Graceful Error Handling
**Type**: If-Then  
**Statement**: IF the Gemini API call fails (network error, rate limit, invalid key), THEN the system SHALL return a structured 500 error with a descriptive message rather than propagating a cryptic exception.  
**Acceptance Criteria**:
- [ ] Missing or invalid `GEMINI_API_KEY` logs a clear error on startup
- [ ] API errors are caught and wrapped in the existing `HTTPException(status_code=500)` pattern

---

## Non-Functional Requirements

### NFR-001: Response Latency (No Regression)
**Statement**: The system SHALL add no more than 100ms of latency overhead compared to the current (broken) Ollama client path for equivalent requests.  
**Acceptance Criteria**:
- [ ] Average chat response time (excluding tool execution) remains under 3 seconds

### NFR-002: Backward Compatibility (Tool API Surface)
**Statement**: The system SHALL not change the JSON shape of the `POST /api/chat/message` request or response.  
**Acceptance Criteria**:
- [ ] Frontend `useChat` hook requires zero changes
- [ ] Response fields `message`, `suggestions`, `context`, `tool_calls_made` remain unchanged

### NFR-003: Configuration via Environment Variables
**Statement**: The system SHALL read the Gemini API key and model name from environment variables, not hardcoded values.  
**Acceptance Criteria**:
- [ ] `GEMINI_API_KEY` env var controls authentication
- [ ] `GEMINI_MODEL` env var (default: `gemini-3-flash-preview`) controls model selection

---

## Constraints

- Python ≥ 3.11 (already enforced by `pyproject.toml`)
- Must use `google-genai` ≥ 1.0.0 (new unified SDK, not deprecated `google-generativeai`)
- The `GEMINI_API_KEY` is already present in `services/.env.local`
- No changes to the frontend (`src/`) are required
- No changes to MCP tools (`mcp_server/tools/`) are required

---

## Dependencies

- `google-genai` PyPI package (new dependency)
- Gemini API key with access to `gemini-3-flash-preview` model
- Existing Supabase, scraper, and MCP tool infrastructure (unchanged)

---

## Out of Scope

- Streaming responses (SSE) for the chat endpoint — not currently implemented
- Switching from REST to gRPC with the Gemini API
- Replacing the sentiment model with a Gemini-based solution (separate concern)
- Changes to the frontend chat UI components
- Changes to schedule optimization, course scraping, or professor data logic
