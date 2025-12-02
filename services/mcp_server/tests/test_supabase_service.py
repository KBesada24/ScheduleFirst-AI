"""
Unit tests for SupabaseService sync metadata methods
Tests sync metadata CRUD operations and error handling
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from postgrest.exceptions import APIError

from mcp_server.services.supabase_service import SupabaseService
from mcp_server.models.sync_metadata import SyncMetadata
from mcp_server.utils.exceptions import DatabaseError

from conftest import create_mock_sync_metadata


class TestSupabaseServiceSyncMetadata:
    """Tests for sync metadata operations in SupabaseService"""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock Supabase client"""
        mock = MagicMock()
        
        # Setup chainable query builder
        mock_builder = MagicMock()
        mock_builder.select.return_value = mock_builder
        mock_builder.insert.return_value = mock_builder
        mock_builder.update.return_value = mock_builder
        mock_builder.upsert.return_value = mock_builder
        mock_builder.eq.return_value = mock_builder
        mock_builder.lt.return_value = mock_builder
        
        mock.table.return_value = mock_builder
        
        return mock, mock_builder
    
    @pytest.fixture
    def service(self, mock_client):
        """Create a SupabaseService with mocked client"""
        mock, _ = mock_client
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create:
            mock_create.return_value = mock
            service = SupabaseService()
            # Override the circuit breaker for testing
            return service
    
    # ============ get_sync_metadata Tests ============
    
    @pytest.mark.asyncio
    async def test_get_sync_metadata_returns_metadata_when_found(self, mock_client):
        """Should return SyncMetadata when record exists"""
        mock, mock_builder = mock_client
        
        expected_data = {
            "id": str(uuid4()),
            "entity_type": "courses",
            "semester": "Fall 2025",
            "university": "Baruch College",
            "last_sync": datetime.now().isoformat(),
            "sync_status": "success",
            "error_message": None,
            "created_at": datetime.now().isoformat()
        }
        
        mock_response = MagicMock()
        mock_response.data = [expected_data]
        mock_builder.execute.return_value = mock_response
        
        async def mock_breaker_call(fn):
            # Properly handle async functions
            result = fn()
            if hasattr(result, '__await__'):
                return await result
            return result
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create, patch(
            'mcp_server.services.supabase_service.supabase_breaker'
        ) as mock_breaker:
            mock_create.return_value = mock
            mock_breaker.call = mock_breaker_call
            
            service = SupabaseService()
            result = await service.get_sync_metadata(
                "courses", "Fall 2025", "Baruch College"
            )
            
            assert result is not None
            assert isinstance(result, SyncMetadata)
            assert result.entity_type == "courses"
            assert result.semester == "Fall 2025"
            assert result.sync_status == "success"
    
    @pytest.mark.asyncio
    async def test_get_sync_metadata_returns_none_when_not_found(self, mock_client):
        """Should return None when no record exists"""
        mock, mock_builder = mock_client
        
        mock_response = MagicMock()
        mock_response.data = []
        mock_builder.execute.return_value = mock_response
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create, patch(
            'mcp_server.services.supabase_service.supabase_breaker'
        ) as mock_breaker:
            mock_create.return_value = mock
            mock_breaker.call = AsyncMock(side_effect=lambda fn: fn())
            
            service = SupabaseService()
            result = await service.get_sync_metadata(
                "courses", "Spring 2030", "Unknown College"
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_sync_metadata_raises_database_error_on_api_error(self, mock_client):
        """Should raise DatabaseError when API fails"""
        mock, mock_builder = mock_client
        
        mock_builder.execute.side_effect = APIError({"message": "Connection failed"})
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create, patch(
            'mcp_server.services.supabase_service.supabase_breaker'
        ) as mock_breaker:
            mock_create.return_value = mock
            mock_breaker.call = AsyncMock(side_effect=lambda fn: fn())
            
            service = SupabaseService()
            
            with pytest.raises(DatabaseError) as exc_info:
                await service.get_sync_metadata(
                    "courses", "Fall 2025", "Baruch College"
                )
            
            assert exc_info.value.operation == "get_sync_metadata"
    
    # ============ update_sync_metadata Tests ============
    
    @pytest.mark.asyncio
    async def test_update_sync_metadata_creates_new_record_when_not_exists(self, mock_client):
        """Should create new record when no existing metadata"""
        mock, mock_builder = mock_client
        
        # First call (get_sync_metadata) returns empty
        # Second call (insert) returns success
        mock_response_empty = MagicMock()
        mock_response_empty.data = []
        
        mock_response_insert = MagicMock()
        mock_response_insert.data = [{"id": str(uuid4())}]
        
        mock_builder.execute.side_effect = [
            mock_response_empty,  # get_sync_metadata check
            mock_response_insert  # insert
        ]
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create, patch(
            'mcp_server.services.supabase_service.supabase_breaker'
        ) as mock_breaker, patch(
            'mcp_server.services.supabase_service.cache_manager'
        ) as mock_cache:
            mock_create.return_value = mock
            mock_breaker.call = AsyncMock(side_effect=lambda fn: fn())
            mock_cache.get = AsyncMock(return_value=None)
            
            service = SupabaseService()
            result = await service.update_sync_metadata(
                "courses", "Fall 2025", "Baruch College", "success"
            )
            
            assert result is True
            # Verify insert was called (check calls to table)
            mock.table.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_sync_metadata_updates_existing_record(self, mock_client):
        """Should update existing record when metadata exists"""
        mock, mock_builder = mock_client
        
        existing_id = uuid4()
        existing_data = {
            "id": str(existing_id),
            "entity_type": "courses",
            "semester": "Fall 2025",
            "university": "Baruch College",
            "last_sync": datetime.now().isoformat(),
            "sync_status": "in_progress",
            "error_message": None,
            "created_at": datetime.now().isoformat()
        }
        
        mock_response_exists = MagicMock()
        mock_response_exists.data = [existing_data]
        
        mock_response_update = MagicMock()
        mock_response_update.data = [{"id": str(existing_id)}]
        
        mock_builder.execute.side_effect = [
            mock_response_exists,  # get_sync_metadata check
            mock_response_update   # update
        ]
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create, patch(
            'mcp_server.services.supabase_service.supabase_breaker'
        ) as mock_breaker, patch(
            'mcp_server.services.supabase_service.cache_manager'
        ) as mock_cache:
            mock_create.return_value = mock
            mock_breaker.call = AsyncMock(side_effect=lambda fn: fn())
            mock_cache.get = AsyncMock(return_value=None)
            
            service = SupabaseService()
            result = await service.update_sync_metadata(
                "courses", "Fall 2025", "Baruch College", "success"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_update_sync_metadata_includes_error_message(self, mock_client):
        """Should include error message when provided"""
        mock, mock_builder = mock_client
        
        mock_response_empty = MagicMock()
        mock_response_empty.data = []
        
        mock_response_insert = MagicMock()
        mock_response_insert.data = [{"id": str(uuid4())}]
        
        mock_builder.execute.side_effect = [
            mock_response_empty,
            mock_response_insert
        ]
        
        inserted_data = None
        original_insert = mock_builder.insert
        
        def capture_insert(data):
            nonlocal inserted_data
            inserted_data = data
            return mock_builder
        
        mock_builder.insert = capture_insert
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create, patch(
            'mcp_server.services.supabase_service.supabase_breaker'
        ) as mock_breaker, patch(
            'mcp_server.services.supabase_service.cache_manager'
        ) as mock_cache:
            mock_create.return_value = mock
            mock_breaker.call = AsyncMock(side_effect=lambda fn: fn())
            mock_cache.get = AsyncMock(return_value=None)
            
            service = SupabaseService()
            result = await service.update_sync_metadata(
                "courses", "Fall 2025", "Baruch College", 
                "failed", "Scraping timeout after 30s"
            )
            
            assert result is True
            assert inserted_data is not None
            assert inserted_data["error_message"] == "Scraping timeout after 30s"
            assert inserted_data["sync_status"] == "failed"
    
    @pytest.mark.asyncio
    async def test_update_sync_metadata_raises_database_error_on_failure(self, mock_client):
        """Should raise DatabaseError when operation fails"""
        mock, mock_builder = mock_client
        
        mock_builder.execute.side_effect = APIError({"message": "Update failed"})
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create, patch(
            'mcp_server.services.supabase_service.supabase_breaker'
        ) as mock_breaker, patch(
            'mcp_server.services.supabase_service.cache_manager'
        ) as mock_cache:
            mock_create.return_value = mock
            mock_breaker.call = AsyncMock(side_effect=lambda fn: fn())
            mock_cache.get = AsyncMock(return_value=None)
            
            service = SupabaseService()
            
            with pytest.raises(DatabaseError) as exc_info:
                await service.update_sync_metadata(
                    "courses", "Fall 2025", "Baruch College", "success"
                )
            
            # The operation name should match the method being called
            assert exc_info.value.operation == "update_sync_metadata"
    
    # ============ get_stale_entities Tests ============
    
    @pytest.mark.asyncio
    async def test_get_stale_entities_returns_stale_records(self, mock_client):
        """Should return records older than TTL"""
        mock, mock_builder = mock_client
        
        stale_records = [
            {
                "id": str(uuid4()),
                "entity_type": "courses",
                "semester": "Fall 2024",
                "university": "Baruch College",
                "last_sync": (datetime.now() - timedelta(days=10)).isoformat(),
                "sync_status": "success"
            },
            {
                "id": str(uuid4()),
                "entity_type": "courses",
                "semester": "Spring 2024",
                "university": "Hunter College",
                "last_sync": (datetime.now() - timedelta(days=14)).isoformat(),
                "sync_status": "success"
            }
        ]
        
        mock_response = MagicMock()
        mock_response.data = stale_records
        mock_builder.execute.return_value = mock_response
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create, patch(
            'mcp_server.services.supabase_service.supabase_breaker'
        ) as mock_breaker:
            mock_create.return_value = mock
            mock_breaker.call = AsyncMock(side_effect=lambda fn: fn())
            
            service = SupabaseService()
            ttl_7_days = 7 * 24 * 3600
            result = await service.get_stale_entities("courses", ttl_7_days)
            
            assert len(result) == 2
            assert result[0]["semester"] == "Fall 2024"
            assert result[1]["semester"] == "Spring 2024"
    
    @pytest.mark.asyncio
    async def test_get_stale_entities_returns_empty_when_all_fresh(self, mock_client):
        """Should return empty list when no stale records"""
        mock, mock_builder = mock_client
        
        mock_response = MagicMock()
        mock_response.data = []
        mock_builder.execute.return_value = mock_response
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create, patch(
            'mcp_server.services.supabase_service.supabase_breaker'
        ) as mock_breaker:
            mock_create.return_value = mock
            mock_breaker.call = AsyncMock(side_effect=lambda fn: fn())
            
            service = SupabaseService()
            result = await service.get_stale_entities("courses", 3600)
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_get_stale_entities_raises_database_error_on_failure(self, mock_client):
        """Should raise DatabaseError when query fails"""
        mock, mock_builder = mock_client
        
        mock_builder.execute.side_effect = APIError({"message": "Query failed"})
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create, patch(
            'mcp_server.services.supabase_service.supabase_breaker'
        ) as mock_breaker:
            mock_create.return_value = mock
            mock_breaker.call = AsyncMock(side_effect=lambda fn: fn())
            
            service = SupabaseService()
            
            with pytest.raises(DatabaseError) as exc_info:
                await service.get_stale_entities("courses", 3600)
            
            assert exc_info.value.operation == "get_stale_entities"


class TestSupabaseServiceErrorHandling:
    """Tests for _handle_api_error method"""
    
    @pytest.fixture
    def service(self):
        """Create a SupabaseService instance"""
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create:
            mock_create.return_value = MagicMock()
            return SupabaseService()
    
    def test_handle_api_error_raises_database_error(self, service):
        """Should raise DatabaseError with correct attributes"""
        error = APIError({"message": "Connection timeout"})
        
        with pytest.raises(DatabaseError) as exc_info:
            service._handle_api_error(
                error, 
                "test_operation",
                {"param": "value"}
            )
        
        assert exc_info.value.operation == "test_operation"
        assert "timeout" in exc_info.value.message.lower()
        assert exc_info.value.details["param"] == "value"
    
    def test_handle_api_error_marks_timeout_as_retryable(self, service):
        """Timeout errors should be marked as retryable"""
        error = APIError({"message": "Connection timeout"})
        
        with pytest.raises(DatabaseError) as exc_info:
            service._handle_api_error(error, "test_operation")
        
        assert exc_info.value.is_retryable is True
    
    def test_handle_api_error_marks_permission_as_not_retryable(self, service):
        """Permission errors should not be retryable"""
        error = APIError({"message": "Permission denied"})
        
        with pytest.raises(DatabaseError) as exc_info:
            service._handle_api_error(error, "test_operation")
        
        assert exc_info.value.is_retryable is False
    
    def test_handle_api_error_marks_not_found_as_not_retryable(self, service):
        """Not found errors should not be retryable"""
        error = APIError({"message": "Resource not found"})
        
        with pytest.raises(DatabaseError) as exc_info:
            service._handle_api_error(error, "test_operation")
        
        assert exc_info.value.is_retryable is False
    
    def test_handle_api_error_marks_unauthorized_as_not_retryable(self, service):
        """Unauthorized errors should not be retryable"""
        error = APIError({"message": "Unauthorized access"})
        
        with pytest.raises(DatabaseError) as exc_info:
            service._handle_api_error(error, "test_operation")
        
        assert exc_info.value.is_retryable is False


class TestSupabaseServiceHealthCheck:
    """Tests for health_check method"""
    
    @pytest.mark.asyncio
    async def test_health_check_returns_true_when_healthy(self):
        """Should return True when database is accessible"""
        mock_client = MagicMock()
        mock_builder = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "test"}]
        
        mock_builder.select.return_value = mock_builder
        mock_builder.limit.return_value = mock_builder
        mock_builder.execute.return_value = mock_response
        mock_client.table.return_value = mock_builder
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create:
            mock_create.return_value = mock_client
            
            service = SupabaseService()
            result = await service.health_check()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_unhealthy(self):
        """Should return False when database is not accessible"""
        mock_client = MagicMock()
        mock_builder = MagicMock()
        
        mock_builder.select.return_value = mock_builder
        mock_builder.limit.return_value = mock_builder
        mock_builder.execute.side_effect = Exception("Connection failed")
        mock_client.table.return_value = mock_builder
        
        with patch(
            'mcp_server.services.supabase_service.create_client'
        ) as mock_create:
            mock_create.return_value = mock_client
            
            service = SupabaseService()
            result = await service.health_check()
            
            assert result is False
