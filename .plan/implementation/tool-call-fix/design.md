# Technical Design: Gemini Tool Call Fix (`thought_signature`)

## Architecture Overview

The fix is a targeted client-layer swap inside `api_server.py`. No architectural changes are required — only the HTTP client used to talk to Gemini changes. All business logic, tool dispatch, and message routing remains identical.

```
Frontend (React)
     │  POST /api/chat/message
     ▼
api_server.py  ──chat_with_ai()──►  [google-genai SDK]  ──►  Gemini API
                                           │                       │
                                    thought_signature        preserved in
                                    handled automatically    Content object
                                           │
                                    tool call detected
                                           │
                         ┌─────────────────▼─────────────────┐
                         │   MCP Tools (unchanged)            │
                         │   fetch_course_sections            │
                         │   generate_optimized_schedule      │
                         │   get_professor_grade              │
                         │   compare_professors               │
                         └─────────────────┬─────────────────┘
                                           │ result dict
                                           ▼
                         types.Part.from_function_response()
                                           │
                                    [google-genai SDK]  ──►  Gemini API
                                                              (final text)
```

---

## Why This Fix Works

When Gemini 3 models "think" before making a function call, they embed an encrypted `thought_signature` blob in the response's `Content.parts`. The Ollama client reconstructs the assistant message from primitive fields (name, arguments) and **drops** this blob. When your code sends it back, Gemini rejects it with a 400.

The `google-genai` SDK's `response.candidates[0].content` is an opaque `Content` object that is passed through **as-is** to the next request, preserving the signature without any special handling on your part.

---

## Key API Differences

| Operation | Ollama Client | google-genai SDK |
|-----------|---------------|------------------|
| Client init | `OllamaClient(host=..., headers=...)` | `genai.Client(api_key=...)` |
| Tool declarations | `{'type': 'function', 'function': {...}}` | `types.FunctionDeclaration(name=..., ...)` |
| Send message | `client.chat(model=..., messages=..., tools=...)` | `client.models.generate_content(model=..., contents=..., config=...)` |
| Check for tool calls | `response.message.tool_calls` | `response.function_calls` |
| Tool call args | `tc.function.arguments` | `fc.args` |
| Append assistant turn | `messages.append(response.message)` ⚠️ | `contents.append(response.candidates[0].content)` ✅ |
| Append tool result | `{'role': 'tool', 'tool_name': ..., 'content': ...}` | `types.Content(role='user', parts=[types.Part.from_function_response(...)])` |
| Extract final text | `response.message.content` | `response.text` |

---

## Data Model / Message Structure

### Old Ollama format (broken — loses thought_signature)
```python
messages = [
    {'role': 'system', 'content': '...'},
    {'role': 'user', 'content': '...'},
    # After tool call:
    response.message,  # ← Ollama Message object, drops thought_signature
    {'role': 'tool', 'tool_name': 'fetch_course_sections', 'content': '{"..."}'},
]
```

### New google-genai format (correct — preserves thought_signature)
```python
from google.genai import types

contents = [
    types.Content(role='user', parts=[types.Part(text=system_instruction + '\n\n' + user_message)]),
    # After tool call:
    response.candidates[0].content,  # ← opaque Content object with thought_signature intact
    types.Content(role='user', parts=[
        types.Part.from_function_response(
            name='fetch_course_sections',
            response={'result': tool_result_dict}
        )
    ]),
]
```

> **Note on system prompt**: `google-genai` handles system instructions via `config=types.GenerateContentConfig(system_instruction=..., tools=[...])` rather than a `system` role message.

---

## Component Breakdown

### Files Modified

#### `services/requirements/base.txt`
- Remove: `ollama>=0.4.0`
- Add: `google-genai>=1.0.0`

#### `services/pyproject.toml`
- Remove: `ollama = "^0.4.0"`
- Add: `google-genai = "^1.0.0"`

#### `services/mcp_server/config.py`
Add two new settings:
```python
# Gemini Configuration (replaces Ollama for chat)
gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
gemini_model: str = Field(default="gemini-3-flash-preview", alias="GEMINI_MODEL")
```
Keep existing `ollama_*` fields as optional (used by deprecated paths).

#### `services/api_server.py` — `chat_with_ai()` function [primary change]

```python
# NEW client init (replaces OllamaClient)
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.gemini_api_key)

# NEW tool declarations
tool_declarations = [
    types.FunctionDeclaration(
        name='fetch_course_sections',
        description=f"Fetch available course sections...",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                'course_codes': types.Schema(type=types.Type.ARRAY, ...),
                'semester': types.Schema(type=types.Type.STRING, ...),
                'university': types.Schema(type=types.Type.STRING, ...),
            },
            required=['course_codes'],
        ),
    ),
    # ... repeat for other tools
]

config = types.GenerateContentConfig(
    system_instruction=system_instruction,
    tools=[types.Tool(function_declarations=tool_declarations)],
)

# NEW initial call
response = client.models.generate_content(
    model=settings.gemini_model,
    contents=contents,
    config=config,
)

# NEW tool call loop
while response.function_calls and tool_call_count < max_tool_calls:
    contents.append(response.candidates[0].content)  # ← KEY FIX
    
    function_response_parts = []
    for fc in response.function_calls:
        # ... existing dispatch logic unchanged ...
        function_response_parts.append(
            types.Part.from_function_response(name=fc.name, response={'result': result})
        )
    
    contents.append(types.Content(role='user', parts=function_response_parts))
    response = client.models.generate_content(model=..., contents=contents, config=config)

final_text = response.text
```

#### `services/api_server.py` — `health()` endpoint
```python
# Update line ~326:
"gemini_api": "configured" if settings.gemini_api_key else "not configured",
```

#### `services/mcp_server/services/sentiment_analyzer.py`
```python
# Remove:
from ollama import Client as OllamaClient

# Add:
from google import genai
from google.genai import types

# Update __init__:
self.client = genai.Client(api_key=settings.gemini_api_key)
self.model = settings.gemini_model

# Update analyze() calls:
# client.chat(...) → client.models.generate_content(...)
```

---

## History Message Handling

The existing history rebuild loop (lines 1018–1022) converts prior chat turns into `Content` objects:

```python
# OLD (Ollama):
messages.append({'role': role, 'content': content})

# NEW (google-genai):
contents.append(types.Content(
    role='model' if role == 'assistant' else 'user',
    parts=[types.Part(text=content)]
))
```

> **Note**: `google-genai` uses `'model'` for the assistant role, not `'assistant'`.

---

## Error Handling Strategy

| Error Condition | Current Behavior | After Fix |
|----------------|-----------------|-----------|
| Missing `GEMINI_API_KEY` | Silent (key not used by Ollama host-based auth) | Log warning on startup; 500 on first chat |
| Gemini 400 (bad request) | 500 from `thought_signature` | Should not occur; logged if it does |
| Gemini 429 (rate limit) | 500 with Ollama error | 500 with `google.api_core.exceptions.ResourceExhausted` message |
| Tool execution error | Result dict `{"error": "..."}` sent back | Same — no change |

---

## Security Considerations

- `GEMINI_API_KEY` is already stored in `services/.env.local` (gitignored)
- The API key is never logged or returned in API responses
- The existing `settings.gemini_api_key` field uses Pydantic `Optional[str]` with no default — it must be set

---

## Performance Considerations

- The `google-genai` SDK uses `httpx` internally (same as current stack) — no extra latency
- Tool execution time is unchanged (same MCP functions)
- Parallel tool calls in one model turn: append all `Part.from_function_response()` parts in a single `Content` object (see tool call loop above) — this is more efficient than the current sequential per-tool message appending

---

## Testing Strategy

- **Unit**: No new unit tests needed — business logic is unchanged
- **Regression**: Run existing `pytest mcp_server/tests/` suite to verify non-chat services are unaffected
- **Integration**: Manual smoke test — send a message that triggers a tool call and verify response
- **Optional**: Add a mock-based test for `chat_with_ai` that monkeypatches `genai.Client` to verify the `contents` list built correctly includes `response.candidates[0].content`
