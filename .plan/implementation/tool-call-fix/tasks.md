# Implementation Plan: Gemini Tool Call Fix (`thought_signature`)

## Summary

Replace the `ollama` Python client library with Google's official `google-genai` SDK in the chat and sentiment analyzer services. This fixes the `thought_signature` 400 error that crashes tool-call responses from Gemini 3 models.

**Estimated total time**: ~2–3 hours  
**Files changed**: 4 backend files, 0 frontend files  
**Risk level**: Low — business logic unchanged, client layer swap only

---

## Task Breakdown

### Phase 1: Dependencies & Configuration (≈20 min)

- [x] **TASK-001**: Update dependency files
  - `services/requirements/base.txt`: remove `ollama>=0.4.0`, add `google-genai>=1.0.0`
  - `services/pyproject.toml`: replace `ollama = "^0.4.0"` with `google-genai = "^1.0.0"`
  - Estimated: 5 minutes

- [x] **TASK-002**: Install new dependency
  - Run `pip install google-genai>=1.0.0` in the `services/venv`
  - Verify `from google import genai` imports cleanly
  - Estimated: 5 minutes

- [x] **TASK-003**: Add `gemini_api_key` and `gemini_model` to `config.py`
  - Add fields aliased to `GEMINI_API_KEY` and `GEMINI_MODEL` env vars
  - Default model: `gemini-3-flash-preview`
  - Estimated: 10 minutes

---

### Phase 2: Core Chat Endpoint Rewrite (≈60 min)

- [ ] **TASK-004**: Replace client initialization in `chat_with_ai()`
  - Remove `OllamaClient` import and instantiation (lines 833, 852–856)
  - Add `genai.Client(api_key=settings.gemini_api_key)` initialization
  - Estimated: 10 minutes

- [ ] **TASK-005**: Convert tool declarations to `types.FunctionDeclaration` format
  - Replace the `tools = [...]` list (lines 902–984) with `google-genai` typed declarations
  - Build `types.GenerateContentConfig(system_instruction=..., tools=[...])`
  - Estimated: 20 minutes

- [ ] **TASK-006**: Convert history messages to `types.Content` format
  - Replace dict-based message list with `types.Content(role=..., parts=[...])` objects
  - Use `'model'` role (not `'assistant'`) for AI turns
  - Estimated: 10 minutes

- [ ] **TASK-007**: Rewrite initial API call and tool call loop (THE KEY FIX)
  - Replace `ollama_client.chat(...)` with `client.models.generate_content(...)`
  - Replace `response.message.tool_calls` with `response.function_calls`
  - Replace `messages.append(response.message)` with `contents.append(response.candidates[0].content)`
  - Replace tool result format with `types.Part.from_function_response(...)`
  - Estimated: 20 minutes

---

### Phase 3: Secondary Service Update (≈20 min)

- [ ] **TASK-008**: Update `sentiment_analyzer.py`
  - Replace `OllamaClient` import and init with `genai.Client`
  - Update `client.chat(...)` calls to `client.models.generate_content(...)`
  - Estimated: 20 minutes

---

### Phase 4: Health & Startup Cleanup (≈10 min)

- [ ] **TASK-009**: Update startup log and health endpoint
  - `api_server.py` line ~130: update startup log to check `settings.gemini_api_key`
  - `api_server.py` line ~326: update health response field to `"gemini_api"`
  - Estimated: 10 minutes

---

### Phase 5: Verification (≈30 min)

- [ ] **TASK-010**: Run existing test suite (regression check)
  ```bash
  cd /home/kbesada/Code/ScheduleFirst-AI/services
  python -m pytest mcp_server/tests/ -v --tb=short
  ```
  - All existing tests should pass (they don't touch the chat endpoint)
  - Estimated: 10 minutes

- [ ] **TASK-011**: Manual smoke test
  - Start backend: `cd services && python api_server.py`
  - Open chat in browser
  - Send: *"Show me CSC 126 sections at Baruch for Spring 2026"*
  - **Expected**: Course sections returned in natural language, no 500 error
  - Verify backend logs show `Tool call 1: fetch_course_sections` followed by a successful final response
  - Estimated: 15 minutes

- [ ] **TASK-012**: Test multi-tool scenario (optional)
  - Send: *"Compare professors for CSC 126 at Baruch"*
  - Verify no error on multi-step tool call chain
  - Estimated: 5 minutes

---

## Dependencies Graph

```
TASK-001 → TASK-002 → TASK-003
TASK-003 → TASK-004 → TASK-005 → TASK-006 → TASK-007
TASK-007 → TASK-008 (independent, can parallelize)
TASK-007 → TASK-009
TASK-007, TASK-008, TASK-009 → TASK-010 → TASK-011 → TASK-012
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `google-genai` API schema differs from expected | Low | Medium | Reference official docs examples; type checker will catch mismatches |
| `thought_signature` error persists after fix | Very Low | High | Verify `contents.append(response.candidates[0].content)` is used (not manual reconstruction) |
| Sentiment analyzer break | Low | Low | Sentiment is not on critical path; can be fixed as follow-up |
| `GEMINI_API_KEY` not loaded from env | Low | High | Key is already in `.env.local`; verify `config.py` alias matches exactly |

---

## Rollback Plan

If the migration causes unexpected failures:
1. Revert `requirements/base.txt` and `pyproject.toml` to restore `ollama>=0.4.0`
2. Revert changes to `api_server.py` and `sentiment_analyzer.py`
3. Re-install: `pip install ollama>=0.4.0`

The git diff for this change will be small and self-contained, making rollback straightforward.

---

## Notes

- The `GEMINI_API_KEY` is already configured in `services/.env.local` (value: `AIzaSyCEYhQ-grUi0k01SEaDa772S1-OSGlVSlI`)
- The old `OLLAMA_API_KEY` and `OLLAMA_HOST` env vars can be left in `.env.local` — they'll be ignored once code no longer references them
- Per the spec skill: link each modified file back to this spec with a comment, e.g.:
  ```python
  # Spec: .plan/implementation/tool-call-fix/
  ```
