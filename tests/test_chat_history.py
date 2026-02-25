import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add services directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../services')))

from pydantic import BaseModel

# Define dummy Pydantic models
class ScheduleConstraints(BaseModel):
    pass

class OptimizedSchedule(BaseModel):
    pass

class CourseSearchFilter(BaseModel):
    pass

class ApiResponse(BaseModel):
    pass

class ResponseMetadata(BaseModel):
    pass

class ErrorResponse(BaseModel):
    pass

class DataQuality(BaseModel):
    pass

# Mock dependencies before importing api_server
sys.modules['mcp_server'] = MagicMock()
sys.modules['mcp_server.config'] = MagicMock()
sys.modules['mcp_server.services'] = MagicMock()
sys.modules['mcp_server.services.supabase_service'] = MagicMock()
sys.modules['mcp_server.services.constraint_solver'] = MagicMock()
sys.modules['mcp_server.services.sentiment_analyzer'] = MagicMock()
sys.modules['mcp_server.services.data_population_service'] = MagicMock()
sys.modules['mcp_server.services.data_freshness_service'] = MagicMock()
sys.modules['mcp_server.services.metrics_collector'] = MagicMock()
sys.modules['mcp_server.utils'] = MagicMock()
sys.modules['mcp_server.utils.logger'] = MagicMock()
sys.modules['mcp_server.utils.metrics'] = MagicMock()
sys.modules['mcp_server.utils.cache'] = MagicMock()
sys.modules['mcp_server.utils.cache_manager'] = MagicMock()
sys.modules['mcp_server.utils.circuit_breaker'] = MagicMock()
sys.modules['mcp_server.utils.exceptions'] = MagicMock()
sys.modules['mcp_server.utils.tool_result_logging'] = MagicMock()
sys.modules['mcp_server.utils.chat_tool_result'] = MagicMock()
sys.modules['mcp_server.models'] = MagicMock()

# Assign dummy models to mocked modules
mock_schedule = MagicMock()
mock_schedule.ScheduleConstraints = ScheduleConstraints
mock_schedule.OptimizedSchedule = OptimizedSchedule
sys.modules['mcp_server.models.schedule'] = mock_schedule

mock_course = MagicMock()
mock_course.CourseSearchFilter = CourseSearchFilter
sys.modules['mcp_server.models.course'] = mock_course

mock_api_models = MagicMock()
mock_api_models.ApiResponse = ApiResponse
mock_api_models.ResponseMetadata = ResponseMetadata
mock_api_models.ErrorResponse = ErrorResponse
mock_api_models.DataQuality = DataQuality
sys.modules['mcp_server.models.api_models'] = mock_api_models

sys.modules['mcp_server.tools'] = MagicMock()
sys.modules['mcp_server.tools.schedule_optimizer'] = MagicMock()

# Patch environment variables if needed
os.environ['SUPABASE_URL'] = 'https://example.supabase.co'
os.environ['SUPABASE_KEY'] = 'example-key'

# Import chat_with_ai
from api_server import chat_with_ai

@pytest.mark.asyncio
async def test_chat_with_ai_history():
    # Mock message with history
    message = {
        "message": "What courses?",
        "history": [
            {"role": "user", "content": "I am at Baruch"},
            {"role": "assistant", "content": "Hello Baruch student"}
        ]
    }

    # Mock Ollama Client
    with patch('ollama.Client') as MockOllamaClient:
        mock_client = MagicMock()
        MockOllamaClient.return_value = mock_client
        
        # Build mock response (no tool calls, just text)
        mock_response = MagicMock()
        mock_response.message.content = "Here are courses"
        mock_response.message.tool_calls = None
        
        mock_client.chat.return_value = mock_response

        # Call function
        await chat_with_ai(message)

        # Verify ollama_client.chat was called
        mock_client.chat.assert_called_once()
        call_kwargs = mock_client.chat.call_args
        messages = call_kwargs.kwargs.get('messages') or call_kwargs[1].get('messages')
        
        # Verify history is in the messages list
        # Messages should be: [system, user:"I am at Baruch", assistant:"Hello Baruch student", user:"What courses?"]
        history_messages = [m for m in messages if m.get('role') in ('user', 'assistant') and isinstance(m, dict)]
        
        # Check that the history user message is present
        assert any(m.get('content') == "I am at Baruch" and m.get('role') == 'user' for m in history_messages)
        # Check that the history assistant message is present
        assert any(m.get('content') == "Hello Baruch student" and m.get('role') == 'assistant' for m in history_messages)
        # Check that the current user message is the last one
        assert messages[-1] == {'role': 'user', 'content': 'What courses?'}


@pytest.mark.asyncio
async def test_chat_dedupes_identical_fetch_tool_calls_within_request():
    message = {
        "message": "Can you find CSC 126 sections?",
        "context": {
            "university": "College of Staten Island",
            "semester": "Spring 2026",
        },
        "history": [],
    }

    tool_result = {
        "success": True,
        "total_courses": 1,
        "courses": [
            {
                "course_code": "CSC 126",
                "sections": [],
            }
        ],
        "metadata": {"source": "selenium_fallback", "fallback_used": True},
    }

    duplicate_args = {
        "course_codes": ["CSC 126"],
        "semester": "Spring 2026",
        "university": "College of Staten Island",
    }

    mock_tool_call_1 = MagicMock()
    mock_tool_call_1.function.name = "fetch_course_sections"
    mock_tool_call_1.function.arguments = duplicate_args

    mock_tool_call_2 = MagicMock()
    mock_tool_call_2.function.name = "fetch_course_sections"
    mock_tool_call_2.function.arguments = duplicate_args

    response_with_first_call = MagicMock()
    response_with_first_call.message.content = ""
    response_with_first_call.message.tool_calls = [mock_tool_call_1]

    response_with_duplicate_call = MagicMock()
    response_with_duplicate_call.message.content = ""
    response_with_duplicate_call.message.tool_calls = [mock_tool_call_2]

    final_response = MagicMock()
    final_response.message.content = "Here are your options"
    final_response.message.tool_calls = None

    schedule_optimizer_module = sys.modules['mcp_server.tools.schedule_optimizer']
    schedule_optimizer_module.fetch_course_sections.fn = AsyncMock(return_value=tool_result)
    schedule_optimizer_module.generate_optimized_schedule.fn = AsyncMock(return_value={"success": True})
    schedule_optimizer_module.get_professor_grade.fn = AsyncMock(return_value={"success": True})
    schedule_optimizer_module.compare_professors.fn = AsyncMock(return_value={"success": True})

    mock_client = MagicMock()
    mock_client.chat.side_effect = [
        response_with_first_call,
        response_with_duplicate_call,
        final_response,
    ]

    mock_ollama_module = MagicMock()
    mock_ollama_module.Client.return_value = mock_client

    with patch.dict(sys.modules, {'ollama': mock_ollama_module}):
        await chat_with_ai(message)

    schedule_optimizer_module.fetch_course_sections.fn.assert_called_once_with(
        course_codes=["CSC 126"],
        semester="Spring 2026",
        university="College of Staten Island",
    )
