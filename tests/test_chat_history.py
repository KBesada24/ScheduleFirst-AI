import sys
import os
import pytest
from unittest.mock import MagicMock, patch

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
os.environ['GEMINI_API_KEY'] = 'example-key'

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

    # Mock genai
    with patch('google.generativeai.GenerativeModel') as MockModel, \
         patch('google.generativeai.configure'), \
         patch('google.generativeai.protos'):
        
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "Here are courses"
        # Ensure function_call is not set or empty
        mock_part.function_call = None
        
        mock_candidate.content.parts = [mock_part]
        mock_response.candidates = [mock_candidate]
        
        mock_chat.send_message.return_value = mock_response
        MockModel.return_value.start_chat.return_value = mock_chat

        # Call function
        await chat_with_ai(message)

        # Verify start_chat called with history
        expected_history = [
            {"role": "user", "parts": ["I am at Baruch"]},
            {"role": "model", "parts": ["Hello Baruch student"]}
        ]
        MockModel.return_value.start_chat.assert_called_with(history=expected_history)
