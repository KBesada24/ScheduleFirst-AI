# Implementation Plan: Ollama LLM Migration

## Task Breakdown

### Phase 1: Foundation (Dependencies & Config)

- [ ] **TASK-001**: Update dependency files
  - Replace `google-generativeai` with `ollama` in `pyproject.toml`
  - Replace `google-generativeai` with `ollama` in `requirements/base.txt`
  - Estimated: 5 minutes

- [ ] **TASK-002**: Update `config.py`
  - Remove `gemini_api_key` required field
  - Add `ollama_host`, `ollama_model`, `ollama_api_key` fields
  - Update error message in `get_settings()`
  - Estimated: 10 minutes

- [ ] **TASK-003**: Update `.env.example`
  - Replace `GEMINI_API_KEY` with Ollama env vars
  - Estimated: 5 minutes

### Phase 2: Backend Implementation

- [ ] **TASK-004**: Migrate `sentiment_analyzer.py`
  - Replace `google.generativeai` import with `ollama.Client`
  - Update `__init__` to create Ollama client with auth headers
  - Update `analyze_review()` to use `client.chat(format='json')`
  - Update `analyze_reviews_batch()` to use `client.chat(format='json')`
  - Remove markdown code block stripping logic
  - Estimated: 30 minutes

- [ ] **TASK-005**: Migrate `api_server.py` chat endpoint
  - Replace `google.generativeai` import with `ollama.Client`
  - Remove `genai.configure()` call
  - Convert 4 tool declarations from protobuf to JSON schema dicts
  - Replace `genai.GenerativeModel` + `start_chat()` with `Client.chat()`
  - Replace stateful chat with flat messages list
  - Rewrite tool calling loop for Ollama's response format
  - Replace response extraction (`candidates[0].content.parts` → `message.content`)
  - Remove `genai.protos.Part(function_response=...)` patterns
  - Estimated: 1 hour

### Phase 3: Test Updates

- [ ] **TASK-006**: Update `test_chat_history.py`
  - Replace `patch('google.generativeai.*')` with `patch('api_server.OllamaClient')`
  - Update mock response structure for Ollama format
  - Update assertion to check messages list instead of `start_chat(history=...)`
  - Estimated: 20 minutes

- [ ] **TASK-007**: Update `test_context_extraction.py`
  - Same mock pattern changes as TASK-006
  - Update `test_chat_with_ai_uses_extracted_context()` assertions
  - `test_extract_context_helper()` needs no changes
  - Estimated: 20 minutes

- [ ] **TASK-008**: Update `test_context_prioritization.py`
  - Same mock pattern changes
  - Fix pre-existing assertion for `"PRIORITIZE CHAT HISTORY"` (text not in current code)
  - Estimated: 20 minutes

### Phase 4: Verification

- [ ] **TASK-009**: Run all updated tests
  - `python -m pytest tests/test_chat_history.py tests/test_context_extraction.py tests/test_context_prioritization.py -v`
  - Estimated: 10 minutes

- [ ] **TASK-010**: Grep for remaining GenAI references
  - Ensure no `google.generativeai` or `genai` imports remain
  - Estimated: 5 minutes

## Dependencies Graph

```
TASK-001 ─┐
TASK-002 ─┼─→ TASK-004 ─→ TASK-009
TASK-003 ─┘   TASK-005 ─→ TASK-006 ─┐
                           TASK-007 ─┼─→ TASK-009 → TASK-010
                           TASK-008 ─┘
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ollama model doesn't support all 4 tools well | Medium | High | Test with `gemini-3-flash-preview`; allow model to be swapped via env var |
| Ollama Cloud API rate limits | Low | Medium | Existing rate limiting on chat endpoint; maintain max 6 tool calls |
| Different JSON response format from model | Medium | Medium | Use `format='json'` for structured output; keep fallback error handling |
| Test mock structure mismatch | Low | Low | Carefully match Ollama's `ChatResponse` type structure |

## Files Modified Summary

| File | Type | Changes |
|------|------|---------|
| `services/pyproject.toml` | Config | Swap dependency |
| `services/requirements/base.txt` | Config | Swap dependency |
| `services/mcp_server/config.py` | Config | Replace API key fields |
| `services/.env.example` | Config | Update env var names |
| `services/mcp_server/services/sentiment_analyzer.py` | Source | Full LLM layer rewrite |
| `services/api_server.py` | Source | Chat endpoint LLM layer rewrite |
| `tests/test_chat_history.py` | Test | Mock updates |
| `tests/test_context_extraction.py` | Test | Mock updates |
| `tests/test_context_prioritization.py` | Test | Mock updates |
