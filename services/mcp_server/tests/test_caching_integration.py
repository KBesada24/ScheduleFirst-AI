import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from mcp_server.services.supabase_service import supabase_service
from mcp_server.services.data_population_service import data_population_service
from mcp_server.utils.cache import cache_manager

@pytest.mark.asyncio
async def test_supabase_service_caching():
    # Clear cache
    await cache_manager.clear()
    
    # Mock the client execution
    mock_execute = MagicMock()
    mock_execute.execute.return_value.data = [{"course_code": "CSC101", "semester": "Fall 2025", "university": "CUNY"}]
    
    # Mock the chain: table().select().eq()...execute()
    # This is complex to mock perfectly, so we'll mock the internal client attribute if possible
    # Or better, we'll patch the client on the service instance
    
    with patch.object(supabase_service, 'client') as mock_client:
        # Setup mock chain
        mock_builder = MagicMock()
        mock_data = [{"course_code": "CSC101", "semester": "Fall 2025", "university": "CUNY", "name": "Intro to CS"}]
        mock_builder.execute.return_value.data = mock_data
        
        # Make the builder return itself for chained calls
        mock_builder.select.return_value = mock_builder
        mock_builder.eq.return_value = mock_builder
        mock_builder.ilike.return_value = mock_builder
        
        # Connect table() to builder
        mock_client.table.return_value = mock_builder
        
        # First call - should hit DB
        courses1 = await supabase_service.get_courses_by_semester("Fall 2025", "CUNY")
        assert len(courses1) == 1
        assert courses1[0].course_code == "CSC101"
        
        # Verify DB call
        assert mock_client.table.call_count >= 1
        call_count_after_first = mock_client.table.call_count
        
        # Second call - should hit cache
        courses2 = await supabase_service.get_courses_by_semester("Fall 2025", "CUNY")
        assert len(courses2) == 1
        
        # Verify NO new DB call
        assert mock_client.table.call_count == call_count_after_first

@pytest.mark.asyncio
async def test_data_population_caching():
    # Clear cache
    await cache_manager.clear()
    
    # Mock dependencies
    with patch('mcp_server.services.data_population_service.data_freshness_service') as mock_freshness, \
         patch('mcp_server.services.data_population_service.sync_courses_job', new_callable=AsyncMock) as mock_sync:
        
        # Setup mocks
        mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
        mock_freshness.mark_sync_in_progress = AsyncMock()
        mock_sync.return_value = {"success": True}
        
        # First call - should trigger sync
        result1 = await data_population_service.ensure_course_data("Fall 2025", "CUNY")
        assert result1.success is True
        assert mock_sync.call_count == 1
        
        # Second call - should hit cache and NOT trigger sync
        # Reset mock to verify it's not called
        mock_sync.reset_mock()
        
        result2 = await data_population_service.ensure_course_data("Fall 2025", "CUNY")
        assert result2.success is True
        assert mock_sync.call_count == 0
        
        # Force call - should trigger sync
        result3 = await data_population_service.ensure_course_data("Fall 2025", "CUNY", force=True)
        assert result3.success is True
        assert mock_sync.call_count == 1
