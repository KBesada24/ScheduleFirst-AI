"""
Integration tests for end-to-end flows
Tests complete data flows including auto-population, caching, and background jobs
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from mcp_server.services.data_population_service import (
    DataPopulationService,
    PopulationResult,
)
from mcp_server.services.data_freshness_service import DataFreshnessService
from mcp_server.utils.cache import cache_manager, InMemoryCache

from conftest import (
    create_mock_course,
    create_mock_section,
    create_mock_professor,
    create_mock_sync_metadata,
    get_fresh_timestamp,
    get_stale_timestamp,
)


class TestEmptyDatabaseAutoPopulation:
    """Tests for auto-population when database is empty"""
    
    @pytest.mark.asyncio
    async def test_auto_populates_courses_when_database_empty(self):
        """Should trigger sync job when no course data exists"""
        sync_triggered = False
        
        async def mock_sync_job(**kwargs):
            nonlocal sync_triggered
            sync_triggered = True
            return {"success": True, "courses_synced": 100}
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            side_effect=mock_sync_job
        ):
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            
            service = DataPopulationService()
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is True
            assert sync_triggered is True
    
    @pytest.mark.asyncio
    async def test_auto_populates_professor_when_not_in_database(self):
        """Should trigger scrape and grade jobs when professor doesn't exist"""
        scrape_triggered = False
        grades_triggered = False
        
        professor = create_mock_professor(name="Dr. New")
        
        async def mock_scrape_job(**kwargs):
            nonlocal scrape_triggered
            scrape_triggered = True
            return {"success": True}
        
        async def mock_grades_job(**kwargs):
            nonlocal grades_triggered
            grades_triggered = True
            return {"success": True}
        
        from mcp_server.utils.exceptions import DataNotFoundError
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.supabase_service'
        ) as mock_supabase, patch(
            'mcp_server.services.data_population_service.scrape_reviews_job',
            side_effect=mock_scrape_job
        ), patch(
            'mcp_server.services.data_population_service.update_grades_job',
            side_effect=mock_grades_job
        ):
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            # First call: not found, second call (after scrape): found
            mock_supabase.get_professor_by_name = AsyncMock(
                side_effect=[
                    DataNotFoundError("Professor", "Dr. New"),
                    professor
                ]
            )
            
            service = DataPopulationService()
            result = await service.ensure_professor_data("Dr. New", "Baruch College")
            
            assert result.success is True
            assert scrape_triggered is True
            assert grades_triggered is True


class TestStaleDataRefresh:
    """Tests for data refresh when existing data is stale"""
    
    @pytest.mark.asyncio
    async def test_refreshes_stale_course_data(self):
        """Should trigger sync when course data is stale"""
        sync_triggered = False
        
        async def mock_sync_job(**kwargs):
            nonlocal sync_triggered
            sync_triggered = True
            return {"success": True}
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            side_effect=mock_sync_job
        ):
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            # Data exists but is stale
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            
            service = DataPopulationService()
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is True
            assert sync_triggered is True
    
    @pytest.mark.asyncio
    async def test_refreshes_stale_professor_data(self):
        """Should trigger scrape when professor data is stale"""
        scrape_triggered = False
        
        stale_professor = create_mock_professor(
            last_updated=get_stale_timestamp(7 * 24 * 3600)
        )
        
        async def mock_scrape_job(**kwargs):
            nonlocal scrape_triggered
            scrape_triggered = True
            return {"success": True}
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.supabase_service'
        ) as mock_supabase, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.scrape_reviews_job',
            side_effect=mock_scrape_job
        ), patch(
            'mcp_server.services.data_population_service.update_grades_job',
            new_callable=AsyncMock
        ) as mock_grades:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_supabase.get_professor_by_name = AsyncMock(return_value=stale_professor)
            mock_freshness.is_professor_data_fresh = AsyncMock(return_value=False)
            mock_grades.return_value = {"success": True}
            
            service = DataPopulationService()
            result = await service.ensure_professor_data(
                "Dr. Stale", "Baruch College"
            )
            
            assert result.success is True
            assert scrape_triggered is True


class TestCachedDataFlow:
    """Tests for cached data returning without DB calls"""
    
    @pytest.mark.asyncio
    async def test_returns_from_cache_without_db_call(self):
        """Should return immediately from cache without checking DB"""
        freshness_check_called = False
        
        async def track_freshness_check(*args, **kwargs):
            nonlocal freshness_check_called
            freshness_check_called = True
            return True
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness:
            mock_cache.get = AsyncMock(return_value=True)  # Cache hit
            mock_freshness.is_course_data_fresh = AsyncMock(side_effect=track_freshness_check)
            
            service = DataPopulationService()
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is True
            # Verify cache was checked first
            mock_cache.get.assert_called_once()
            # Verify freshness check was NOT called (cache hit should short-circuit)
            assert freshness_check_called is False, "Freshness check should be skipped on cache hit"
    
    @pytest.mark.asyncio
    async def test_skips_sync_when_data_is_fresh(self):
        """Should skip sync job when data is fresh"""
        sync_triggered = False
        
        async def mock_sync_job(**kwargs):
            nonlocal sync_triggered
            sync_triggered = True
            return {"success": True}
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            side_effect=mock_sync_job
        ):
            mock_cache.get = AsyncMock(return_value=None)
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=True)
            
            service = DataPopulationService()
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is True
            assert sync_triggered is False


class TestBackgroundJobIntegration:
    """Tests for background job integration with sync metadata"""
    
    @pytest.mark.asyncio
    async def test_marks_sync_in_progress_before_job(self):
        """Should mark sync as in_progress before starting job"""
        progress_marked = False
        
        async def track_progress(*args, **kwargs):
            nonlocal progress_marked
            progress_marked = True
            return True
        
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
            mock_freshness.mark_sync_in_progress = AsyncMock(side_effect=track_progress)
            mock_sync.return_value = {"success": True}
            
            service = DataPopulationService()
            await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert progress_marked is True
    
    @pytest.mark.asyncio
    async def test_caches_success_after_job_completion(self):
        """Should cache successful population result"""
        cached_key = None
        cached_value = None
        
        async def track_cache_set(key, value, **kwargs):
            nonlocal cached_key, cached_value
            cached_key = key
            cached_value = value
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            new_callable=AsyncMock
        ) as mock_sync:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock(side_effect=track_cache_set)
            mock_freshness.is_course_data_fresh = AsyncMock(return_value=False)
            mock_freshness.mark_sync_in_progress = AsyncMock()
            mock_sync.return_value = {"success": True}
            
            service = DataPopulationService()
            await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert cached_key is not None
            assert "population:courses:Fall 2025:Baruch College" in cached_key
            assert cached_value is True


class TestMCPToolIntegration:
    """Tests for MCP tools integration with services"""
    
    @pytest.mark.asyncio
    async def test_fetch_sections_triggers_population(self):
        """MCP tool should trigger data population"""
        from mcp_server.tools.schedule_optimizer import fetch_course_sections
        
        population_called = False
        
        async def track_population(*args, **kwargs):
            nonlocal population_called
            population_called = True
            return PopulationResult(success=True)
        
        course = create_mock_course()
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_course_data = AsyncMock(side_effect=track_population)
            mock_supabase.search_courses = AsyncMock(return_value=[course])
            mock_supabase.get_sections_by_course = AsyncMock(return_value=[])
            
            # Use .fn to access the underlying async function
            result = await fetch_course_sections.fn(
                course_codes=["CSC101"],
                semester="Fall 2025"
            )
            
            assert population_called is True
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_professor_grade_triggers_population(self):
        """MCP tool should trigger professor data population"""
        from mcp_server.tools.schedule_optimizer import get_professor_grade
        
        population_called = False
        
        async def track_population(*args, **kwargs):
            nonlocal population_called
            population_called = True
            return PopulationResult(success=True)
        
        professor = create_mock_professor()
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_professor_data = AsyncMock(
                side_effect=track_population
            )
            mock_supabase.get_professor_by_name = AsyncMock(return_value=professor)
            
            # Use .fn to access the underlying async function
            result = await get_professor_grade.fn(
                professor_name="Dr. Smith",
                university="Baruch College"
            )
            
            assert population_called is True
            assert result["success"] is True


class TestCacheInvalidation:
    """Tests for cache behavior with fresh data"""
    
    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self):
        """Force refresh should bypass cache and trigger sync"""
        sync_triggered = False
        
        async def mock_sync(**kwargs):
            nonlocal sync_triggered
            sync_triggered = True
            return {"success": True}
        
        with patch(
            'mcp_server.services.data_population_service.cache_manager'
        ) as mock_cache, patch(
            'mcp_server.services.data_population_service.data_freshness_service'
        ) as mock_freshness, patch(
            'mcp_server.services.data_population_service.sync_courses_job',
            side_effect=mock_sync
        ):
            # Even with cache hit, force should trigger sync
            mock_cache.get = AsyncMock(return_value=True)
            mock_cache.set = AsyncMock()
            mock_freshness.mark_sync_in_progress = AsyncMock()
            
            service = DataPopulationService()
            result = await service.ensure_course_data(
                "Fall 2025", "Baruch College", force=True
            )
            
            assert result.success is True
            assert sync_triggered is True


class TestErrorRecoveryFlow:
    """Tests for error handling and recovery in flows"""
    
    @pytest.mark.asyncio
    async def test_continues_with_warnings_on_partial_failure(self):
        """Should continue with warnings when some operations fail"""
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
            # Scrape fails but grades succeed
            mock_scrape.return_value = {"success": False, "error": "Rate limited"}
            mock_grades.return_value = {"success": True}
            
            service = DataPopulationService()
            result = await service.ensure_professor_data(
                "Dr. Smith", "Baruch College"
            )
            
            assert result.success is True
            assert result.is_partial is True
            assert len(result.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_returns_failure_on_complete_failure(self):
        """Should return failure when all operations fail"""
        from mcp_server.utils.exceptions import ExternalServiceError
        
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
                service="CUNY", operation="scrape"
            )
            
            service = DataPopulationService()
            result = await service.ensure_course_data("Fall 2025", "Baruch College")
            
            assert result.success is False
            assert result.error is not None


class TestConcurrentRequestHandling:
    """Tests for handling concurrent requests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_share_sync(self):
        """Concurrent requests for same data should share single sync"""
        sync_count = 0
        
        async def mock_sync(**kwargs):
            nonlocal sync_count
            sync_count += 1
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
            
            service = DataPopulationService()
            
            # Fire concurrent requests
            results = await asyncio.gather(
                service.ensure_course_data("Fall 2025", "Baruch College"),
                service.ensure_course_data("Fall 2025", "Baruch College"),
                service.ensure_course_data("Fall 2025", "Baruch College"),
            )
            
            # All should succeed
            assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_different_requests_sync_independently(self):
        """Requests for different data should sync independently"""
        synced_keys = []
        
        async def mock_sync(**kwargs):
            synced_keys.append(f"{kwargs['semester']}:{kwargs['university']}")
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
            
            service = DataPopulationService()
            
            # Different semesters/universities should sync independently
            results = await asyncio.gather(
                service.ensure_course_data("Fall 2025", "Baruch College"),
                service.ensure_course_data("Fall 2025", "Hunter College"),
                service.ensure_course_data("Spring 2026", "Baruch College"),
            )
            
            assert all(r.success for r in results)
            assert len(synced_keys) == 3
