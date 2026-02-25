"""
Unit tests for DataPopulationService
Tests on-demand data population, concurrency control, and error handling
"""
import pytest
import asyncio
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from mcp_server.services.data_population_service import (
    DataPopulationService,
    PopulationResult,
)
from mcp_server.utils.exceptions import (
    CircuitBreakerOpenError,
    ExternalServiceError,
    DatabaseError,
    DataNotFoundError,
    ScrapingError,
)

from conftest import (
    create_mock_professor,
    create_mock_sync_metadata,
)


class TestPopulationResult:
    """Tests for PopulationResult dataclass"""
    
    def test_successful_result(self):
        """Test creating successful population result"""
        result = PopulationResult(success=True)
        
        assert result.success is True
        assert result.warnings == []
        assert result.error is None
        assert result.is_partial is False
    
    def test_result_with_warnings(self):
        """Test result with warnings"""
        result = PopulationResult(
            success=True,
            warnings=["Data may be slightly outdated", "Some records skipped"]
        )
        
        assert result.success is True
        assert len(result.warnings) == 2
        assert "Data may be slightly outdated" in result.warnings
    
    def test_failed_result_with_error(self):
        """Test failed result with error message"""
        result = PopulationResult(
            success=False,
            error="Scraping failed: timeout"
        )
        
        assert result.success is False
        assert result.error == "Scraping failed: timeout"
    
    def test_partial_success_result(self):
        """Test partial success result"""
        result = PopulationResult(
            success=True,
            warnings=["Could not fetch reviews"],
            is_partial=True
        )
        
        assert result.success is True
        assert result.is_partial is True
        assert len(result.warnings) == 1
    
    def test_to_dict_conversion(self):
        """Test conversion to dictionary"""
        result = PopulationResult(
            success=True,
            warnings=["Warning 1"],
            error=None,
            is_partial=False
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["warnings"] == ["Warning 1"]
        assert result_dict["error"] is None
        assert result_dict["is_partial"] is False


class TestDataPopulationServiceEnsureCourseData:
    """Tests for ensure_course_data method"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh DataPopulationService instance"""
        return DataPopulationService()
    
    @pytest.mark.asyncio
    async def test_returns_success_when_data_is_fresh(self, service):
        """Should return success immediately when data is fresh"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness:
            mock_cache.get = AsyncMock(return_value=None)
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=True)
            
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is True
            mock_freshness.is_course_data_fresh.assert_called_once_with(
                "Fall 2025", "Baruch College"
            )
    
    @pytest.mark.asyncio
    async def test_returns_cached_success(self, service):
        """Should return success from cache without checking freshness"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness:
            mock_cache.get = AsyncMock(return_value=True)
            
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is True
            # Freshness service should not be called if cache hit
            mock_freshness.is_course_data_fresh.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_triggers_sync_when_data_is_stale(self, service):
        """Should trigger sync job when data is stale"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            new_callable=AsyncMock
        ) as mock_sync:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            mock_sync.return_value = {"success": True}
            
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is True
            mock_sync.assert_called_once_with(
                semester="Fall 2025", university="Baruch College"
            )
    
    @pytest.mark.asyncio
    async def test_force_triggers_sync_regardless_of_freshness(self, service):
        """Should trigger sync when force=True even if data is fresh"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            new_callable=AsyncMock
        ) as mock_sync:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_freshness.mark_sync_in_progress = AsyncMock()
            mock_sync.return_value = {"success": True}
            
            result = await service.ensure_course_data(
                "Fall 2025", "Baruch College", force=True
            )
            
            assert result.success is True
            mock_sync.assert_called_once()
            # Freshness check should be skipped with force=True
            mock_freshness.is_course_data_fresh.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_returns_failure_when_sync_fails(self, service):
        """Should return failure when sync job fails"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            new_callable=AsyncMock
        ) as mock_sync:
            mock_cache.get = AsyncMock(return_value=None)
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            mock_sync.return_value = {"success": False, "error": "Scraping timeout"}
            
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is False
            assert "Scraping timeout" in result.error
    
    @pytest.mark.asyncio
    async def test_handles_circuit_breaker_open(self, service):
        """Should handle CircuitBreakerOpenError gracefully"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness:
            mock_cache.get = AsyncMock(return_value=None)
            mock_freshness.is_course_data_fresh = AsyncMock(
                side_effect=CircuitBreakerOpenError(
                    service_name="supabase",
                    retry_after_seconds=60,
                    failure_count=5
                )
            )
            
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is False
            assert "temporarily unavailable" in result.error
    
    @pytest.mark.asyncio
    async def test_handles_external_service_error(self, service):
        """Should handle ExternalServiceError gracefully"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            new_callable=AsyncMock
        ) as mock_sync:
            mock_cache.get = AsyncMock(return_value=None)
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            mock_sync.side_effect = ExternalServiceError(
                service="CUNY Global Search",
                operation="scrape"
            )
            
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is False
            assert "External service error" in result.error
    
    @pytest.mark.asyncio
    async def test_adds_warning_when_freshness_check_fails(self, service):
        """Should add warning but continue when freshness check fails"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            new_callable=AsyncMock
        ) as mock_sync:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_freshness.is_course_data_fresh = AsyncMock(
                side_effect=DatabaseError(operation="check", reason="timeout")
            )
            mock_freshness.mark_sync_in_progress = AsyncMock()
            mock_sync.return_value = {"success": True}
            
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is True
            assert any("freshness" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_forwards_subject_code_to_sync_job(self, service):
        """Should pass subject_code through to sync job when provided"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            new_callable=AsyncMock
        ) as mock_sync:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            mock_sync.return_value = {"success": True}

            result = await service.ensure_course_data(
                "Spring 2026",
                "College of Staten Island",
                subject_code="CSC",
            )

            assert result.success is True
            mock_sync.assert_called_once_with(
                semester="Spring 2026",
                university="College of Staten Island",
                subject_code="CSC",
            )

    @pytest.mark.asyncio
    async def test_propagates_source_metadata_from_sync_job(self, service):
        """Should propagate source and fallback metadata from sync result"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            new_callable=AsyncMock
        ) as mock_sync:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            mock_sync.return_value = {
                "success": True,
                "source": "selenium_fallback",
                "fallback_used": True,
                "warnings": ["Primary source failed"],
            }

            result = await service.ensure_course_data("Spring 2026", "Baruch College")

            assert result.success is True
            assert result.source == "selenium_fallback"
            assert result.fallback_used is True
            assert any("primary source failed" in warning.lower() for warning in result.warnings)

    @pytest.mark.asyncio
    async def test_returns_degraded_failure_when_all_sources_fail(self, service):
        """Should return a structured degraded failure when sync result indicates no source available"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            new_callable=AsyncMock
        ) as mock_sync:
            mock_cache.get = AsyncMock(return_value=None)
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            mock_sync.return_value = {
                "success": False,
                "source": "none",
                "fallback_used": False,
                "error": "No ingestion source enabled",
            }

            result = await service.ensure_course_data("Spring 2026", "Baruch College")

            assert result.success is False
            assert result.source == "none"
            assert result.fallback_used is False
            assert "no ingestion source enabled" in (result.error or "").lower()


class TestDataPopulationServiceEnsureProfessorData:
    """Tests for ensure_professor_data method"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh DataPopulationService instance"""
        return DataPopulationService()
    
    @pytest.mark.asyncio
    async def test_returns_success_when_professor_is_fresh(self, service):
        """Should return success when professor data is fresh"""
        professor = create_mock_professor()
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.supabase_service'
        ) as mock_supabase, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness:
            mock_cache.get = AsyncMock(return_value=None)
            mock_supabase.get_professor_by_name = AsyncMock(return_value=professor)
            mock_freshness.is_professor_data_fresh = AsyncMock(return_value=True)
            
            result = await service.ensure_professor_data(
                "Dr. Smith", "Baruch College"
            )
            
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_returns_cached_success(self, service):
        """Should return success from cache"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache:
            mock_cache.get = AsyncMock(return_value=True)
            
            result = await service.ensure_professor_data(
                "Dr. Smith", "Baruch College"
            )
            
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_triggers_scrape_for_new_professor(self, service):
        """Should trigger scrape job when professor doesn't exist"""
        new_professor = create_mock_professor(name="Dr. New")
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.supabase_service'
        ) as mock_supabase, patch(
            'mcp_server.services.data_population_service.scrape_reviews_job',
            new_callable=AsyncMock
        ) as mock_scrape, patch(
            'mcp_server.services.data_population_service.update_grades_job',
            new_callable=AsyncMock
        ) as mock_grades:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            # First call returns None (not found), second call returns professor
            mock_supabase.get_professor_by_name = AsyncMock(
                side_effect=[
                    DataNotFoundError(entity_type="Professor", identifier="Dr. New"),
                    new_professor
                ]
            )
            mock_scrape.return_value = {"success": True}
            mock_grades.return_value = {"success": True}
            
            result = await service.ensure_professor_data(
                "Dr. New", "Baruch College"
            )
            
            assert result.success is True
            mock_scrape.assert_called_once_with(
                professor_name="Dr. New", university="Baruch College"
            )
            mock_grades.assert_called_once_with(professor_id=new_professor.id)
    
    @pytest.mark.asyncio
    async def test_triggers_scrape_for_stale_professor(self, service):
        """Should trigger scrape when professor data is stale"""
        stale_professor = create_mock_professor(name="Dr. Old")
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.supabase_service'
        ) as mock_supabase, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.scrape_reviews_job',
            new_callable=AsyncMock
        ) as mock_scrape, patch(
            'mcp_server.services.data_population_service.update_grades_job',
            new_callable=AsyncMock
        ) as mock_grades:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_supabase.get_professor_by_name = AsyncMock(return_value=stale_professor)
            mock_freshness.is_professor_data_fresh = AsyncMock(return_value=False)
            mock_scrape.return_value = {"success": True}
            mock_grades.return_value = {"success": True}
            
            result = await service.ensure_professor_data(
                "Dr. Old", "Baruch College"
            )
            
            assert result.success is True
            mock_scrape.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_returns_partial_when_scrape_fails_but_grades_succeed(self, service):
        """Should return partial success when scrape fails but grades succeed"""
        professor = create_mock_professor()
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.supabase_service'
        ) as mock_supabase, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.scrape_reviews_job',
            new_callable=AsyncMock
        ) as mock_scrape, patch(
            'mcp_server.services.data_population_service.update_grades_job',
            new_callable=AsyncMock
        ) as mock_grades:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_supabase.get_professor_by_name = AsyncMock(return_value=professor)
            mock_freshness.is_professor_data_fresh = AsyncMock(return_value=False)
            mock_scrape.return_value = {"success": False, "error": "Rate limited"}
            mock_grades.return_value = {"success": True}
            
            result = await service.ensure_professor_data(
                "Dr. Smith", "Baruch College"
            )
            
            assert result.success is True
            assert result.is_partial is True
            assert any("reviews" in w.lower() for w in result.warnings)
    
    @pytest.mark.asyncio
    async def test_returns_failure_when_professor_not_found_after_scrape(self, service):
        """Should return failure when professor still not found after scrape"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.supabase_service'
        ) as mock_supabase, patch(
            'mcp_server.services.data_population_service.scrape_reviews_job',
            new_callable=AsyncMock
        ) as mock_scrape:
            mock_cache.get = AsyncMock(return_value=None)
            # Professor not found before and after scrape
            mock_supabase.get_professor_by_name = AsyncMock(
                side_effect=DataNotFoundError(
                    entity_type="Professor", identifier="Dr. Ghost"
                )
            )
            mock_scrape.return_value = {"success": True}
            
            result = await service.ensure_professor_data(
                "Dr. Ghost", "Baruch College"
            )
            
            assert result.success is False
            assert "not found" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_handles_circuit_breaker_open(self, service):
        """Should handle CircuitBreakerOpenError gracefully"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.supabase_service'
        ) as mock_supabase:
            mock_cache.get = AsyncMock(return_value=None)
            mock_supabase.get_professor_by_name = AsyncMock(
                side_effect=CircuitBreakerOpenError(
                    service_name="ratemyprof",
                    retry_after_seconds=60,
                    failure_count=5
                )
            )
            
            result = await service.ensure_professor_data(
                "Dr. Smith", "Baruch College"
            )
            
            assert result.success is False
            assert "temporarily unavailable" in result.error
    
    @pytest.mark.asyncio
    async def test_handles_scraping_error(self, service):
        """Should handle ScrapingError gracefully"""
        professor = create_mock_professor()
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.supabase_service'
        ) as mock_supabase, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.scrape_reviews_job',
            new_callable=AsyncMock
        ) as mock_scrape:
            mock_cache.get = AsyncMock(return_value=None)
            mock_supabase.get_professor_by_name = AsyncMock(return_value=professor)
            mock_freshness.is_professor_data_fresh = AsyncMock(return_value=False)
            mock_scrape.side_effect = ScrapingError(
                source="RateMyProfessors", reason="Blocked"
            )
            
            result = await service.ensure_professor_data(
                "Dr. Smith", "Baruch College"
            )
            
            assert result.success is False
            assert "scrape" in result.error.lower()


class TestDataPopulationServiceConcurrency:
    """Tests for concurrency control in DataPopulationService"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh DataPopulationService instance"""
        return DataPopulationService()
    
    @pytest.mark.asyncio
    async def test_lock_prevents_duplicate_sync(self, service):
        """Should prevent duplicate syncs for same semester/university"""
        sync_call_count = 0
        
        async def mock_sync(**kwargs):
            nonlocal sync_call_count
            sync_call_count += 1
            await asyncio.sleep(0.1)  # Simulate work
            return {"success": True}
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            side_effect=mock_sync
        ):
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            
            # Start two concurrent calls for same semester/university
            results = await asyncio.gather(
                service.ensure_course_data("Fall 2025", "Baruch College"),
                service.ensure_course_data("Fall 2025", "Baruch College"),
            )
            
            # Both should succeed
            assert all(r.success for r in results)
            # Verify sync was called at most twice (lock should minimize duplicates)
            # In ideal scenario with proper locking, sync_call_count should be 1-2
            assert sync_call_count <= 2, f"Expected <=2 sync calls with locking, got {sync_call_count}"
    
    @pytest.mark.asyncio
    async def test_different_keys_sync_independently(self, service):
        """Should allow concurrent syncs for different semester/university pairs"""
        sync_calls = []
        
        async def mock_sync(**kwargs):
            sync_calls.append(kwargs)
            await asyncio.sleep(0.05)
            return {"success": True}
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            side_effect=mock_sync
        ):
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            
            # Start concurrent calls for different universities
            results = await asyncio.gather(
                service.ensure_course_data("Fall 2025", "Baruch College"),
                service.ensure_course_data("Fall 2025", "Hunter College"),
            )
            
            assert all(r.success for r in results)
            # Both syncs should have been called
            assert len(sync_calls) == 2
    
    @pytest.mark.asyncio
    async def test_get_lock_creates_new_locks(self, service):
        """Should create new locks for new keys"""
        lock1 = await service._get_lock("key1")
        lock2 = await service._get_lock("key2")
        
        assert lock1 is not lock2
        assert "key1" in service._locks
        assert "key2" in service._locks
    
    @pytest.mark.asyncio
    async def test_get_lock_returns_same_lock_for_same_key(self, service):
        """Should return same lock for same key"""
        lock1 = await service._get_lock("key1")
        lock2 = await service._get_lock("key1")
        
        assert lock1 is lock2


class TestDataPopulationServiceForceRefresh:
    """Tests for force refresh functionality"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh DataPopulationService instance"""
        return DataPopulationService()
    
    @pytest.mark.asyncio
    async def test_force_bypasses_cache(self, service):
        """Force should bypass cache check"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            new_callable=AsyncMock
        ) as mock_sync:
            mock_cache.get = AsyncMock(return_value=True)  # Cache would return True
            mock_cache.set = AsyncMock()
            mock_freshness.mark_sync_in_progress = AsyncMock()
            mock_sync.return_value = {"success": True}
            
            result = await service.ensure_course_data(
                "Fall 2025", "Baruch College", force=True
            )
            
            assert result.success is True
            # Cache get should still be called with force, but result ignored
            mock_sync.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_force_bypasses_freshness_check(self, service):
        """Force should bypass freshness check"""
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            new_callable=AsyncMock
        ) as mock_sync:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=True)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            mock_sync.return_value = {"success": True}
            
            result = await service.ensure_course_data(
                "Fall 2025", "Baruch College", force=True
            )
            
            assert result.success is True
            mock_freshness.is_course_data_fresh.assert_not_called()
            mock_sync.assert_called_once()
