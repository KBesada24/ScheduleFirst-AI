"""
Unit tests for CircuitBreaker
Tests state transitions, request filtering, statistics, and registry management
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from mcp_server.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitState,
)
from mcp_server.utils.exceptions import CircuitBreakerOpenError


class TestCircuitBreakerStateTransitions:
    """Tests for circuit breaker state machine"""
    
    @pytest.fixture
    def breaker(self):
        """Create a circuit breaker with low thresholds for testing"""
        return CircuitBreaker(
            name="test",
            failure_threshold=3,
            recovery_timeout=1,  # 1 second for fast tests
            half_open_max_calls=2
        )
    
    @pytest.mark.asyncio
    async def test_starts_in_closed_state(self, breaker):
        """Circuit breaker should start in CLOSED state"""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed is True
        assert breaker.is_open is False
    
    @pytest.mark.asyncio
    async def test_transitions_to_open_after_failure_threshold(self, breaker):
        """Should transition to OPEN after reaching failure threshold"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Fail threshold times
        for _ in range(3):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open is True
    
    @pytest.mark.asyncio
    async def test_stays_closed_before_threshold(self, breaker):
        """Should stay CLOSED before reaching failure threshold"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Fail less than threshold
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        assert breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_recovery_timeout(self, breaker):
        """Should transition to HALF_OPEN after recovery timeout"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Trip the breaker
        for _ in range(3):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Next request should transition to HALF_OPEN
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        
        # After a success in HALF_OPEN, may transition to CLOSED
        assert breaker.state in [CircuitState.HALF_OPEN, CircuitState.CLOSED]
    
    @pytest.mark.asyncio
    async def test_transitions_to_closed_after_half_open_successes(self, breaker):
        """Should transition to CLOSED after enough successes in HALF_OPEN"""
        async def failing_func():
            raise Exception("Test failure")
        
        async def success_func():
            return "success"
        
        # Trip the breaker
        for _ in range(3):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        # Wait for recovery
        await asyncio.sleep(1.1)
        
        # Succeed enough times in HALF_OPEN
        for _ in range(breaker.half_open_max_calls):
            await breaker.call(success_func)
        
        assert breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_transitions_back_to_open_on_half_open_failure(self, breaker):
        """Should transition back to OPEN if failure occurs in HALF_OPEN"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Trip the breaker
        for _ in range(3):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        # Wait for recovery
        await asyncio.sleep(1.1)
        
        # Fail in HALF_OPEN
        try:
            await breaker.call(failing_func)
        except Exception:
            pass
        
        assert breaker.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_reset_resets_to_closed(self, breaker):
        """Manual reset should return to CLOSED state"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Trip the breaker
        for _ in range(3):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        
        # Reset
        await breaker.reset()
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0


class TestCircuitBreakerRequestFiltering:
    """Tests for request filtering based on state"""
    
    @pytest.fixture
    def breaker(self):
        """Create a circuit breaker for testing"""
        return CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=10,
            half_open_max_calls=2
        )
    
    @pytest.mark.asyncio
    async def test_allows_requests_when_closed(self, breaker):
        """Should allow requests when CLOSED"""
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_rejects_requests_when_open(self, breaker):
        """Should reject requests when OPEN"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Trip the breaker
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        
        # Next request should be rejected
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            async def another_func():
                return "test"
            await breaker.call(another_func)
        
        assert exc_info.value.service_name == "test"
        assert exc_info.value.retry_after_seconds > 0
    
    @pytest.mark.asyncio
    async def test_limits_calls_in_half_open(self, breaker):
        """Should limit number of calls in HALF_OPEN state"""
        # Manually set to HALF_OPEN
        breaker._state = CircuitState.HALF_OPEN
        breaker._half_open_calls = 0
        
        async def success_func():
            return "success"
        
        # First two calls should succeed
        await breaker.call(success_func)
        await breaker.call(success_func)
        
        # After max calls in HALF_OPEN, should be CLOSED or still limiting
        # Based on implementation, 2 successes should close the circuit
        assert breaker.state == CircuitState.CLOSED


class TestCircuitBreakerStatistics:
    """Tests for statistics tracking"""
    
    @pytest.fixture
    def breaker(self):
        """Create a circuit breaker for testing"""
        return CircuitBreaker(
            name="test",
            failure_threshold=5,
            recovery_timeout=60
        )
    
    @pytest.mark.asyncio
    async def test_tracks_total_calls(self, breaker):
        """Should track total call count"""
        async def success_func():
            return "success"
        
        for _ in range(5):
            await breaker.call(success_func)
        
        stats = breaker.get_stats()
        assert stats["total_calls"] == 5
    
    @pytest.mark.asyncio
    async def test_tracks_successful_calls(self, breaker):
        """Should track successful call count"""
        async def success_func():
            return "success"
        
        for _ in range(3):
            await breaker.call(success_func)
        
        stats = breaker.get_stats()
        assert stats["successful_calls"] == 3
    
    @pytest.mark.asyncio
    async def test_tracks_failed_calls(self, breaker):
        """Should track failed call count"""
        async def failing_func():
            raise Exception("Test failure")
        
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        stats = breaker.get_stats()
        assert stats["failed_calls"] == 2
    
    @pytest.mark.asyncio
    async def test_tracks_rejected_calls(self, breaker):
        """Should track rejected call count when circuit is open"""
        breaker.failure_threshold = 2
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Trip the breaker
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        # Try more calls that will be rejected
        for _ in range(3):
            try:
                await breaker.call(failing_func)
            except CircuitBreakerOpenError:
                pass
        
        stats = breaker.get_stats()
        assert stats["rejected_calls"] == 3
    
    @pytest.mark.asyncio
    async def test_tracks_state_changes(self, breaker):
        """Should track state change count"""
        breaker.failure_threshold = 2
        
        async def failing_func():
            raise Exception("Test failure")
        
        initial_changes = breaker.get_stats()["state_changes"]
        
        # Trip the breaker
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        stats = breaker.get_stats()
        assert stats["state_changes"] > initial_changes
    
    def test_get_stats_returns_current_state(self, breaker):
        """get_stats should include current state"""
        stats = breaker.get_stats()
        
        assert stats["name"] == "test"
        assert stats["state"] == "closed"
        assert "failure_count" in stats
        assert "success_count" in stats


class TestCircuitBreakerExcludedExceptions:
    """Tests for excluded exception handling"""
    
    @pytest.mark.asyncio
    async def test_excluded_exceptions_not_counted_as_failures(self):
        """Excluded exceptions should not count toward failure threshold"""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=60,
            excluded_exceptions=(ValueError,)
        )
        
        async def value_error_func():
            raise ValueError("Expected error")
        
        # These should not count as failures
        for _ in range(5):
            with pytest.raises(ValueError):
                await breaker.call(value_error_func)
        
        # Circuit should still be closed
        assert breaker.state == CircuitState.CLOSED
        stats = breaker.get_stats()
        assert stats["failure_count"] == 0
    
    @pytest.mark.asyncio
    async def test_non_excluded_exceptions_counted_as_failures(self):
        """Non-excluded exceptions should count toward failure threshold"""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=60,
            excluded_exceptions=(ValueError,)
        )
        
        async def type_error_func():
            raise TypeError("Unexpected error")
        
        # These should count as failures
        for _ in range(2):
            with pytest.raises(TypeError):
                await breaker.call(type_error_func)
        
        # Circuit should be open
        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerDecorator:
    """Tests for the @protected decorator"""
    
    @pytest.mark.asyncio
    async def test_protected_decorator_wraps_function(self):
        """@protected decorator should wrap function with circuit breaker"""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=3,
            recovery_timeout=60
        )
        
        @breaker.protected
        async def my_function():
            return "success"
        
        result = await my_function()
        
        assert result == "success"
        stats = breaker.get_stats()
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1
    
    @pytest.mark.asyncio
    async def test_protected_decorator_handles_failures(self):
        """@protected decorator should track failures"""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=3,
            recovery_timeout=60
        )
        
        @breaker.protected
        async def failing_function():
            raise RuntimeError("Test error")
        
        with pytest.raises(RuntimeError):
            await failing_function()
        
        stats = breaker.get_stats()
        assert stats["failed_calls"] == 1


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry"""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry for testing"""
        return CircuitBreakerRegistry()
    
    def test_register_creates_new_breaker(self, registry):
        """Should create and return new circuit breaker"""
        breaker = registry.register(
            "test_service",
            failure_threshold=5,
            recovery_timeout=60
        )
        
        assert breaker is not None
        assert breaker.name == "test_service"
        assert breaker.failure_threshold == 5
    
    def test_register_returns_existing_breaker(self, registry):
        """Should return existing breaker if already registered"""
        breaker1 = registry.register("test_service", failure_threshold=5)
        breaker2 = registry.register("test_service", failure_threshold=10)
        
        assert breaker1 is breaker2
        # Should keep original configuration
        assert breaker1.failure_threshold == 5
    
    def test_get_returns_registered_breaker(self, registry):
        """Should return breaker by name"""
        registry.register("my_service")
        
        breaker = registry.get("my_service")
        
        assert breaker is not None
        assert breaker.name == "my_service"
    
    def test_get_returns_none_for_unknown(self, registry):
        """Should return None for unregistered service"""
        breaker = registry.get("unknown_service")
        
        assert breaker is None
    
    def test_get_all_stats_returns_all_breaker_stats(self, registry):
        """Should return stats for all registered breakers"""
        registry.register("service_a")
        registry.register("service_b")
        registry.register("service_c")
        
        all_stats = registry.get_all_stats()
        
        assert len(all_stats) == 3
        assert "service_a" in all_stats
        assert "service_b" in all_stats
        assert "service_c" in all_stats
    
    def test_get_all_states_returns_all_breaker_states(self, registry):
        """Should return states for all registered breakers"""
        registry.register("service_a")
        registry.register("service_b")
        
        all_states = registry.get_all_states()
        
        assert all_states == {
            "service_a": "closed",
            "service_b": "closed"
        }
    
    @pytest.mark.asyncio
    async def test_reset_all_resets_all_breakers(self, registry):
        """Should reset all registered breakers"""
        breaker_a = registry.register("service_a", failure_threshold=1)
        breaker_b = registry.register("service_b", failure_threshold=1)
        
        # Trip both breakers
        async def failing_func():
            raise Exception("Test")
        
        try:
            await breaker_a.call(failing_func)
        except Exception:
            pass
        
        try:
            await breaker_b.call(failing_func)
        except Exception:
            pass
        
        assert breaker_a.state == CircuitState.OPEN
        assert breaker_b.state == CircuitState.OPEN
        
        # Reset all
        await registry.reset_all()
        
        assert breaker_a.state == CircuitState.CLOSED
        assert breaker_b.state == CircuitState.CLOSED


class TestCircuitBreakerConfiguration:
    """Tests for circuit breaker configuration"""
    
    def test_default_configuration(self):
        """Should use default values when not specified"""
        breaker = CircuitBreaker(name="test")
        
        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 60
        assert breaker.half_open_max_calls == 3
    
    def test_custom_configuration(self):
        """Should use custom values when specified"""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=10,
            recovery_timeout=120,
            half_open_max_calls=5
        )
        
        assert breaker.failure_threshold == 10
        assert breaker.recovery_timeout == 120
        assert breaker.half_open_max_calls == 5
    
    def test_name_property(self):
        """Should expose name property"""
        breaker = CircuitBreaker(name="my_service")
        
        assert breaker.name == "my_service"


class TestGlobalCircuitBreakers:
    """Tests for pre-configured global circuit breakers"""
    
    def test_ratemyprof_breaker_exists(self):
        """Global ratemyprof breaker should be configured"""
        from mcp_server.utils.circuit_breaker import ratemyprof_breaker
        
        assert ratemyprof_breaker is not None
        assert ratemyprof_breaker.name == "ratemyprof"
    
    def test_cuny_scraper_breaker_exists(self):
        """Global CUNY scraper breaker should be configured"""
        from mcp_server.utils.circuit_breaker import cuny_scraper_breaker
        
        assert cuny_scraper_breaker is not None
        assert cuny_scraper_breaker.name == "cuny_scraper"
    
    def test_supabase_breaker_exists(self):
        """Global Supabase breaker should be configured"""
        from mcp_server.utils.circuit_breaker import supabase_breaker
        
        assert supabase_breaker is not None
        assert supabase_breaker.name == "supabase"
    
    def test_ollama_breaker_exists(self):
        """Global Ollama breaker should be configured"""
        from mcp_server.utils.circuit_breaker import ollama_breaker
        
        assert ollama_breaker is not None
        assert ollama_breaker.name == "ollama"
    
    def test_global_registry_contains_all_breakers(self):
        """Global registry should contain all pre-configured breakers"""
        from mcp_server.utils.circuit_breaker import circuit_breaker_registry
        
        all_states = circuit_breaker_registry.get_all_states()
        
        assert "ratemyprof" in all_states
        assert "cuny_scraper" in all_states
        assert "supabase" in all_states
        assert "ollama" in all_states
