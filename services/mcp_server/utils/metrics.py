"""
Centralized metrics collection for monitoring and alerting.
Tracks API requests, cache operations, job executions, and errors.
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict
from dataclasses import dataclass, field
import asyncio
import threading

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class TimingStats:
    """Statistics for timing measurements"""
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float('inf')
    max_ms: float = 0.0
    
    def record(self, duration_ms: float) -> None:
        self.count += 1
        self.total_ms += duration_ms
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)
    
    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "total_ms": round(self.total_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
            "min_ms": round(self.min_ms, 2) if self.min_ms != float('inf') else 0,
            "max_ms": round(self.max_ms, 2),
        }


@dataclass
class RequestMetrics:
    """Metrics for a single endpoint"""
    success_count: int = 0
    error_count: int = 0
    timing: TimingStats = field(default_factory=TimingStats)
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    def record_request(self, status_code: int, duration_ms: float) -> None:
        if 200 <= status_code < 400:
            self.success_count += 1
        else:
            self.error_count += 1
        self.status_codes[status_code] += 1
        self.timing.record(duration_ms)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success_count": self.success_count,
            "error_count": self.error_count,
            "error_rate": round(self.error_count / (self.success_count + self.error_count) * 100, 2) 
                if (self.success_count + self.error_count) > 0 else 0,
            "timing": self.timing.to_dict(),
            "status_codes": dict(self.status_codes),
        }


@dataclass
class JobMetrics:
    """Metrics for background jobs"""
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_duration_ms: float = 0.0
    timing: TimingStats = field(default_factory=TimingStats)
    
    def record_execution(self, success: bool, duration_ms: float) -> None:
        self.run_count += 1
        self.last_run = datetime.utcnow()
        self.last_duration_ms = duration_ms
        self.timing.record(duration_ms)
        
        if success:
            self.success_count += 1
            self.last_success = datetime.utcnow()
        else:
            self.failure_count += 1
            self.last_failure = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_count / self.run_count * 100, 2) if self.run_count > 0 else 0,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_duration_ms": round(self.last_duration_ms, 2),
            "timing": self.timing.to_dict(),
        }


class MetricsCollector:
    """
    Centralized metrics collection.
    Thread-safe singleton for tracking application metrics.
    """
    
    _instance: Optional['MetricsCollector'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'MetricsCollector':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._metrics_lock: Optional[asyncio.Lock] = None
        
        # API request metrics by endpoint
        self._request_metrics: Dict[str, RequestMetrics] = defaultdict(RequestMetrics)
        
        # Background job metrics by job name
        self._job_metrics: Dict[str, JobMetrics] = defaultdict(JobMetrics)
        
        # Error tracking
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._recent_errors: List[Dict[str, Any]] = []
        self._max_recent_errors = 100
        
        # Query timing
        self._query_metrics: Dict[str, TimingStats] = defaultdict(TimingStats)
        
        # Scraping metrics
        self._scraping_metrics: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})
        
        # Usage analytics
        self._course_requests: Dict[str, int] = defaultdict(int)
        self._semester_requests: Dict[str, int] = defaultdict(int)
        self._hourly_requests: Dict[int, int] = defaultdict(int)
        
        # Start time for uptime calculation
        self._start_time = datetime.utcnow()
        
        # Cache stats (updated externally)
        self._cache_stats: Dict[str, Any] = {}
        
        # Alert thresholds
        self._thresholds = {
            "cache_hit_rate_min": 50.0,  # Warn if below 50%
            "error_rate_max": 10.0,  # Warn if above 10%
            "response_time_max_ms": 2000.0,  # Warn if avg above 2s
            "slow_query_threshold_ms": 500.0,  # Log queries above this
        }
        
        logger.info("MetricsCollector initialized")
    
    def _get_lock(self) -> asyncio.Lock:
        """Lazily initialize and return the asyncio lock"""
        if self._metrics_lock is None:
            self._metrics_lock = asyncio.Lock()
        return self._metrics_lock
    
    async def record_request(
        self, 
        endpoint: str, 
        method: str,
        status_code: int, 
        duration_ms: float
    ) -> None:
        """Record an API request"""
        key = f"{method} {endpoint}"
        async with self._get_lock():
            self._request_metrics[key].record_request(status_code, duration_ms)
            
            # Track hourly distribution
            hour = datetime.utcnow().hour
            self._hourly_requests[hour] += 1
        
        # Log slow requests
        if duration_ms > self._thresholds["response_time_max_ms"]:
            logger.warning(
                f"Slow request: {key} took {duration_ms:.2f}ms",
                extra={"endpoint": endpoint, "duration_ms": duration_ms}
            )
    
    async def record_job_execution(
        self, 
        job_name: str, 
        success: bool, 
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a background job execution"""
        async with self._get_lock():
            self._job_metrics[job_name].record_execution(success, duration_ms)
        
        log_msg = f"Job '{job_name}' {'succeeded' if success else 'failed'} in {duration_ms:.2f}ms"
        if success:
            logger.info(log_msg, extra={"job_name": job_name, "duration_ms": duration_ms, **(details or {})})
        else:
            logger.error(log_msg, extra={"job_name": job_name, "duration_ms": duration_ms, **(details or {})})
    
    async def record_error(
        self, 
        error_type: str, 
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record an error occurrence"""
        async with self._get_lock():
            self._error_counts[error_type] += 1
            
            error_record = {
                "type": error_type,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "context": context or {},
            }
            self._recent_errors.append(error_record)
            
            # Keep only recent errors
            if len(self._recent_errors) > self._max_recent_errors:
                self._recent_errors = self._recent_errors[-self._max_recent_errors:]
    
    async def record_query(
        self, 
        query_name: str, 
        duration_ms: float
    ) -> None:
        """Record a database query execution"""
        async with self._get_lock():
            self._query_metrics[query_name].record(duration_ms)
        
        # Log slow queries
        if duration_ms > self._thresholds["slow_query_threshold_ms"]:
            logger.warning(
                f"Slow query: {query_name} took {duration_ms:.2f}ms",
                extra={"query_name": query_name, "duration_ms": duration_ms}
            )
    
    async def record_scraping(
        self, 
        scraper_type: str, 
        success: bool
    ) -> None:
        """Record a scraping operation"""
        async with self._get_lock():
            key = "success" if success else "failure"
            self._scraping_metrics[scraper_type][key] += 1
    
    async def record_course_request(self, course_code: str, semester: str) -> None:
        """Track course usage for analytics"""
        async with self._get_lock():
            self._course_requests[course_code] += 1
            self._semester_requests[semester] += 1
    
    def update_cache_stats(self, cache_stats: Dict[str, Any]) -> None:
        """Update cache statistics (called from CacheManager)"""
        # This is a sync method since cache stats are updated frequently
        self._cache_stats = cache_stats
    
    async def check_thresholds(self, cache_stats: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Check metrics against thresholds and return alerts"""
        alerts = []
        
        # Check cache hit rate
        if cache_stats:
            hits = cache_stats.get("hits", 0)
            misses = cache_stats.get("misses", 0)
            total = hits + misses
            if total > 100:  # Only check if we have enough data
                hit_rate = (hits / total) * 100
                if hit_rate < self._thresholds["cache_hit_rate_min"]:
                    alert = {
                        "type": "low_cache_hit_rate",
                        "severity": "warning",
                        "message": f"Cache hit rate is {hit_rate:.1f}% (threshold: {self._thresholds['cache_hit_rate_min']}%)",
                        "value": hit_rate,
                        "threshold": self._thresholds["cache_hit_rate_min"],
                    }
                    alerts.append(alert)
                    logger.warning(alert["message"])
        
        # Check overall error rate
        async with self._get_lock():
            total_success = sum(m.success_count for m in self._request_metrics.values())
            total_errors = sum(m.error_count for m in self._request_metrics.values())
            total_requests = total_success + total_errors
            
            if total_requests > 100:
                error_rate = (total_errors / total_requests) * 100
                if error_rate > self._thresholds["error_rate_max"]:
                    alert = {
                        "type": "high_error_rate",
                        "severity": "error",
                        "message": f"Error rate is {error_rate:.1f}% (threshold: {self._thresholds['error_rate_max']}%)",
                        "value": error_rate,
                        "threshold": self._thresholds["error_rate_max"],
                    }
                    alerts.append(alert)
                    logger.error(alert["message"])
            
            # Check average response time
            total_time = sum(m.timing.total_ms for m in self._request_metrics.values())
            total_count = sum(m.timing.count for m in self._request_metrics.values())
            
            if total_count > 100:
                avg_time = total_time / total_count
                if avg_time > self._thresholds["response_time_max_ms"]:
                    alert = {
                        "type": "slow_response_time",
                        "severity": "warning",
                        "message": f"Average response time is {avg_time:.1f}ms (threshold: {self._thresholds['response_time_max_ms']}ms)",
                        "value": avg_time,
                        "threshold": self._thresholds["response_time_max_ms"],
                    }
                    alerts.append(alert)
                    logger.warning(alert["message"])
        
        return alerts
    
    async def get_all_metrics(self, cache_stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get all collected metrics"""
        async with self._get_lock():
            uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()
            
            # Calculate totals
            total_requests = sum(m.timing.count for m in self._request_metrics.values())
            total_errors = sum(m.error_count for m in self._request_metrics.values())
            
            return {
                "uptime_seconds": round(uptime_seconds, 2),
                "uptime_human": str(timedelta(seconds=int(uptime_seconds))),
                "collected_at": datetime.utcnow().isoformat(),
                
                "requests": {
                    "total": total_requests,
                    "total_errors": total_errors,
                    "error_rate": round(total_errors / total_requests * 100, 2) if total_requests > 0 else 0,
                    "by_endpoint": {k: v.to_dict() for k, v in self._request_metrics.items()},
                },
                
                "jobs": {k: v.to_dict() for k, v in self._job_metrics.items()},
                
                "errors": {
                    "counts_by_type": dict(self._error_counts),
                    "recent_count": len(self._recent_errors),
                },
                
                "queries": {k: v.to_dict() for k, v in self._query_metrics.items()},
                
                "scraping": {k: dict(v) for k, v in self._scraping_metrics.items()},
                
                "cache": cache_stats or {},
                
                "usage": {
                    "top_courses": dict(sorted(
                        self._course_requests.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:10]),
                    "top_semesters": dict(sorted(
                        self._semester_requests.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:5]),
                    "hourly_distribution": dict(self._hourly_requests),
                },
                
                "thresholds": self._thresholds,
            }
    
    async def get_health_summary(self, cache_stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get a health summary for quick status checks"""
        alerts = await self.check_thresholds(cache_stats)
        
        async with self._get_lock():
            total_requests = sum(m.timing.count for m in self._request_metrics.values())
            total_errors = sum(m.error_count for m in self._request_metrics.values())
            
            # Calculate average response time
            total_time = sum(m.timing.total_ms for m in self._request_metrics.values())
            total_count = sum(m.timing.count for m in self._request_metrics.values())
            avg_response_time = total_time / total_count if total_count > 0 else 0
            
            # Determine overall status
            if any(a["severity"] == "error" for a in alerts):
                status = "unhealthy"
            elif alerts:
                status = "degraded"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds(),
                "total_requests": total_requests,
                "error_rate": round(total_errors / total_requests * 100, 2) if total_requests > 0 else 0,
                "avg_response_time_ms": round(avg_response_time, 2),
                "active_alerts": len(alerts),
                "alerts": alerts,
            }
    
    async def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)"""
        async with self._get_lock():
            self._request_metrics.clear()
            self._job_metrics.clear()
            self._error_counts.clear()
            self._recent_errors.clear()
            self._query_metrics.clear()
            self._scraping_metrics.clear()
            self._course_requests.clear()
            self._semester_requests.clear()
            self._hourly_requests.clear()
            self._start_time = datetime.utcnow()
        
        logger.info("Metrics reset")


# Singleton instance
metrics_collector = MetricsCollector()


# Timing context manager for easy instrumentation
class Timer:
    """Context manager for timing operations"""
    
    def __init__(self):
        self.start_time: float = 0
        self.duration_ms: float = 0
    
    def __enter__(self) -> 'Timer':
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args) -> None:
        self.duration_ms = (time.perf_counter() - self.start_time) * 1000


from functools import wraps

def record_query_timing(query_name: str):
    """Decorator for timing database queries"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            timer = Timer()
            with timer:
                result = await func(*args, **kwargs)
            await metrics_collector.record_query(query_name, timer.duration_ms)
            return result
        return wrapper
    return decorator
