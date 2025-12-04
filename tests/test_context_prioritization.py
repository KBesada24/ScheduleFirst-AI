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
    # Mock message with history containing the university
    message = {
        "message": "I need CSC 446",
        "context": {
            "university": None, # Simulating "Not yet specified" in app context
            "semester": None
        },
        "history": [
            {"role": "user", "content": "I go to CUNY College of Staten Island"},
            {"role": "assistant", "content": "Great, College of Staten Island."}
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
        
        # Simulate LLM calling the tool with the correct university from history
        mock_part.function_call.name = "fetch_course_sections"
        mock_part.function_call.args = {
            "course_code": "CSC 446",
            "university": "College of Staten Island",
            "semester": "Spring 2025" # Assuming LLM infers or asks, but checking university is key
        }
        
        mock_candidate.content.parts = [mock_part]
        mock_response.candidates = [mock_candidate]
        
        mock_chat.send_message.return_value = mock_response
        MockModel.return_value.start_chat.return_value = mock_chat

        # We need to mock the tool execution to avoid errors
        with patch('mcp_server.tools.schedule_optimizer.fetch_course_sections.fn') as mock_fetch:
            mock_fetch.return_value = {"sections": []}
            
            # Call function
            await chat_with_ai(message)

        # Verify that the system instruction contains the prioritization rule
        call_args = MockModel.call_args
        system_instruction = call_args.kwargs['system_instruction']
        assert "PRIORITIZE CHAT HISTORY" in system_instruction
        assert "Initial App Context" in system_instruction
