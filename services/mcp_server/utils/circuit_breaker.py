"""
Circuit Breaker Pattern Implementation
Prevents cascading failures by temporarily blocking requests to failing services
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict
from functools import wraps
from enum import Enum

from .logger import get_logger


logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation, requests allowed
    OPEN = "open"           # Failing, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered


class CircuitBreaker:
    """
    Async-compatible circuit breaker for protecting external service calls.
    
    States:
        - CLOSED: Normal operation, all requests pass through
        - OPEN: Service failing, all requests immediately rejected
        - HALF_OPEN: Testing recovery, limited requests allowed
    
    Configuration:
        - failure_threshold: Number of failures before opening circuit
        - recovery_timeout: Seconds to wait before testing recovery
        - half_open_max_calls: Number of test calls allowed in half-open state
    
    Usage:
        breaker = CircuitBreaker("ratemyprof", failure_threshold=5, recovery_timeout=60)
        
        @breaker.protected
        async def call_ratemyprof():
            ...
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
        excluded_exceptions: Optional[tuple] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Identifier for this circuit breaker (for logging)
            failure_threshold: Number of consecutive failures to open circuit
            recovery_timeout: Seconds to wait in open state before testing
            half_open_max_calls: Max calls allowed in half-open state
            excluded_exceptions: Exception types that should not count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.excluded_exceptions = excluded_exceptions or ()
        
        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        
        # Lock for thread-safe state changes
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "rejected_calls": 0,
            "state_changes": 0
        }
        
        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"threshold={failure_threshold}, recovery={recovery_timeout}s"
        )
    
    @property
    def state(self) -> CircuitState:
        """Current circuit state"""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is allowing requests"""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is blocking requests"""
        return self._state == CircuitState.OPEN
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None,
            **self._stats
        }
    
    async def _should_allow_request(self) -> bool:
        """Determine if a request should be allowed through"""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self._last_failure_time:
                    elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                    if elapsed >= self.recovery_timeout:
                        await self._transition_to(CircuitState.HALF_OPEN)
                        return True
                return False
            
            if self._state == CircuitState.HALF_OPEN:
                # Allow limited calls in half-open state
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            
            return False
    
    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state"""
        old_state = self._state
        self._state = new_state
        self._stats["state_changes"] += 1
        
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        
        logger.info(
            f"Circuit breaker '{self.name}' state change: {old_state.value} -> {new_state.value}"
        )
    
    async def _record_success(self) -> None:
        """Record a successful call"""
        async with self._lock:
            self._stats["successful_calls"] += 1
            self._success_count += 1
            
            if self._state == CircuitState.HALF_OPEN:
                # If enough successes in half-open, close the circuit
                if self._success_count >= self.half_open_max_calls:
                    await self._transition_to(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0
    
    async def _record_failure(self, exception: Exception) -> None:
        """Record a failed call"""
        async with self._lock:
            self._stats["failed_calls"] += 1
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            
            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens the circuit
                await self._transition_to(CircuitState.OPEN)
                logger.warning(
                    f"Circuit breaker '{self.name}' reopened after failure in half-open state"
                )
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)
                    logger.warning(
                        f"Circuit breaker '{self.name}' opened after {self._failure_count} failures"
                    )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result of the function
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Original exception: If function fails
        """
        from .exceptions import CircuitBreakerOpenError
        
        self._stats["total_calls"] += 1
        
        # Check if request should be allowed
        if not await self._should_allow_request():
            self._stats["rejected_calls"] += 1
            
            retry_after = self.recovery_timeout
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                retry_after = max(0, int(self.recovery_timeout - elapsed))
            
            logger.debug(f"Circuit breaker '{self.name}' rejected request (retry after {retry_after}s)")
            
            raise CircuitBreakerOpenError(
                service_name=self.name,
                retry_after_seconds=retry_after,
                failure_count=self._failure_count
            )
        
        # Execute the function
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except self.excluded_exceptions:
            # These exceptions don't count as failures
            raise
        except Exception as e:
            await self._record_failure(e)
            raise
    
    def protected(self, func: Callable) -> Callable:
        """
        Decorator to protect an async function with this circuit breaker.
        
        Usage:
            @breaker.protected
            async def my_function():
                ...
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    async def reset(self) -> None:
        """Manually reset the circuit breaker to closed state"""
        async with self._lock:
            await self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    Provides centralized access and monitoring.
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    def register(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        **kwargs
    ) -> CircuitBreaker:
        """Register a new circuit breaker"""
        if name in self._breakers:
            return self._breakers[name]
        
        breaker = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            **kwargs
        )
        self._breakers[name] = breaker
        return breaker
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name"""
        return self._breakers.get(name)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}
    
    def get_all_states(self) -> Dict[str, str]:
        """Get states of all circuit breakers"""
        return {name: breaker.state.value for name, breaker in self._breakers.items()}
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            await breaker.reset()


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()

# Pre-configured circuit breakers for common services
ratemyprof_breaker = circuit_breaker_registry.register(
    "ratemyprof",
    failure_threshold=5,
    recovery_timeout=60,
    half_open_max_calls=2
)

cuny_scraper_breaker = circuit_breaker_registry.register(
    "cuny_scraper",
    failure_threshold=5,
    recovery_timeout=60,
    half_open_max_calls=2
)

supabase_breaker = circuit_breaker_registry.register(
    "supabase",
    failure_threshold=10,
    recovery_timeout=30,
    half_open_max_calls=3
)

gemini_breaker = circuit_breaker_registry.register(
    "gemini",
    failure_threshold=5,
    recovery_timeout=120,
    half_open_max_calls=2
)


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitState",
    "circuit_breaker_registry",
    "ratemyprof_breaker",
    "cuny_scraper_breaker",
    "supabase_breaker",
    "gemini_breaker",
]
