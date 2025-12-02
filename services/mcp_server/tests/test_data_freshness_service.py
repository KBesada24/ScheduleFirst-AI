"""
Unit tests for DataFreshnessService
Tests TTL-based data freshness checking and sync metadata management
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from mcp_server.services.data_freshness_service import DataFreshnessService
from mcp_server.models.sync_metadata import SyncMetadata
from mcp_server.models.professor import Professor

from conftest import (
    create_mock_sync_metadata,
    create_mock_professor,
    get_fresh_timestamp,
    get_stale_timestamp,
    get_boundary_timestamp,
)


class TestDataFreshnessService:
    """Tests for DataFreshnessService class"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh DataFreshnessService instance"""
        return DataFreshnessService()
    
    # ============ is_course_data_fresh Tests ============
    
    @pytest.mark.asyncio
    async def test_is_course_data_fresh_returns_true_for_fresh_data(self, service):
        """Fresh data within TTL should return True"""
        fresh_metadata = create_mock_sync_metadata(
            entity_type="courses",
            semester="Fall 2025",
            university="Baruch College",
            sync_status="success",
            last_sync=get_fresh_timestamp(service.COURSE_DATA_TTL)
        )
        
        with patch.object(
            service, '_is_expired', return_value=False
        ), patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_sync_metadata = AsyncMock(return_value=fresh_metadata)
            
            result = await service.is_course_data_fresh("Fall 2025", "Baruch College")
            
            assert result is True
            mock_supabase.get_sync_metadata.assert_called_once_with(
                "courses", "Fall 2025", "Baruch College"
            )
    
    @pytest.mark.asyncio
    async def test_is_course_data_fresh_returns_false_for_stale_data(self, service):
        """Stale data beyond TTL should return False"""
        stale_metadata = create_mock_sync_metadata(
            entity_type="courses",
            semester="Fall 2025",
            university="Baruch College",
            sync_status="success",
            last_sync=get_stale_timestamp(service.COURSE_DATA_TTL)
        )
        
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_sync_metadata = AsyncMock(return_value=stale_metadata)
            
            result = await service.is_course_data_fresh("Fall 2025", "Baruch College")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_is_course_data_fresh_returns_false_for_missing_metadata(self, service):
        """Missing sync metadata should return False"""
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_sync_metadata = AsyncMock(return_value=None)
            
            result = await service.is_course_data_fresh("Fall 2025", "Baruch College")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_is_course_data_fresh_returns_false_for_failed_sync(self, service):
        """Failed sync status should return False even if timestamp is fresh"""
        failed_metadata = create_mock_sync_metadata(
            entity_type="courses",
            semester="Fall 2025",
            university="Baruch College",
            sync_status="failed",
            last_sync=get_fresh_timestamp(service.COURSE_DATA_TTL),
            error_message="Scraping error"
        )
        
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_sync_metadata = AsyncMock(return_value=failed_metadata)
            
            result = await service.is_course_data_fresh("Fall 2025", "Baruch College")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_is_course_data_fresh_returns_false_for_in_progress_sync(self, service):
        """In-progress sync status should return False"""
        in_progress_metadata = create_mock_sync_metadata(
            entity_type="courses",
            semester="Fall 2025",
            university="Baruch College",
            sync_status="in_progress",
            last_sync=datetime.now()
        )
        
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_sync_metadata = AsyncMock(return_value=in_progress_metadata)
            
            result = await service.is_course_data_fresh("Fall 2025", "Baruch College")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_is_course_data_fresh_handles_exception(self, service):
        """Exception during freshness check should return False"""
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_sync_metadata = AsyncMock(
                side_effect=Exception("Database error")
            )
            
            result = await service.is_course_data_fresh("Fall 2025", "Baruch College")
            
            assert result is False
    
    # ============ is_professor_data_fresh Tests ============
    
    @pytest.mark.asyncio
    async def test_is_professor_data_fresh_returns_true_for_fresh_data(self, service):
        """Fresh professor data should return True"""
        professor_id = uuid4()
        fresh_professor = create_mock_professor(
            id=professor_id,
            last_updated=get_fresh_timestamp(service.PROFESSOR_DATA_TTL)
        )
        
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_professor_by_id = AsyncMock(return_value=fresh_professor)
            
            result = await service.is_professor_data_fresh(professor_id)
            
            assert result is True
            mock_supabase.get_professor_by_id.assert_called_once_with(professor_id)
    
    @pytest.mark.asyncio
    async def test_is_professor_data_fresh_returns_false_for_stale_data(self, service):
        """Stale professor data should return False"""
        professor_id = uuid4()
        stale_professor = create_mock_professor(
            id=professor_id,
            last_updated=get_stale_timestamp(service.PROFESSOR_DATA_TTL)
        )
        
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_professor_by_id = AsyncMock(return_value=stale_professor)
            
            result = await service.is_professor_data_fresh(professor_id)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_is_professor_data_fresh_returns_false_for_missing_professor(self, service):
        """Missing professor should return False"""
        professor_id = uuid4()
        
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_professor_by_id = AsyncMock(return_value=None)
            
            result = await service.is_professor_data_fresh(professor_id)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_is_professor_data_fresh_returns_false_for_null_last_updated(self, service):
        """Professor with null last_updated should return False"""
        professor_id = uuid4()
        professor = create_mock_professor(id=professor_id, last_updated=None)
        
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_professor_by_id = AsyncMock(return_value=professor)
            
            result = await service.is_professor_data_fresh(professor_id)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_is_professor_data_fresh_handles_exception(self, service):
        """Exception during freshness check should return False"""
        professor_id = uuid4()
        
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_professor_by_id = AsyncMock(
                side_effect=Exception("Database error")
            )
            
            result = await service.is_professor_data_fresh(professor_id)
            
            assert result is False
    
    # ============ is_review_data_fresh Tests ============
    
    @pytest.mark.asyncio
    async def test_is_review_data_fresh_delegates_to_professor_freshness(self, service):
        """Review freshness should use professor freshness as proxy"""
        professor_id = uuid4()
        
        with patch.object(
            service, 'is_professor_data_fresh', new_callable=AsyncMock
        ) as mock_prof_fresh:
            mock_prof_fresh.return_value = True
            
            result = await service.is_review_data_fresh(professor_id)
            
            assert result is True
            mock_prof_fresh.assert_called_once_with(professor_id)
    
    @pytest.mark.asyncio
    async def test_is_review_data_fresh_handles_exception(self, service):
        """Exception during review freshness check should return False"""
        professor_id = uuid4()
        
        with patch.object(
            service, 'is_professor_data_fresh', new_callable=AsyncMock
        ) as mock_prof_fresh:
            mock_prof_fresh.side_effect = Exception("Error")
            
            result = await service.is_review_data_fresh(professor_id)
            
            assert result is False
    
    # ============ get_last_sync Tests ============
    
    @pytest.mark.asyncio
    async def test_get_last_sync_returns_timestamp_for_successful_sync(self, service):
        """Should return last_sync timestamp for successful sync"""
        expected_time = datetime.now()
        metadata = create_mock_sync_metadata(
            sync_status="success",
            last_sync=expected_time
        )
        
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_sync_metadata = AsyncMock(return_value=metadata)
            
            result = await service.get_last_sync("courses", "Fall 2025", "Baruch College")
            
            assert result == expected_time
    
    @pytest.mark.asyncio
    async def test_get_last_sync_returns_none_for_failed_sync(self, service):
        """Should return None for failed sync status"""
        metadata = create_mock_sync_metadata(
            sync_status="failed",
            last_sync=datetime.now()
        )
        
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_sync_metadata = AsyncMock(return_value=metadata)
            
            result = await service.get_last_sync("courses", "Fall 2025", "Baruch College")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_last_sync_returns_none_for_missing_metadata(self, service):
        """Should return None when no metadata exists"""
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_sync_metadata = AsyncMock(return_value=None)
            
            result = await service.get_last_sync("courses", "Fall 2025", "Baruch College")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_last_sync_handles_exception(self, service):
        """Should return None on exception"""
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_sync_metadata = AsyncMock(
                side_effect=Exception("Error")
            )
            
            result = await service.get_last_sync("courses", "Fall 2025", "Baruch College")
            
            assert result is None
    
    # ============ mark_sync_in_progress Tests ============
    
    @pytest.mark.asyncio
    async def test_mark_sync_in_progress_calls_update_metadata(self, service):
        """Should call update_sync_metadata with in_progress status"""
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.update_sync_metadata = AsyncMock(return_value=True)
            
            result = await service.mark_sync_in_progress(
                "courses", "Fall 2025", "Baruch College"
            )
            
            assert result is True
            mock_supabase.update_sync_metadata.assert_called_once_with(
                "courses", "Fall 2025", "Baruch College", "in_progress"
            )
    
    @pytest.mark.asyncio
    async def test_mark_sync_in_progress_returns_false_on_failure(self, service):
        """Should return False when update fails"""
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.update_sync_metadata = AsyncMock(return_value=False)
            
            result = await service.mark_sync_in_progress(
                "courses", "Fall 2025", "Baruch College"
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_mark_sync_in_progress_handles_exception(self, service):
        """Should return False on exception"""
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.update_sync_metadata = AsyncMock(
                side_effect=Exception("Error")
            )
            
            result = await service.mark_sync_in_progress(
                "courses", "Fall 2025", "Baruch College"
            )
            
            assert result is False
    
    # ============ mark_sync_complete Tests ============
    
    @pytest.mark.asyncio
    async def test_mark_sync_complete_with_success_status(self, service):
        """Should call update_sync_metadata with success status"""
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.update_sync_metadata = AsyncMock(return_value=True)
            
            result = await service.mark_sync_complete(
                "courses", "Fall 2025", "Baruch College", "success"
            )
            
            assert result is True
            mock_supabase.update_sync_metadata.assert_called_once_with(
                "courses", "Fall 2025", "Baruch College", "success", None
            )
    
    @pytest.mark.asyncio
    async def test_mark_sync_complete_with_failed_status_and_error(self, service):
        """Should call update_sync_metadata with failed status and error message"""
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.update_sync_metadata = AsyncMock(return_value=True)
            
            result = await service.mark_sync_complete(
                "courses", "Fall 2025", "Baruch College", 
                "failed", "Scraping timeout"
            )
            
            assert result is True
            mock_supabase.update_sync_metadata.assert_called_once_with(
                "courses", "Fall 2025", "Baruch College", "failed", "Scraping timeout"
            )
    
    @pytest.mark.asyncio
    async def test_mark_sync_complete_handles_exception(self, service):
        """Should return False on exception"""
        with patch(
            'mcp_server.services.data_freshness_service.supabase_service'
        ) as mock_supabase:
            mock_supabase.update_sync_metadata = AsyncMock(
                side_effect=Exception("Error")
            )
            
            result = await service.mark_sync_complete(
                "courses", "Fall 2025", "Baruch College", "success"
            )
            
            assert result is False
    
    # ============ _is_expired Helper Tests ============
    
    def test_is_expired_returns_false_for_fresh_timestamp(self, service):
        """Fresh timestamp should not be expired"""
        fresh_time = datetime.now() - timedelta(seconds=100)
        ttl = 3600
        
        result = service._is_expired(fresh_time, ttl)
        
        assert result is False
    
    def test_is_expired_returns_true_for_stale_timestamp(self, service):
        """Stale timestamp should be expired"""
        stale_time = datetime.now() - timedelta(seconds=7200)
        ttl = 3600
        
        result = service._is_expired(stale_time, ttl)
        
        assert result is True
    
    def test_is_expired_at_exact_boundary(self, service):
        """Timestamp exactly at TTL boundary - test boundary behavior"""
        # Use a time slightly before boundary to avoid timing issues
        boundary_time = datetime.now() - timedelta(seconds=3599)
        ttl = 3600
        
        # Slightly before boundary should not be expired
        result = service._is_expired(boundary_time, ttl)
        
        # With > comparison, 3599 seconds elapsed < 3600 TTL = not expired
        assert result is False
    
    def test_is_expired_just_past_boundary(self, service):
        """Timestamp just past TTL should be expired"""
        past_boundary = datetime.now() - timedelta(seconds=3601)
        ttl = 3600
        
        result = service._is_expired(past_boundary, ttl)
        
        assert result is True


class TestDataFreshnessServiceTTLConstants:
    """Tests for TTL constant values"""
    
    def test_course_data_ttl_is_7_days(self):
        """Course data TTL should be 7 days"""
        service = DataFreshnessService()
        expected_ttl = 7 * 24 * 3600  # 7 days in seconds
        
        assert service.COURSE_DATA_TTL == expected_ttl
    
    def test_professor_data_ttl_is_7_days(self):
        """Professor data TTL should be 7 days"""
        service = DataFreshnessService()
        expected_ttl = 7 * 24 * 3600  # 7 days in seconds
        
        assert service.PROFESSOR_DATA_TTL == expected_ttl
    
    def test_review_data_ttl_is_30_days(self):
        """Review data TTL should be 30 days"""
        service = DataFreshnessService()
        expected_ttl = 30 * 24 * 3600  # 30 days in seconds
        
        assert service.REVIEW_DATA_TTL == expected_ttl
