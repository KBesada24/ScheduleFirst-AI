# Requirements: Ollama LLM Migration

## Overview
Migrate all LLM calls in the ScheduleFirst-AI Python backend from the `google-generativeai` SDK to the `ollama` Python library, using the Ollama Cloud API (`https://ollama.com`) with Bearer token authentication.

## Functional Requirements

### FR-001: Chat Endpoint Tool Calling
**Type**: Ubiquitous
**Statement**: The system shall use the Ollama Python library's `Client.chat()` with JSON-schema tool definitions for the `/api/chat/message` endpoint, replacing all `genai.protos.FunctionDeclaration` and `genai.protos.Schema` usage.
**Acceptance Criteria**:
- [ ] Tool declarations use JSON schema dict format (not protobuf)
- [ ] Multi-turn agent loop correctly appends tool results with `role: 'tool'`
- [ ] Maximum of 6 tool calls per conversation turn (unchanged behavior)
- [ ] All 4 tools work: `fetch_course_sections`, `generate_optimized_schedule`, `get_professor_grade`, `compare_professors`

### FR-002: Chat History & System Instructions
**Type**: Ubiquitous
**Statement**: The system shall pass chat history and system instructions via a flat `messages` list (Ollama format), replacing Gemini's stateful `model.start_chat(history=...)` pattern.
**Acceptance Criteria**:
- [ ] System instruction sent as `{'role': 'system', ...}` message
- [ ] History messages mapped: `user` → `user`, `assistant` → `assistant`
- [ ] Current user message appended after history
- [ ] Context extraction from history still works identically

### FR-003: Sentiment Analysis
**Type**: Ubiquitous
**Statement**: The system shall use `ollama.Client.chat()` with `format='json'` for sentiment analysis, replacing `genai.GenerativeModel.generate_content()`.
**Acceptance Criteria**:
- [ ] Single review analysis returns valid JSON with sentiment scores
- [ ] Batch review analysis returns valid JSON array
- [ ] JSON code block stripping is no longer needed (Ollama returns clean JSON)
- [ ] Fallback to neutral scores on error (unchanged behavior)

### FR-004: Ollama Cloud Authentication
**Type**: Event-driven
**Statement**: WHEN the `OLLAMA_API_KEY` environment variable is set, the system shall include a `Bearer` token in the `Authorization` header for all Ollama API requests.
**Acceptance Criteria**:
- [ ] `Client` instantiated with `headers={'Authorization': 'Bearer <key>'}` when key is present
- [ ] Client works without API key for local Ollama (fallback)

### FR-005: Configuration
**Type**: Ubiquitous
**Statement**: The system shall read `OLLAMA_HOST`, `OLLAMA_MODEL`, and `OLLAMA_API_KEY` from environment variables via the existing `pydantic-settings` `Settings` class.
**Acceptance Criteria**:
- [ ] `GEMINI_API_KEY` removed as a required field
- [ ] `OLLAMA_HOST` defaults to `https://ollama.com`
- [ ] `OLLAMA_MODEL` defaults to `gemini-3-flash-preview`
- [ ] `OLLAMA_API_KEY` is optional (defaults to `None`)

### FR-006: Dependency Management
**Type**: Ubiquitous
**Statement**: The system shall replace `google-generativeai` with `ollama` in all dependency files.
**Acceptance Criteria**:
- [ ] `pyproject.toml` updated
- [ ] `requirements/base.txt` updated
- [ ] `google-generativeai` no longer imported anywhere

## Non-Functional Requirements

### NFR-001: Backward Compatibility
**Statement**: The API contract (request/response format) of all HTTP endpoints shall remain unchanged.
**Acceptance Criteria**:
- [ ] `/api/chat/message` returns same JSON structure
- [ ] Sentiment analysis output format unchanged
- [ ] Frontend requires zero changes

### NFR-002: Test Coverage
**Statement**: All existing tests that mock Google GenAI shall be updated to mock Ollama equivalents.
**Acceptance Criteria**:
- [ ] `test_chat_history.py` passes with Ollama mocks
- [ ] `test_context_extraction.py` passes with Ollama mocks
- [ ] `test_context_prioritization.py` passes with Ollama mocks

## Constraints
- Must use existing `pydantic-settings` pattern for configuration
- Ollama Cloud API at `https://ollama.com` (not local)
- Model: `gemini-3-flash-preview` (configurable via env)

## Dependencies
- `ollama` Python package (>= 0.4.0)
- Ollama Cloud account with API key (already configured)
- Existing MCP tools (`fetch_course_sections`, etc.) remain unchanged

## Out of Scope
- Frontend changes (API contract unchanged)
- MCP tool logic changes (only the LLM integration layer changes)
- Model fine-tuning or prompt engineering for Ollama-specific behavior
- Local Ollama server setup/management
