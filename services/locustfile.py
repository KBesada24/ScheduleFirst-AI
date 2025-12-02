"""
Locust load testing configuration for ScheduleFirst-AI backend
Performance targets:
- Cached queries: <100ms P95 response time
- Fresh data queries: <10s P95 response time  
- Concurrent load: 100 users at 1000 requests/min
"""
import os
import json
import random
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

# Test configuration
API_HOST = os.getenv("API_HOST", "http://localhost:8000")
MCP_HOST = os.getenv("MCP_HOST", "http://localhost:3000")

# Sample test data
SEMESTERS = ["Fall 2025", "Spring 2025", "Fall 2024", "Spring 2024"]
UNIVERSITIES = ["Baruch College", "Hunter College", "Brooklyn College", "Queens College"]
COURSE_CODES = [
    "CSC101", "CSC211", "CSC326", "CSC330", "CSC332",
    "MTH201", "MTH202", "MTH301", "MTH311",
    "ACC101", "ACC201", "FIN301", "MKT101",
]
PROFESSOR_NAMES = [
    "Dr. Smith", "Dr. Johnson", "Dr. Williams", "Dr. Brown",
    "Dr. Jones", "Dr. Davis", "Dr. Miller", "Dr. Wilson",
]

# Time slots for conflict checking
TIME_SLOTS = [
    {"start": "09:00", "end": "10:15", "days": ["Monday", "Wednesday"]},
    {"start": "10:30", "end": "11:45", "days": ["Monday", "Wednesday"]},
    {"start": "12:00", "end": "13:15", "days": ["Tuesday", "Thursday"]},
    {"start": "14:00", "end": "15:15", "days": ["Tuesday", "Thursday"]},
]


class ScheduleFirstUser(HttpUser):
    """
    Simulates a typical user interacting with ScheduleFirst-AI
    Mix of cached and fresh data requests
    """
    
    # Wait 1-3 seconds between tasks
    wait_time = between(1, 3)
    
    # Default host
    host = API_HOST
    
    def on_start(self):
        """Setup before running tasks"""
        # Track which requests hit cache vs fresh data
        self.cache_hits = 0
        self.cache_misses = 0
        self.semester = random.choice(SEMESTERS)
        self.university = random.choice(UNIVERSITIES)
    
    # HIGH FREQUENCY TASKS - Should hit cache (<100ms P95)
    
    @task(10)  # Highest weight - most common operation
    def fetch_cached_sections(self):
        """
        Fetch course sections - should hit cache on repeated requests
        Target: <100ms P95 response time
        """
        course_code = random.choice(COURSE_CODES)
        
        with self.client.post(
            "/api/v1/mcp/tools/fetch_course_sections",
            json={
                "course_codes": [course_code],
                "semester": self.semester,
                "university": self.university,
            },
            name="fetch_sections (cached)",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("from_cache"):
                        self.cache_hits += 1
                        response.success()
                    else:
                        self.cache_misses += 1
                        response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(8)
    def get_cached_professor_grade(self):
        """
        Get professor grade - should hit cache on repeated requests
        Target: <100ms P95 response time
        """
        professor = random.choice(PROFESSOR_NAMES)
        
        with self.client.post(
            "/api/v1/mcp/tools/get_professor_grade",
            json={
                "professor_name": professor,
                "university": self.university,
            },
            name="get_professor_grade (cached)",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(5)
    def check_schedule_conflicts(self):
        """
        Check for time conflicts - pure computation, no DB
        Target: <100ms P95 response time
        """
        selected_slots = random.sample(TIME_SLOTS, k=min(3, len(TIME_SLOTS)))
        
        with self.client.post(
            "/api/v1/mcp/tools/check_schedule_conflicts",
            json={
                "sections": selected_slots,
            },
            name="check_conflicts",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    # ============================================================
    # MEDIUM FREQUENCY TASKS - May trigger refresh
    # ============================================================
    
    @task(3)
    def compare_professors(self):
        """
        Compare multiple professors
        Target: <2s P95 if cached, <10s if refresh needed
        """
        profs = random.sample(PROFESSOR_NAMES, k=min(3, len(PROFESSOR_NAMES)))
        
        with self.client.post(
            "/api/v1/mcp/tools/compare_professors",
            json={
                "professor_names": profs,
                "university": self.university,
            },
            name="compare_professors",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 504:
                response.failure("Timeout - acceptable for fresh data")
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def generate_schedule(self):
        """
        Generate optimized schedule - complex computation
        Target: <5s P95 response time
        """
        courses = random.sample(COURSE_CODES, k=min(4, len(COURSE_CODES)))
        
        with self.client.post(
            "/api/v1/mcp/tools/generate_optimized_schedule",
            json={
                "course_codes": courses,
                "semester": self.semester,
                "university": self.university,
                "preferences": {
                    "avoid_early_morning": random.choice([True, False]),
                    "prefer_back_to_back": random.choice([True, False]),
                    "max_classes_per_day": random.randint(2, 4),
                }
            },
            name="generate_schedule",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 504:
                response.failure("Timeout - needs optimization")
            else:
                response.failure(f"Status {response.status_code}")
    
    # ============================================================
    # LOW FREQUENCY TASKS - Force refresh (<10s P95)
    # ============================================================
    
    @task(1)
    def fetch_fresh_sections(self):
        """
        Force refresh of course sections
        Target: <10s P95 response time
        """
        course_code = random.choice(COURSE_CODES)
        
        with self.client.post(
            "/api/v1/mcp/tools/fetch_course_sections",
            json={
                "course_codes": [course_code],
                "semester": self.semester,
                "university": self.university,
                "force_refresh": True,
            },
            name="fetch_sections (fresh)",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 504:
                response.failure("Timeout - but acceptable for fresh data")
            else:
                response.failure(f"Status {response.status_code}")


class HighLoadUser(HttpUser):
    """
    Simulates burst traffic for stress testing
    Mostly cached requests with occasional fresh data
    """
    
    # Faster requests for load testing
    wait_time = between(0.5, 1)
    host = API_HOST
    
    @task(20)
    def rapid_section_lookup(self):
        """Rapid fire section lookups - should all hit cache"""
        course_code = random.choice(COURSE_CODES)
        
        self.client.post(
            "/api/v1/mcp/tools/fetch_course_sections",
            json={
                "course_codes": [course_code],
                "semester": "Fall 2025",
                "university": "Baruch College",
            },
            name="rapid_lookup",
        )
    
    @task(5)
    def rapid_professor_lookup(self):
        """Rapid professor grade lookups"""
        professor = random.choice(PROFESSOR_NAMES)
        
        self.client.post(
            "/api/v1/mcp/tools/get_professor_grade",
            json={
                "professor_name": professor,
                "university": "Baruch College",
            },
            name="rapid_professor",
        )


class APIHealthUser(HttpUser):
    """
    Monitors API health endpoints
    """
    
    wait_time = between(5, 10)
    host = API_HOST
    
    @task
    def health_check(self):
        """Check API health endpoint"""
        self.client.get("/health", name="health_check")
    
    @task
    def readiness_check(self):
        """Check API readiness"""
        self.client.get("/ready", name="readiness_check")


# ============================================================
# Event hooks for custom metrics
# ============================================================

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics"""
    if isinstance(environment.runner, MasterRunner):
        print("Initializing master runner")


@events.request.add_listener
def on_request(
    request_type, name, response_time, response_length, exception, **kwargs
):
    """Track custom metrics per request"""
    # Log slow requests for analysis
    if response_time > 10000:  # > 10 seconds
        print(f"SLOW REQUEST: {name} took {response_time}ms")
    
    # Log cache performance (would need to parse response)
    pass


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print final statistics"""
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST COMPLETED")
    print("=" * 60)
    
    stats = environment.stats
    
    # Print summary by endpoint
    print("\nEndpoint Performance Summary:")
    print("-" * 60)
    
    for entry in stats.entries.values():
        if entry.num_requests > 0:
            print(f"\n{entry.name}:")
            print(f"  Requests: {entry.num_requests}")
            print(f"  Failures: {entry.num_failures}")
            print(f"  Avg Time: {entry.avg_response_time:.0f}ms")
            print(f"  P95 Time: {entry.get_response_time_percentile(0.95):.0f}ms")
            print(f"  P99 Time: {entry.get_response_time_percentile(0.99):.0f}ms")
    
    # Performance targets check
    print("\n" + "=" * 60)
    print("PERFORMANCE TARGETS CHECK")
    print("=" * 60)
    
    cached_endpoints = ["fetch_sections (cached)", "get_professor_grade (cached)", 
                        "check_conflicts", "rapid_lookup", "rapid_professor"]
    
    fresh_endpoints = ["fetch_sections (fresh)", "compare_professors", 
                       "generate_schedule"]
    
    all_passed = True
    
    for name, entry in stats.entries.items():
        if entry.num_requests == 0:
            continue
            
        p95 = entry.get_response_time_percentile(0.95)
        
        if name in cached_endpoints:
            target = 100  # 100ms
            passed = p95 <= target
        elif name in fresh_endpoints:
            target = 10000  # 10s
            passed = p95 <= target
        else:
            continue
        
        status = "✓ PASS" if passed else "✗ FAIL"
        all_passed = all_passed and passed
        print(f"{status}: {name} - P95: {p95:.0f}ms (target: {target}ms)")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL PERFORMANCE TARGETS MET ✓")
    else:
        print("SOME PERFORMANCE TARGETS FAILED ✗")
    print("=" * 60)


# ============================================================
# CLI usage examples
# ============================================================
"""
Basic usage:
    locust -f locustfile.py --host http://localhost:8000

Run with web UI:
    locust -f locustfile.py --host http://localhost:8000 --web-port 8089

Headless mode (CI/CD):
    locust -f locustfile.py --host http://localhost:8000 \
           --headless -u 100 -r 10 --run-time 5m

Specific user class:
    locust -f locustfile.py --host http://localhost:8000 \
           HighLoadUser -u 50 -r 5 --run-time 2m

Target performance test:
    # Test cached query performance (100 concurrent users)
    locust -f locustfile.py --host http://localhost:8000 \
           ScheduleFirstUser -u 100 -r 20 --run-time 10m \
           --csv=performance_results

Generate HTML report:
    locust -f locustfile.py --host http://localhost:8000 \
           --headless -u 100 -r 10 --run-time 5m \
           --html=performance_report.html
"""
