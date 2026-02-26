"""
REST API Server for CUNY Schedule Optimizer
Serves the React frontend with schedule optimization endpoints
"""
import time
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
import uvicorn

from mcp_server.config import settings
from mcp_server.services.supabase_service import supabase_service
from mcp_server.services.constraint_solver import schedule_optimizer
from mcp_server.services.sentiment_analyzer import sentiment_analyzer
from mcp_server.utils.logger import get_logger
from mcp_server.utils.metrics import metrics_collector
from mcp_server.utils.cache import cache_manager
from mcp_server.utils.exceptions import (
    ScheduleOptimizerError,
    DataNotFoundError,
    DataStaleError,
    DatabaseError,
    CircuitBreakerOpenError,
    RateLimitError,
    ValidationError,
    ScrapingError,
    ExternalServiceError,
)
from mcp_server.models.schedule import ScheduleConstraints, OptimizedSchedule
from mcp_server.models.course import CourseSearchFilter
from mcp_server.models.api_models import ApiResponse, ResponseMetadata, ErrorResponse, DataQuality
from mcp_server.services.data_population_service import data_population_service
from mcp_server.services.data_freshness_service import data_freshness_service
from mcp_server.tools.schedule_optimizer import compare_professors
from mcp_server.utils.circuit_breaker import circuit_breaker_registry
from mcp_server.utils.tool_result_logging import format_tool_result_for_log

logger = get_logger(__name__)

# Security for admin endpoints
security = HTTPBearer(auto_error=False)


async def verify_admin_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> HTTPAuthorizationCredentials:
    """Verify admin API token for protected endpoints"""
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=503,
            detail="Admin API key not configured. Set ADMIN_API_KEY environment variable."
        )
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.credentials != settings.admin_api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin credentials"
        )
    
    return credentials


class ScheduleOptimizeRequest(BaseModel):
    course_codes: List[str]
    semester: str
    university: str
    constraints: ScheduleConstraints


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track request metrics"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Get endpoint path (normalize to avoid high cardinality)
        path = request.url.path
        # Normalize paths with IDs
        for param in ["professor_name", "name", "id"]:
            if f"{{{param}}}" not in path and "/" in path:
                parts = path.split("/")
                # Simple normalization: replace likely ID segments
                normalized_parts = []
                for i, part in enumerate(parts):
                    if i > 0 and parts[i-1] in ["professor", "course", "section", "schedule"]:
                        normalized_parts.append(f"{{{parts[i-1]}_id}}")
                    else:
                        normalized_parts.append(part)
                path = "/".join(normalized_parts)
        
        # Record metrics
        await metrics_collector.record_request(
            endpoint=path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        # Add timing header
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("=" * 60)
    logger.info("CUNY Schedule Optimizer API Server")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"API Host: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"Ollama API: {'✓ Configured' if settings.ollama_api_key else '✗ Not configured (local)'}")
    logger.info(f"Sentry: {'✓ Configured' if settings.sentry_dsn else '✗ Not configured'}")
    logger.info("=" * 60)
    
    # Health check
    logger.info("Performing database health check...")
    try:
        is_healthy = await supabase_service.health_check()
        if is_healthy:
            logger.info("✅ Database connected")
        else:
            logger.warning("⚠️ Database connection failed")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
    
    # Cache warming
    logger.info("Warming cache...")
    try:
        warm_result = await cache_manager.warm_cache()
        logger.info(f"Cache warming: {warm_result.get('status', 'unknown')}")
    except Exception as e:
        logger.warning(f"Cache warming failed: {e}")
    
    logger.info("=" * 60)
    logger.info("API Server ready!")
    logger.info("Available endpoints:")
    logger.info("  GET  /health")
    logger.info("  GET  /health/metrics")
    logger.info("  GET  /health/cache")
    logger.info("  GET  /api/courses")
    logger.info("  POST /api/schedule/optimize")
    logger.info("  GET  /api/professor/{name}")
    logger.info("  POST /api/professor/compare")
    logger.info("  POST /api/admin/sync")
    logger.info("  POST /api/feedback")
    logger.info("=" * 60)
    
    yield
    
    logger.info("Shutting down API server...")


app = FastAPI(
    title="CUNY Schedule Optimizer API",
    description="AI-powered schedule optimization for CUNY students",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================
# GLOBAL EXCEPTION HANDLERS
# ============================================

@app.exception_handler(DataNotFoundError)
async def data_not_found_handler(request: Request, exc: DataNotFoundError):
    """Handle 404 Not Found errors"""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse.from_exception(exc).model_dump(),
        headers={"X-Error-Code": exc.code},
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle 400 Validation errors"""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse.from_exception(exc).model_dump(),
        headers={"X-Error-Code": exc.code},
    )


@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError):
    """Handle 429 Rate Limit errors"""
    headers = {"X-Error-Code": exc.code}
    if exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    
    return JSONResponse(
        status_code=429,
        content=ErrorResponse.from_exception(exc).model_dump(),
        headers=headers,
    )


@app.exception_handler(CircuitBreakerOpenError)
async def circuit_breaker_handler(request: Request, exc: CircuitBreakerOpenError):
    """Handle 503 Circuit Breaker Open errors"""
    return JSONResponse(
        status_code=503,
        content=ErrorResponse.from_exception(exc).model_dump(),
        headers={
            "X-Error-Code": exc.code,
            "Retry-After": str(exc.retry_after_seconds),
        },
    )


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle 503 Database errors"""
    status_code = 503 if exc.is_retryable else 500
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse.from_exception(exc).model_dump(),
        headers={"X-Error-Code": exc.code},
    )


@app.exception_handler(ScrapingError)
async def scraping_error_handler(request: Request, exc: ScrapingError):
    """Handle 502 Scraping errors (external service issues)"""
    return JSONResponse(
        status_code=502,
        content=ErrorResponse.from_exception(exc).model_dump(),
        headers={"X-Error-Code": exc.code},
    )


@app.exception_handler(ExternalServiceError)
async def external_service_handler(request: Request, exc: ExternalServiceError):
    """Handle 502 External Service errors"""
    return JSONResponse(
        status_code=502,
        content=ErrorResponse.from_exception(exc).model_dump(),
        headers={"X-Error-Code": exc.code},
    )


@app.exception_handler(ScheduleOptimizerError)
async def schedule_optimizer_error_handler(request: Request, exc: ScheduleOptimizerError):
    """Catch-all handler for any ScheduleOptimizerError subclass not specifically handled"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse.from_exception(exc).model_dump(),
        headers={"X-Error-Code": exc.code},
    )

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative React port
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "CUNY Schedule Optimizer API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint with circuit breaker status"""
    try:
        db_healthy = await supabase_service.health_check()
        
        # Get circuit breaker states
        breaker_states = circuit_breaker_registry.get_all_states()
        
        # Get metrics health summary
        cache_stats = cache_manager.get_stats()
        health_summary = await metrics_collector.get_health_summary(cache_stats)
        
        # Determine overall status
        any_circuit_open = any(state == "open" for state in breaker_states.values())
        
        if not db_healthy:
            status = "unhealthy"
        elif any_circuit_open or health_summary.get("status") == "degraded":
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "database": "connected" if db_healthy else "disconnected",
            "environment": settings.environment,
            "ollama_api": "configured" if settings.ollama_api_key else "not configured",
            "sentry": "configured" if settings.sentry_dsn else "not configured",
            "circuit_breakers": breaker_states,
            "metrics_summary": {
                "uptime_seconds": health_summary.get("uptime_seconds"),
                "total_requests": health_summary.get("total_requests"),
                "error_rate": health_summary.get("error_rate"),
                "avg_response_time_ms": health_summary.get("avg_response_time_ms"),
                "active_alerts": health_summary.get("active_alerts"),
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/health/metrics")
async def health_metrics():
    """Detailed metrics endpoint for monitoring"""
    try:
        cache_stats = cache_manager.get_stats()
        metrics = await metrics_collector.get_all_metrics(cache_stats)
        return metrics
    except Exception as e:
        logger.error(f"Metrics fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health/cache")
async def health_cache():
    """Cache statistics endpoint"""
    try:
        stats = cache_manager.get_stats()
        return {
            "status": "healthy",
            "statistics": stats,
            "config": {
                "default_ttl": settings.cache_ttl,
                "max_size": settings.cache_max_size,
                "ttl_courses": settings.cache_ttl_courses,
                "ttl_professors": settings.cache_ttl_professors,
                "ttl_reviews": settings.cache_ttl_reviews,
                "ttl_schedules": settings.cache_ttl_schedules,
            }
        }
    except Exception as e:
        logger.error(f"Cache stats fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health/jobs")
async def health_jobs():
    """Background job status endpoint"""
    try:
        cache_stats = cache_manager.get_stats()
        metrics = await metrics_collector.get_all_metrics(cache_stats)
        return {
            "status": "healthy",
            "jobs": metrics.get("jobs", {}),
            "scraping": metrics.get("scraping", {}),
        }
    except Exception as e:
        logger.error(f"Job stats fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses", response_model=ApiResponse)
async def get_courses(
    semester: str,
    university: str = "Baruch College",
    auto_populate: bool = True
):
    """Get all courses for a semester"""
    try:
        # Auto-populate if requested
        was_populated = False
        if auto_populate:
            population_result = await data_population_service.ensure_course_data(semester, university)
            was_populated = population_result.success
        
        courses = await supabase_service.get_courses_by_semester(semester, university)
        
        # Determine freshness
        is_fresh = await data_freshness_service.is_course_data_fresh(semester, university)
        last_sync = await data_freshness_service.get_last_sync("courses", semester, university)
        
        return ApiResponse(
            data={
                "courses": [course.model_dump() for course in courses],
                "count": len(courses)
            },
            metadata=ResponseMetadata(
                source="hybrid",
                last_updated=last_sync,
                is_fresh=is_fresh,
                auto_populated=was_populated,
                count=len(courses)
            )
        )
    except Exception as e:
        logger.error(f"Error fetching courses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/courses/search", response_model=ApiResponse)
async def search_courses(
    filters: CourseSearchFilter,
    auto_populate: bool = True
):
    """Search courses with filters"""
    try:
        # Auto-populate if filters provide enough context
        was_populated = False
        if auto_populate and filters.semester and filters.university:
            population_result = await data_population_service.ensure_course_data(
                filters.semester, 
                filters.university
            )
            was_populated = population_result.success
            
        courses = await supabase_service.search_courses(filters)
        
        # Determine freshness (best effort)
        is_fresh = True
        last_sync = None
        if filters.semester and filters.university:
            is_fresh = await data_freshness_service.is_course_data_fresh(
                filters.semester, 
                filters.university
            )
            last_sync = await data_freshness_service.get_last_sync(
                "courses", 
                filters.semester, 
                filters.university
            )
            
        return ApiResponse(
            data={
                "courses": [course.model_dump() for course in courses],
                "count": len(courses)
            },
            metadata=ResponseMetadata(
                source="hybrid",
                last_updated=last_sync,
                is_fresh=is_fresh,
                auto_populated=was_populated,
                count=len(courses)
            )
        )
    except Exception as e:
        logger.error(f"Error searching courses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/schedule/optimize")
async def optimize_schedule(request: ScheduleOptimizeRequest):
    """Generate optimized schedule"""
    try:
        all_sections = []
        course_map = {}  # Track which courses were found
        
        for course_code in request.course_codes:
            # Get course by code
            course = await supabase_service.get_course_by_code(
                course_code=course_code,
                semester=request.semester,
                university=request.university
            )
            
            if not course:
                logger.warning(f"Course not found: {course_code}")
                continue
            
            # Store course info for response
            course_map[course_code] = {
                "id": course.id,
                "name": course.name
            }
            
            # Fetch sections
            sections = await supabase_service.get_sections_by_course(course.id)
            all_sections.extend(sections)
            
            logger.info(f"Found {len(sections)} sections for {course_code}")
        
        if not all_sections:
            raise HTTPException(
                status_code=404,
                detail=f"No sections found for courses: {', '.join(request.course_codes)}"
            )
        
        # Generate optimized schedules
        schedules = await schedule_optimizer.generate_optimized_schedules(
            required_courses=request.course_codes,
            semester=request.semester,
            university=request.university,
            constraints=request.constraints
        )
        
        return {
            "schedules": [schedule.model_dump() for schedule in schedules],
            "count": len(schedules),
            "courses": course_map,
            "total_sections": len(all_sections)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/professor/{professor_name}", response_model=ApiResponse)
async def get_professor(
    professor_name: str,
    university: str = "Baruch College",
    auto_populate: bool = True
):
    """Get professor information and grades"""
    try:
        # Auto-populate if requested
        was_populated = False
        if auto_populate:
            population_result = await data_population_service.ensure_professor_data(
                professor_name, 
                university
            )
            was_populated = population_result.success
            
        professor = await supabase_service.get_professor_by_name(professor_name, university)
        
        if not professor:
            raise HTTPException(status_code=404, detail="Professor not found")
        
        # Get reviews
        reviews = await supabase_service.get_reviews_by_professor(professor.id)
        
        # Determine freshness
        is_fresh = await data_freshness_service.is_professor_data_fresh(professor.id)
        
        return ApiResponse(
            data={
                "professor": professor.model_dump(),
                "reviews": [review.model_dump() for review in reviews],
                "review_count": len(reviews)
            },
            metadata=ResponseMetadata(
                source="hybrid",
                last_updated=professor.last_updated,
                is_fresh=is_fresh,
                auto_populated=was_populated,
                count=1
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching professor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ProfessorComparisonRequest(BaseModel):
    professor_names: List[str]
    university: str
    course_code: Optional[str] = None


@app.post("/api/professor/compare", response_model=ApiResponse)
async def compare_professors_endpoint(request: ProfessorComparisonRequest):
    """Compare multiple professors"""
    try:
        # Import the implementation function directly to avoid MCP tool wrapper
        from mcp_server.tools.schedule_optimizer import _get_professor_grade_impl
        
        professors_data = []
        for name in request.professor_names:
            prof_grade = await _get_professor_grade_impl(name, request.university, request.course_code)
            if prof_grade.get('success'):
                professors_data.append(prof_grade)
        
        if not professors_data:
            raise HTTPException(status_code=404, detail="No professor data found")
        
        # Sort by composite score
        professors_data.sort(key=lambda p: p.get('composite_score', 0), reverse=True)
        
        # Generate recommendation
        best_prof = professors_data[0]
        recommendation = f"Based on ratings and reviews, {best_prof.get('professor_name')} " \
                        f"(Grade: {best_prof.get('grade_letter')}) is recommended."
        
        result = {
            'success': True,
            'total_professors': len(professors_data),
            'professors': professors_data,
            'recommendation': recommendation,
            'course_code': request.course_code,
        }
             
        return ApiResponse(
            data=result,
            metadata=ResponseMetadata(
                source="hybrid",
                last_updated=None,
                is_fresh=True,
                auto_populated=True,
                count=len(request.professor_names)
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing professors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ScheduleValidationRequest(BaseModel):
    schedule_id: str
    section_id: str
    action: str  # 'add' or 'remove'


@app.post("/api/schedule/validate")
async def validate_schedule_action(request: ScheduleValidationRequest):
    """Validate adding/removing a section to/from a schedule"""
    try:
        # Check for conflicts
        if request.action == "add":
            # Get section details
            section = await supabase_service.get_section_by_id(request.section_id)
            if not section:
                raise HTTPException(status_code=404, detail="Section not found")
            
            # Get current schedule sections
            # This is a simplified check - in a real app we'd fetch the full schedule
            # For now, we'll assume the frontend handles basic conflict detection
            # and the backend does a second pass or more complex validation
            
            # TODO: Implement full conflict detection logic here
            # For now, return success
            pass
            
        return {
            "valid": True,
            "conflicts": [],
            "warnings": [],
            "suggestions": []
        }
    except Exception as e:
        logger.error(f"Error validating schedule action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_next_semester(current_date: Optional[datetime] = None) -> str:
    """
    Calculate the next semester students are likely registering for.
    Based on CUNY registration cycles.
    
    Registration periods:
    - Oct-Dec: Registering for Spring (next year)
    - Jan-May: Registering for Fall (same year) - Spring is already in session
    - Jun-Sep: Registering for Fall (same year)
    
    Args:
        current_date: Optional date to use (defaults to now in Eastern Time, useful for testing)
    
    Returns:
        Semester string like "Spring 2025" or "Fall 2025"
    """
<<<<<<< Updated upstream
    return "Spring 2026"
    # from datetime import datetime
    # from zoneinfo import ZoneInfo
    #
    # # Use Eastern Time for CUNY students
    # if current_date:
    #     now = current_date
    # else:
    #     now = datetime.now(ZoneInfo("America/New_York"))
    #
    # month = now.month
    # year = now.year
    #
    # # Oct-Dec: Students registering for Spring (next year)
    # if month >= 10:
    #     return f"Spring {year + 1}"
    #
    # # Jan-Sep: Students registering for Fall (same year)
    # # In January, Spring semester has started, so next registration is Fall
    # return f"Fall {year}"
=======
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    # Use Eastern Time for CUNY students
    if current_date:
        now = current_date
    else:
        now = datetime.now(ZoneInfo("America/New_York"))
    
    month = now.month
    year = now.year
    
    # Oct-Dec: Students registering for Spring (next year)
    if month >= 10:
        return f"Spring {year + 1}"
    
    # Jan-Sep: Students registering for Fall (same year)
    # In January, Spring semester has started, so next registration is Fall
    return f"Fall {year}"
>>>>>>> Stashed changes



def _extract_context_from_history(history: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """
    Heuristic to extract university and semester from chat history.
    This is a fallback when the frontend context is missing.
    """
    import re
    from datetime import datetime
    
    extracted = {"university": None, "semester": None}
    
    # Common CUNY colleges - expanded list
    universities = {
        "baruch": "Baruch College",
        "csi": "College of Staten Island",
        "staten island": "College of Staten Island",
        "hunter": "Hunter College",
        "city college": "City College",
        "ccny": "City College",
        "queens": "Queens College",
        "brooklyn": "Brooklyn College",
        "bmcc": "Borough of Manhattan Community College",
        "laguardia": "LaGuardia Community College",
        "lehman": "Lehman College",
        "medgar evers": "Medgar Evers College",
        "york": "York College",
        "john jay": "John Jay College",
        "hostos": "Hostos Community College",
        "kingsborough": "Kingsborough Community College",
        "queensborough": "Queensborough Community College",
        "bronx community": "Bronx Community College",
        "cuny grad center": "CUNY Graduate Center",
        "guttman": "Guttman Community College",
    }
    
    # Semester patterns
    # Matches: "Fall 2025", "Spring '25", "Summer 2025", "Fall 25"
    semester_pattern = re.compile(r'\b(fall|spring|summer|winter)\s+(\'?\d{2,4})\b', re.IGNORECASE)
    # Matches: "next fall", "this spring", "upcoming summer"
    relative_semester_pattern = re.compile(r'\b(next|this|upcoming|current)\s+(fall|spring|summer|winter)\b', re.IGNORECASE)
    
    # Calculate current/next semester for relative references
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    def resolve_relative_semester(modifier: str, term: str) -> str:
        """Resolve 'next fall' or 'this spring' to actual semester"""
        term = term.capitalize()
        
        # Determine which year based on current date and term
        term_months = {"Spring": 1, "Summer": 6, "Fall": 9, "Winter": 12}
        term_month = term_months.get(term, 1)
        
        if modifier.lower() in ("next", "upcoming"):
            # Next occurrence of this term
            if current_month < term_month:
                return f"{term} {current_year}"
            else:
                return f"{term} {current_year + 1}"
        else:  # "this" or "current"
            return f"{term} {current_year}"
    
    logger.debug(f"Scanning history for context. {len(history)} messages.")
    
    # Scan history in reverse (most recent first)
    for msg in reversed(history):
        content = msg.get("content", "").lower()
        logger.debug(f"Scanning message: {content[:50]}...")
        if not content:
            continue
            
        # Check for university if not found yet
        if not extracted["university"]:
            for key, name in universities.items():
                if key in content:
                    extracted["university"] = name
                    logger.debug(f"Found university: {name} (key: {key})")
                    break
        
        # Check for semester if not found yet
        if not extracted["semester"]:
            # Try explicit semester first (Fall 2025, Spring '25)
            match = semester_pattern.search(content)
            if match:
                term = match.group(1).capitalize()
                year_raw = match.group(2).replace("'", "")
                # Normalize year to 4 digits
                if len(year_raw) == 2:
                    year = f"20{year_raw}"
                else:
                    year = year_raw
                    
                extracted["semester"] = f"{term} {year}"
                logger.debug(f"Found semester: {extracted['semester']}")
            else:
                # Try relative semester (next fall, this spring)
                relative_match = relative_semester_pattern.search(content)
                if relative_match:
                    modifier = relative_match.group(1)
                    term = relative_match.group(2)
                    extracted["semester"] = resolve_relative_semester(modifier, term)
                    logger.debug(f"Found relative semester: {extracted['semester']}")
                
        # If both found, stop scanning
        if extracted["university"] and extracted["semester"]:
            break
            
    return extracted


@app.post("/api/chat/message")
async def chat_with_ai(message: Dict[str, Any]):
    """Chat with AI assistant for schedule recommendations using MCP tools"""
    try:
        import json as json_module
        from ollama import Client as OllamaClient
        from mcp_server.tools.schedule_optimizer import (
            fetch_course_sections,
            generate_optimized_schedule,
            get_professor_grade,
            compare_professors as compare_professors_tool,
        )
        from mcp_server.utils.chat_tool_result import pick_better_fetch_sections_result
        
        user_message = message.get("message", "")
        context = message.get("context", {})
        history_raw = message.get("history", [])
        
        logger.debug(f"Received chat message: {user_message[:100]}...")
        logger.debug(f"Received context: {context}")
        logger.debug(f"Received history length: {len(history_raw)}")

        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Configure Ollama client with auth
        headers = {}
        if settings.ollama_api_key:
            headers['Authorization'] = f'Bearer {settings.ollama_api_key}'
        ollama_client = OllamaClient(host=settings.ollama_host, headers=headers)
        
        # ============================================
        # STEP 1: EXTRACT CONTEXT FIRST (before tool declarations!)
        # ============================================
        current_courses = context.get("currentCourses", [])
        
        # Extract context from BOTH current message AND history
        current_msg_context = _extract_context_from_history([{"role": "user", "content": user_message}])
        history_context = _extract_context_from_history(history_raw)
        
        # Calculate default semester based on current date
        default_semester = get_next_semester()
        
        # Priority for university: current message > history > frontend context
        university = (
            current_msg_context["university"] or 
            history_context["university"] or 
            context.get("university")
        )
        
        # Priority for semester:
        # 1. Current message (what user is saying RIGHT NOW)
        # 2. Chat history (what user said earlier this session)
        # 3. Backend-calculated default (always Spring 2026 until changed)
        # 4. Frontend persisted cache (lowest - may be stale from old sessions)
        semester = (
            current_msg_context["semester"] or      # Explicit in current message (highest trust)
            history_context["semester"] or          # Mentioned earlier this session
            default_semester or                     # Backend-calculated default (Spring 2026)
            context.get("semester")                 # Stale frontend cache (lowest priority)
        )
        
        university_str = university if university else "Not yet specified"
        semester_str = semester  # Will always be set now (never "Not yet specified")
        
        logger.info(f"Context: university={university_str}, semester={semester_str} (default={default_semester})")
        
        # ============================================
        # STEP 2: BUILD TOOL DECLARATIONS WITH CONTEXT EMBEDDED
        # ============================================
        
        # Dynamic descriptions with auto-calculated defaults
        university_desc = f"University (optional - defaults to '{university_str}' if not specified)"
        semester_desc = f"Semester (optional - defaults to '{semester_str}' for current registration)"
        
        tools = [
            {
                'type': 'function',
                'function': {
                    'name': 'fetch_course_sections',
                    'description': f"Fetch available course sections from the database.\nDefault semester: {semester_str}. Default university: {university_str}.",
                    'parameters': {
                        'type': 'object',
                        'required': ['course_codes'],
                        'properties': {
                            'course_codes': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': "List of course codes like ['CSC 126'] or ['MTH 231', 'CSC 446']"
                            },
                            'semester': {'type': 'string', 'description': semester_desc},
                            'university': {'type': 'string', 'description': university_desc},
                        },
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'generate_optimized_schedule',
                    'description': f"Generate an optimized schedule from a list of desired courses.\nDefault semester: {semester_str}. Default university: {university_str}.",
                    'parameters': {
                        'type': 'object',
                        'required': ['course_codes'],
                        'properties': {
                            'course_codes': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': "List of course codes like ['CSC 126', 'MTH 231', 'ENG 101']"
                            },
                            'semester': {'type': 'string', 'description': semester_desc},
                            'university': {'type': 'string', 'description': university_desc},
                        },
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'get_professor_grade',
                    'description': f"Get RateMyProfessor rating and grade distribution for a professor.\nNOTE: User is at {university_str}. Use this as the default university.",
                    'parameters': {
                        'type': 'object',
                        'required': ['professor_name'],
                        'properties': {
                            'professor_name': {
                                'type': 'string',
                                'description': "Professor's name like 'John Smith'"
                            },
                            'university': {'type': 'string', 'description': university_desc},
                        },
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'compare_professors',
                    'description': f"Compare multiple professors teaching the same course.\nNOTE: User is at {university_str}. Use this as the default university.",
                    'parameters': {
                        'type': 'object',
                        'required': ['professor_names'],
                        'properties': {
                            'professor_names': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': "List of professor names to compare"
                            },
                            'university': {'type': 'string', 'description': university_desc},
                            'course_code': {
                                'type': 'string',
                                'description': "Optional course code for context"
                            },
                        },
                    },
                },
            },
        ]
        
        # ============================================
        # STEP 3: BUILD SYSTEM INSTRUCTION & MESSAGES
        # ============================================
        system_instruction = f"""You are an AI assistant helping CUNY students plan their class schedules.

You have access to real tools to fetch course data, professor ratings, and generate optimized schedules.
ALWAYS use these tools to get real data - never make up course times, professor ratings, or schedules.

=== CURRENT USER CONTEXT ===
University: {university_str}
Semester: {semester_str}
Courses in schedule: {', '.join([c.get('name', c.get('code', 'Unknown')) for c in current_courses]) if current_courses else 'None yet'}
=== END CONTEXT ===

CRITICAL RULES:
1. The default semester is "{semester_str}" and university is "{university_str}".
2. If university is NOT "Not yet specified", DO NOT ask for it - you already know it!
3. When calling tools, use semester="{semester_str}" and university="{university_str}" unless user specified different.
4. If user mentions a different semester (e.g., "Fall 2026"), use that instead.
5. Only ask for university if it shows "Not yet specified" above.

TOOL USAGE:
- Use fetch_course_sections to get real course section data with times, professors, and availability.
- Use generate_optimized_schedule when the user wants help building a conflict-free schedule.
- Use get_professor_grade or compare_professors to help users choose between professors.

When presenting course sections, include: section number, days/times, professor name, location, and seats available."""

        # Build messages list (Ollama uses a flat list, not stateful chat)
        messages = [{'role': 'system', 'content': system_instruction}]
        
        # Add history
        for msg in history_raw:
            role = "user" if msg.get("role") == "user" else "assistant"
            content = msg.get("content", "")
            if content:
                messages.append({'role': role, 'content': content})
        
        # Add current user message
        messages.append({'role': 'user', 'content': user_message})

        # Start chat and get initial response
        response = ollama_client.chat(
            model=settings.ollama_model,
            messages=messages,
            tools=tools,
        )
        last_fetch_sections_result: Optional[Dict[str, Any]] = None
        fetch_sections_result_cache: Dict[str, Any] = {}
        
        # Handle function calling loop (max 6 tool calls)
        tool_call_count = 0
        max_tool_calls = 6
        
        while response.message.tool_calls and tool_call_count < max_tool_calls:
            # Append the assistant's message (with tool_calls) to the messages list
            messages.append(response.message)
            
            # Process each function call
            for tc in response.message.tool_calls:
                tool_call_count += 1
                fc_name = tc.function.name
                logger.info(f"Tool call {tool_call_count}: {fc_name}")
                
                try:
                    # Get function arguments
                    args = tc.function.arguments or {}
                    
                    # Merge in context defaults for missing arguments
                    effective_semester = args.get("semester") or semester or ""
                    effective_university = args.get("university") or university or ""
                    
                    # Execute the appropriate MCP tool with validation
                    if fc_name == "fetch_course_sections":
                        # Handle both singular course_code and plural course_codes
                        course_codes = args.get("course_codes", [])
                        if not course_codes:
                            # Try singular for backwards compatibility
                            single_code = args.get("course_code", "")
                            if single_code:
                                course_codes = [single_code]
                        
                        if not course_codes:
                            result = {
                                "success": False,
                                "error": "Course code(s) required",
                                "error_code": "VALIDATION_ERROR",
                                "suggestions": ["Please specify a course code like 'CSC 126' or 'MTH 231'"]
                            }
                        elif not effective_semester:
                            result = {
                                "success": False,
                                "error": "Semester is required",
                                "error_code": "VALIDATION_ERROR",
                                "suggestions": ["Please specify a semester like 'Fall 2025' or 'Spring 2025'"]
                            }
                        elif not effective_university:
                            result = {
                                "success": False,
                                "error": "University is required",
                                "error_code": "VALIDATION_ERROR",
                                "suggestions": ["Please specify your school like 'Baruch College' or 'Hunter College'"]
                            }
                        else:
                            dedupe_key_payload = {
                                "course_codes": [
                                    str(code).strip().upper()
                                    for code in course_codes
                                ],
                                "semester": str(effective_semester).strip(),
                                "university": str(effective_university).strip(),
                            }
                            dedupe_key = json_module.dumps(dedupe_key_payload, sort_keys=True)

                            if dedupe_key in fetch_sections_result_cache:
                                result = fetch_sections_result_cache[dedupe_key]
                                logger.info(
                                    "Reusing cached fetch_course_sections result within chat request",
                                    extra={
                                        "course_codes": dedupe_key_payload["course_codes"],
                                        "semester": dedupe_key_payload["semester"],
                                        "university": dedupe_key_payload["university"],
                                    },
                                )
                            else:
                                result = await fetch_course_sections.fn(
                                    course_codes=course_codes,
                                    semester=effective_semester,
                                    university=effective_university
                                )
                                fetch_sections_result_cache[dedupe_key] = result

                            if isinstance(result, dict):
                                last_fetch_sections_result = pick_better_fetch_sections_result(
                                    last_fetch_sections_result,
                                    result,
                                )
                    elif fc_name == "generate_optimized_schedule":
                        course_codes = args.get("course_codes", [])
                        if not course_codes:
                            result = {
                                "success": False,
                                "error": "Course codes are required",
                                "error_code": "VALIDATION_ERROR",
                                "suggestions": ["Please specify the courses you want to schedule"]
                            }
                        elif not effective_semester:
                            result = {
                                "success": False,
                                "error": "Semester is required",
                                "error_code": "VALIDATION_ERROR",
                                "suggestions": ["Please specify a semester like 'Fall 2025'"]
                            }
                        elif not effective_university:
                            result = {
                                "success": False,
                                "error": "University is required",
                                "error_code": "VALIDATION_ERROR",
                                "suggestions": ["Please specify your school"]
                            }
                        else:
                            result = await generate_optimized_schedule.fn(
                                course_codes=course_codes,
                                semester=effective_semester,
                                university=effective_university,
                                preferences=args.get("preferences")
                            )
                    elif fc_name == "get_professor_grade":
                        professor_name = args.get("professor_name", "")
                        if not professor_name:
                            result = {
                                "success": False,
                                "error": "Professor name is required",
                                "error_code": "VALIDATION_ERROR",
                                "suggestions": ["Please specify the professor's name"]
                            }
                        elif not effective_university:
                            result = {
                                "success": False,
                                "error": "University is required",
                                "error_code": "VALIDATION_ERROR",
                                "suggestions": ["Please specify your school"]
                            }
                        else:
                            result = await get_professor_grade.fn(
                                professor_name=professor_name,
                                university=effective_university
                            )
                    elif fc_name == "compare_professors":
                        professor_names = args.get("professor_names", [])
                        if not professor_names or len(professor_names) < 2:
                            result = {
                                "success": False,
                                "error": "At least two professor names are required for comparison",
                                "error_code": "VALIDATION_ERROR",
                                "suggestions": ["Please specify at least two professors to compare"]
                            }
                        elif not effective_university:
                            result = {
                                "success": False,
                                "error": "University is required",
                                "error_code": "VALIDATION_ERROR",
                                "suggestions": ["Please specify your school"]
                            }
                        else:
                            result = await compare_professors_tool.fn(
                                professor_names=professor_names,
                                university=effective_university,
                                course_code=args.get("course_code")
                            )
                    else:
                        result = {"error": f"Unknown function: {fc_name}", "error_code": "UNKNOWN_FUNCTION"}
                    
                    formatted_result = format_tool_result_for_log(
                        result,
                        max_chars=settings.log_tool_result_preview_chars,
                        full=settings.log_full_tool_results,
                    )
                    logger.info(f"Tool {fc_name} result: {formatted_result}")
                    
                except Exception as tool_error:
                    logger.error(f"Error executing tool {fc_name}: {tool_error}")
                    result = {"error": str(tool_error)}
                
                # Add tool result to messages
                messages.append({
                    'role': 'tool',
                    'tool_name': fc_name,
                    'content': json_module.dumps(result) if not isinstance(result, str) else result,
                })
            
            # Send updated messages back to get next response
            response = ollama_client.chat(
                model=settings.ollama_model,
                messages=messages,
                tools=tools,
            )

        if last_fetch_sections_result is None and tool_call_count == 0 and semester and university:
            import re

            inferred_course_codes = re.findall(r"\b[A-Za-z]{2,4}\s?\d{3}[A-Za-z]?\b", user_message)
            normalized_codes = [
                f"{match[:-3].strip().upper()} {match[-3:].upper()}"
                if " " not in match.strip()
                else match.strip().upper()
                for match in inferred_course_codes
            ]
            if normalized_codes:
                try:
                    inferred_result = await fetch_course_sections.fn(
                        course_codes=normalized_codes,
                        semester=semester,
                        university=university,
                    )
                    if isinstance(inferred_result, dict):
                        last_fetch_sections_result = pick_better_fetch_sections_result(
                            last_fetch_sections_result,
                            inferred_result,
                        )
                except Exception as infer_error:
                    logger.warning(
                        "Auto-fetch fallback for course-code query failed",
                        extra={"error": str(infer_error), "course_codes": normalized_codes},
                    )
        
        # Extract final text response
        final_text = response.message.content or ""

        if isinstance(last_fetch_sections_result, dict):
            success = bool(last_fetch_sections_result.get("success"))
            total_courses = int(last_fetch_sections_result.get("total_courses") or 0)
            courses = last_fetch_sections_result.get("courses") or []
            if success and total_courses > 0 and isinstance(courses, list):
                total_sections = 0
                first_course_code = "Requested course"
                for idx, course in enumerate(courses):
                    if not isinstance(course, dict):
                        continue
                    if idx == 0:
                        first_course_code = course.get("course_code") or first_course_code
                    sections = course.get("sections") or []
                    if isinstance(sections, list):
                        total_sections += len(sections)

                final_text = (
                    f"I found {total_courses} matching course(s) for {semester_str} at {university_str}. "
                    f"{first_course_code} is available with {total_sections} section(s) currently returned."
                )
        
        if not final_text:
            final_text = "I encountered an issue processing your request. Please try again."
        
        # Return merged context so frontend can update its state with inferred values
        merged_context = {
            **context,
            "university": university if university else context.get("university"),
            "semester": semester if semester else context.get("semester"),
        }
        
        return {
            "message": final_text,
            "suggestions": [],
            "context": merged_context,
            "tool_calls_made": tool_call_count
        }
        
    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ADMIN ENDPOINTS
# ============================================

class SyncRequest(BaseModel):
    entity_type: str
    semester: Optional[str] = None
    university: Optional[str] = None
    force: bool = False


@app.post("/api/admin/sync")
async def admin_sync(
    request: SyncRequest,
    credentials: HTTPAuthorizationCredentials = Depends(verify_admin_token)
):
    """Trigger manual data sync"""
    try:
        success = False
        if request.entity_type == "courses":
            if not request.semester:
                raise HTTPException(status_code=400, detail="Semester required for course sync")
            
            population_result = await data_population_service.ensure_course_data(
                request.semester, 
                request.university or "Baruch College",
                force=request.force
            )
            success = population_result.success
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported entity type: {request.entity_type}")
            
        return {"success": success, "request": request.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in admin sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/sync-status")
async def admin_sync_status(
    entity_type: str,
    semester: str,
    university: str
):
    """Get sync status"""
    try:
        metadata = await supabase_service.get_sync_metadata(entity_type, semester, university)
        if not metadata:
            raise HTTPException(status_code=404, detail="Sync metadata not found")
            
        return metadata.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/analytics")
async def admin_analytics(
    credentials: HTTPAuthorizationCredentials = Depends(verify_admin_token)
):
    """Get usage analytics for admin dashboard"""
    try:
        cache_stats = cache_manager.get_stats()
        metrics = await metrics_collector.get_all_metrics(cache_stats)
        
        return {
            "usage": metrics.get("usage", {}),
            "requests": {
                "total": metrics.get("requests", {}).get("total", 0),
                "error_rate": metrics.get("requests", {}).get("error_rate", 0),
            },
            "cache": {
                "hit_rate": cache_stats.get("hit_rate", 0),
                "total_entries": cache_stats.get("total_entries", 0),
            },
            "uptime": {
                "seconds": metrics.get("uptime_seconds", 0),
                "human": metrics.get("uptime_human", "unknown"),
            },
        }
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/cache/clear")
async def admin_cache_clear(
    credentials: HTTPAuthorizationCredentials = Depends(verify_admin_token)
):
    """Clear the application cache"""
    try:
        logger.warning("Cache clear requested by admin")
        stats_before = cache_manager.get_stats()
        await cache_manager.clear()
        stats_after = cache_manager.get_stats()
        
        return {
            "success": True,
            "cleared_entries": stats_before.get("total_entries", 0),
            "stats_before": stats_before,
            "stats_after": stats_after,
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# FEEDBACK ENDPOINTS
# ============================================

class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    category: str = Field(..., description="Feedback category (e.g., 'performance', 'accuracy', 'feature')")
    message: str = Field(..., max_length=2000, description="Feedback message")
    page: Optional[str] = Field(None, description="Page where feedback was submitted")
    user_agent: Optional[str] = Field(None, description="User's browser/device info")


@app.post("/api/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit user feedback"""
    try:
        # Log feedback for now (could store in database later)
        logger.info(
            f"User feedback received",
            extra={
                "rating": feedback.rating,
                "category": feedback.category,
                "message": feedback.message[:100],  # Truncate for log
                "page": feedback.page,
            }
        )
        
        return {
            "success": True,
            "message": "Thank you for your feedback!",
            "feedback_id": None,  # Would be DB ID if storing
        }
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    )
