"""
REST API Server for CUNY Schedule Optimizer
Serves the React frontend with schedule optimization endpoints
"""
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Dict, Any
import uvicorn

from mcp_server.config import settings
from mcp_server.services.supabase_service import supabase_service
from mcp_server.services.constraint_solver import schedule_optimizer
from mcp_server.services.sentiment_analyzer import sentiment_analyzer
from mcp_server.utils.logger import get_logger
from mcp_server.models.schedule import ScheduleConstraints, OptimizedSchedule
from mcp_server.models.course import CourseSearchFilter
from mcp_server.models.api_models import ApiResponse, ResponseMetadata
from mcp_server.services.data_population_service import data_population_service
from mcp_server.services.data_freshness_service import data_freshness_service
from mcp_server.tools.schedule_optimizer import compare_professors

logger = get_logger(__name__)


class ScheduleOptimizeRequest(BaseModel):
    course_codes: List[str]
    semester: str
    university: str
    constraints: ScheduleConstraints


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("=" * 60)
    logger.info("CUNY Schedule Optimizer API Server")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"API Host: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"Gemini API: {'✓ Configured' if settings.gemini_api_key else '✗ Not configured'}")
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
    
    logger.info("=" * 60)
    logger.info("API Server ready!")
    logger.info("Available endpoints:")
    logger.info("  GET  /health")
    logger.info("  GET  /api/courses")
    logger.info("  POST /api/schedule/optimize")
    logger.info("  GET  /api/professor/{name}")
    logger.info("  POST /api/professor/compare")
    logger.info("  POST /api/admin/sync")
    logger.info("=" * 60)
    
    yield
    
    logger.info("Shutting down API server...")


app = FastAPI(
    title="CUNY Schedule Optimizer API",
    description="AI-powered schedule optimization for CUNY students",
    version="1.0.0",
    lifespan=lifespan
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
    """Health check endpoint"""
    try:
        db_healthy = await supabase_service.health_check()
        return {
            "status": "healthy" if db_healthy else "degraded",
            "database": "connected" if db_healthy else "disconnected",
            "environment": settings.environment,
            "gemini_api": "configured" if settings.gemini_api_key else "not configured"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


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
            was_populated = await data_population_service.ensure_course_data(semester, university)
        
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
            was_populated = await data_population_service.ensure_course_data(
                filters.semester, 
                filters.university
            )
            
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
        schedules = await schedule_optimizer.generate_schedules(
            all_sections,
            request.constraints
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
            was_populated = await data_population_service.ensure_professor_data(
                professor_name, 
                university
            )
            
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
    course_code: str = None


@app.post("/api/professor/compare", response_model=ApiResponse)
async def compare_professors_endpoint(request: ProfessorComparisonRequest):
    """Compare multiple professors"""
    try:
        # Use MCP tool logic
        result = await compare_professors(
            professor_names=request.professor_names,
            university=request.university,
            course_code=request.course_code
        )
        
        if not result.get("success"):
             raise HTTPException(status_code=400, detail=result.get("error"))
             
        return ApiResponse(
            data=result,
            metadata=ResponseMetadata(
                source="hybrid",
                is_fresh=True, # Comparison fetches fresh data
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
    """Chat with AI assistant for schedule recommendations"""
    try:
        import google.generativeai as genai
        
        user_message = message.get("message", "")
        context = message.get("context", {})
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Configure Gemini API
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Build context for the AI
        current_courses = context.get("currentCourses", [])
        semester = context.get("semester", "Spring 2025")
        university = context.get("university", "Baruch College")
        
        context_text = f"""You are an AI assistant helping students at {university} with their {semester} schedule.

Current schedule context:
- Courses in schedule: {', '.join([c.get('name', c.get('code', 'Unknown')) for c in current_courses]) if current_courses else 'None yet'}
- Number of courses: {len(current_courses)}

User question: {user_message}

Provide helpful, concise advice about:
- Course selection and recommendations
- Schedule optimization (avoiding conflicts, minimizing gaps)
- Professor insights (if relevant)
- General academic planning

Keep responses conversational and under 150 words."""

        # Generate AI response
        ai_response = model.generate_content(context_text)
        
        response = {
            "message": ai_response.text,
            "suggestions": [],
            "context": context
        }
        
        return response
        return response
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ADMIN ENDPOINTS
# ============================================

class SyncRequest(BaseModel):
    entity_type: str
    semester: str = None
    university: str = None
    force: bool = False


@app.post("/api/admin/sync")
async def admin_sync(request: SyncRequest):
    """Trigger manual data sync"""
    try:
        success = False
        if request.entity_type == "courses":
            if not request.semester:
                raise HTTPException(status_code=400, detail="Semester required for course sync")
            
            success = await data_population_service.ensure_course_data(
                request.semester, 
                request.university or "Baruch College",
                force=request.force
            )
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



if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    )