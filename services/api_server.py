"""
REST API Server for CUNY Schedule Optimizer
Serves the React frontend with schedule optimization endpoints
"""
import time
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
    logger.info(f"Gemini API: {'✓ Configured' if settings.gemini_api_key else '✗ Not configured'}")
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
            "gemini_api": "configured" if settings.gemini_api_key else "not configured",
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


@app.post("/api/chat/message")
async def chat_with_ai(message: Dict[str, Any]):
    """Chat with AI assistant for schedule recommendations using MCP tools"""
    try:
        import google.generativeai as genai  # type: ignore[import-untyped]
        from mcp_server.tools.schedule_optimizer import (
            fetch_course_sections,
            generate_optimized_schedule,
            get_professor_grade,
            compare_professors as compare_professors_tool,
        )
        
        user_message = message.get("message", "")
        context = message.get("context", {})
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Configure Gemini API with function calling
        genai.configure(api_key=settings.gemini_api_key)  # type: ignore[attr-defined]
        
        # Define tool functions for Gemini using proper protos format
        fetch_course_sections_decl = genai.protos.FunctionDeclaration(  # type: ignore[attr-defined]
            name="fetch_course_sections",
            description="Fetch available course sections from the database. Uses hybrid approach: checks DB first, auto-populates via scraping if data is stale or missing.",
            parameters=genai.protos.Schema(  # type: ignore[attr-defined]
                type=genai.protos.Type.OBJECT,  # type: ignore[attr-defined]
                properties={
                    "course_code": genai.protos.Schema(  # type: ignore[attr-defined]
                        type=genai.protos.Type.STRING,  # type: ignore[attr-defined]
                        description="Course code like 'CSC 126' or 'MTH 231'"
                    ),
                    "semester": genai.protos.Schema(  # type: ignore[attr-defined]
                        type=genai.protos.Type.STRING,  # type: ignore[attr-defined]
                        description="Semester like 'Spring 2025' or 'Fall 2025'"
                    ),
                    "university": genai.protos.Schema(  # type: ignore[attr-defined]
                        type=genai.protos.Type.STRING,  # type: ignore[attr-defined]
                        description="University name like 'CSI College' or 'Baruch College'"
                    ),
                },
                required=["course_code", "semester", "university"]
            )
        )
        
        generate_schedule_decl = genai.protos.FunctionDeclaration(  # type: ignore[attr-defined]
            name="generate_optimized_schedule",
            description="Generate an optimized schedule from a list of desired courses. Considers time conflicts, professor ratings, and preferences.",
            parameters=genai.protos.Schema(  # type: ignore[attr-defined]
                type=genai.protos.Type.OBJECT,  # type: ignore[attr-defined]
                properties={
                    "course_codes": genai.protos.Schema(  # type: ignore[attr-defined]
                        type=genai.protos.Type.ARRAY,  # type: ignore[attr-defined]
                        items=genai.protos.Schema(type=genai.protos.Type.STRING),  # type: ignore[attr-defined]
                        description="List of course codes like ['CSC 126', 'MTH 231', 'ENG 101']"
                    ),
                    "semester": genai.protos.Schema(  # type: ignore[attr-defined]
                        type=genai.protos.Type.STRING,  # type: ignore[attr-defined]
                        description="Semester like 'Spring 2025'"
                    ),
                    "university": genai.protos.Schema(  # type: ignore[attr-defined]
                        type=genai.protos.Type.STRING,  # type: ignore[attr-defined]
                        description="University name"
                    ),
                },
                required=["course_codes", "semester", "university"]
            )
        )
        
        get_professor_grade_decl = genai.protos.FunctionDeclaration(  # type: ignore[attr-defined]
            name="get_professor_grade",
            description="Get RateMyProfessor rating and grade distribution for a professor.",
            parameters=genai.protos.Schema(  # type: ignore[attr-defined]
                type=genai.protos.Type.OBJECT,  # type: ignore[attr-defined]
                properties={
                    "professor_name": genai.protos.Schema(  # type: ignore[attr-defined]
                        type=genai.protos.Type.STRING,  # type: ignore[attr-defined]
                        description="Professor's name like 'John Smith'"
                    ),
                    "university": genai.protos.Schema(  # type: ignore[attr-defined]
                        type=genai.protos.Type.STRING,  # type: ignore[attr-defined]
                        description="University name"
                    ),
                },
                required=["professor_name", "university"]
            )
        )
        
        compare_professors_decl = genai.protos.FunctionDeclaration(  # type: ignore[attr-defined]
            name="compare_professors",
            description="Compare multiple professors teaching the same course based on ratings and reviews.",
            parameters=genai.protos.Schema(  # type: ignore[attr-defined]
                type=genai.protos.Type.OBJECT,  # type: ignore[attr-defined]
                properties={
                    "professor_names": genai.protos.Schema(  # type: ignore[attr-defined]
                        type=genai.protos.Type.ARRAY,  # type: ignore[attr-defined]
                        items=genai.protos.Schema(type=genai.protos.Type.STRING),  # type: ignore[attr-defined]
                        description="List of professor names to compare"
                    ),
                    "university": genai.protos.Schema(  # type: ignore[attr-defined]
                        type=genai.protos.Type.STRING,  # type: ignore[attr-defined]
                        description="University name"
                    ),
                    "course_code": genai.protos.Schema(  # type: ignore[attr-defined]
                        type=genai.protos.Type.STRING,  # type: ignore[attr-defined]
                        description="Optional course code for context"
                    ),
                },
                required=["professor_names", "university"]
            )
        )
        
        # Create tool with all function declarations
        tools = genai.protos.Tool(  # type: ignore[attr-defined]
            function_declarations=[
                fetch_course_sections_decl,
                generate_schedule_decl,
                get_professor_grade_decl,
                compare_professors_decl,
            ]
        )
        
        # Build context for the AI
        current_courses = context.get("currentCourses", [])
        semester = context.get("semester")  # No default - LLM should ask if missing
        university = context.get("university")  # No default - LLM should ask if missing
        
        # Build context strings - only mark as unknown if truly not provided
        university_str = university if university else "Not yet specified"
        semester_str = semester if semester else "Not yet specified"
        
        system_instruction = f"""You are an AI assistant helping CUNY students plan their class schedules.

You have access to real tools to fetch course data, professor ratings, and generate optimized schedules.
ALWAYS use these tools to get real data - never make up course times, professor ratings, or schedules.

Current context from app:
- University: {university_str}
- Semester: {semester_str}
- Courses in schedule: {', '.join([c.get('name', c.get('code', 'Unknown')) for c in current_courses]) if current_courses else 'None yet'}

IMPORTANT RULES:
1. If the user mentions their university or semester in their message, USE THAT INFO to call tools - don't ask again.
2. Only ask for university/semester if the user hasn't mentioned it AND it's not in the context above.
3. Use fetch_course_sections to get real course section data with times, professors, and availability.
4. Use generate_optimized_schedule when the user wants help building a conflict-free schedule.
5. Use get_professor_grade or compare_professors to help users choose between professors.
6. Provide specific, actionable information based on real data from the tools.

When presenting course sections, include:
- Section number
- Days and times
- Professor name
- Location (if available)
- Seats available (if available)"""

        # Create model with tools
        model = genai.GenerativeModel(  # type: ignore[attr-defined]
            'gemini-2.0-flash',
            tools=[tools],
            system_instruction=system_instruction
        )
        
        # Start chat and get initial response
        chat = model.start_chat()
        response = chat.send_message(user_message)
        
        # Handle function calling loop (max 6 tool calls)
        tool_call_count = 0
        max_tool_calls = 6
        
        while response.candidates[0].content.parts:
            # Check if there are function calls to process
            function_calls = [
                part for part in response.candidates[0].content.parts 
                if hasattr(part, 'function_call') and part.function_call.name
            ]
            
            if not function_calls:
                break  # No more function calls, we have the final text response
            
            if tool_call_count >= max_tool_calls:
                logger.warning(f"Reached max tool calls ({max_tool_calls}), stopping")
                break
            
            # Process each function call
            function_responses = []
            for fc_part in function_calls:
                fc = fc_part.function_call
                tool_call_count += 1
                logger.info(f"Tool call {tool_call_count}: {fc.name}")
                
                try:
                    # Get function arguments
                    args = dict(fc.args) if fc.args else {}
                    
                    # Execute the appropriate MCP tool
                    if fc.name == "fetch_course_sections":
                        result = await fetch_course_sections.fn(
                            course_code=args.get("course_code", ""),
                            semester=args.get("semester", semester or ""),
                            university=args.get("university", university or "")
                        )
                    elif fc.name == "generate_optimized_schedule":
                        result = await generate_optimized_schedule.fn(
                            course_codes=args.get("course_codes", []),
                            semester=args.get("semester", semester or ""),
                            university=args.get("university", university or ""),
                            preferences=args.get("preferences")
                        )
                    elif fc.name == "get_professor_grade":
                        result = await get_professor_grade.fn(
                            professor_name=args.get("professor_name", ""),
                            university=args.get("university", university or "")
                        )
                    elif fc.name == "compare_professors":
                        result = await compare_professors_tool.fn(
                            professor_names=args.get("professor_names", []),
                            university=args.get("university", university or ""),
                            course_code=args.get("course_code")
                        )
                    else:
                        result = {"error": f"Unknown function: {fc.name}"}
                    
                    logger.info(f"Tool {fc.name} result: {str(result)[:200]}...")
                    
                except Exception as tool_error:
                    logger.error(f"Error executing tool {fc.name}: {tool_error}")
                    result = {"error": str(tool_error)}
                
                # Build function response
                function_responses.append(
                    genai.protos.Part(  # type: ignore[attr-defined]
                        function_response=genai.protos.FunctionResponse(  # type: ignore[attr-defined]
                            name=fc.name,
                            response={"result": result}
                        )
                    )
                )
            
            # Send function responses back to the model
            response = chat.send_message(function_responses)
        
        # Extract final text response
        final_text = ""
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text') and part.text:
                final_text += part.text
        
        if not final_text:
            final_text = "I encountered an issue processing your request. Please try again."
        
        return {
            "message": final_text,
            "suggestions": [],
            "context": context,
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