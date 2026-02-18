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

# Import chat_with_ai
from api_server import chat_with_ai

@pytest.mark.asyncio
async def test_context_prioritization():
    """Test that university extracted from chat history overrides None in app context"""
    message = {
        "message": "I need CSC 446",
        "context": {
            "university": None,  # Simulating "Not yet specified" in app context
            "semester": None
        },
        "history": [
            {"role": "user", "content": "I go to CUNY College of Staten Island"},
            {"role": "assistant", "content": "Great, College of Staten Island."}
        ]
    }

    # Mock Ollama Client
    with patch('api_server.OllamaClient') as MockOllamaClient:
        mock_client = MagicMock()
        MockOllamaClient.return_value = mock_client
        
        # Build mock response (no tool calls, just text)
        mock_response = MagicMock()
        mock_response.message.content = "Let me look up CSC 446 for you."
        mock_response.message.tool_calls = None
        
        mock_client.chat.return_value = mock_response

        # Call function
        result = await chat_with_ai(message)

        # Verify that the system message contains the university from history
        call_kwargs = mock_client.chat.call_args
        messages = call_kwargs.kwargs.get('messages') or call_kwargs[1].get('messages')
        
        system_msg = messages[0]
        assert system_msg['role'] == 'system'
        system_content = system_msg['content']
        
        # University should be extracted from history ("College of Staten Island")
        # since app context university is None
        assert "University: College of Staten Island" in system_content
        
        # The system instruction should contain the critical rules about context usage
        assert "CURRENT USER CONTEXT" in system_content
        assert "CRITICAL RULES" in system_content
        
        # Verify the merged context in the response includes the extracted university
        assert result["context"]["university"] == "College of Staten Island"
