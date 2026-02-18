import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

# Add services directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../services')))

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

# Import chat_with_ai and helper
from api_server import chat_with_ai, _extract_context_from_history

def test_extract_context_helper():
    # Test 1: Extract both
    history = [
        {"role": "user", "content": "I go to College of Staten Island"},
        {"role": "assistant", "content": "Ok"},
        {"role": "user", "content": "I want to plan for Fall 2025"}
    ]
    extracted = _extract_context_from_history(history)
    assert extracted["university"] == "College of Staten Island"
    assert extracted["semester"] == "Fall 2025"

    # Test 2: Extract from single message
    history = [
        {"role": "user", "content": "I am at Baruch for Spring 2025"}
    ]
    extracted = _extract_context_from_history(history)
    assert extracted["university"] == "Baruch College"
    assert extracted["semester"] == "Spring 2025"
    
    # Test 3: No context
    history = [
        {"role": "user", "content": "Hello"}
    ]
    extracted = _extract_context_from_history(history)
    assert extracted["university"] is None
    assert extracted["semester"] is None

    # Test 4: Short year format
    history = [
        {"role": "user", "content": "Fall '25"}
    ]
    extracted = _extract_context_from_history(history)
    assert extracted["semester"] == "Fall 2025"

    # Test 5: No quotes short year
    history = [
        {"role": "user", "content": "Spring 25"}
    ]
    extracted = _extract_context_from_history(history)
    assert extracted["semester"] == "Spring 2025"

@pytest.mark.asyncio
async def test_chat_with_ai_uses_extracted_context():
    # Mock message with history containing context
    message = {
        "message": "I need courses",
        "context": {
            "university": "Old University",
            "semester": "Fall 2024"
        },
        "history": [
            {"role": "user", "content": "I go to Hunter College planning for Fall 2025"}
        ]
    }

    # Mock Ollama Client
    with patch('api_server.OllamaClient') as MockOllamaClient:
        mock_client = MagicMock()
        MockOllamaClient.return_value = mock_client
        
        # Build mock response (no tool calls, just text)
        mock_response = MagicMock()
        mock_response.message.content = "Here are courses"
        mock_response.message.tool_calls = None
        
        mock_client.chat.return_value = mock_response

        # Call function
        await chat_with_ai(message)

        # Verify that the system message contains the extracted context values
        call_kwargs = mock_client.chat.call_args
        messages = call_kwargs.kwargs.get('messages') or call_kwargs[1].get('messages')
        
        # The first message should be the system instruction
        system_msg = messages[0]
        assert system_msg['role'] == 'system'
        system_content = system_msg['content']
        
        # The extracted values should be injected into the "CURRENT CONTEXT" section
        # Extracted "Hunter College" from history should be used (history > context priority)
        assert "University: Hunter College" in system_content
        # "Fall 2024" from context.semester takes priority over "Fall 2025" from history
        # (context.get("semester") is checked first in the priority chain)
        assert "Semester: Fall 2024" in system_content
