"""
Main entry point for CUNY Schedule Optimizer MCP Server
"""
import asyncio

from .config import settings
from .utils.logger import get_logger
from .tools import mcp
from .services.supabase_service import supabase_service


logger = get_logger(__name__)


async def startup_checks():
    """Perform startup checks before running server"""
    logger.info("=" * 60)
    logger.info("CUNY Schedule Optimizer MCP Server")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"API Host: {settings.api_host}:{settings.api_port}")
    logger.info("=" * 60)
    
    # Health check
    logger.info("Performing database health check...")
    db_healthy = await supabase_service.health_check()
    if db_healthy:
        logger.info("✓ Database connection healthy")
    else:
        logger.error("✗ Database connection failed")
        logger.warning("Server will start but database operations may fail")
    
    logger.info("MCP Server ready!")
    logger.info("Available tools:")
    logger.info("  - fetch_course_sections")
    logger.info("  - generate_optimized_schedule")
    logger.info("  - get_professor_grade")
    logger.info("  - compare_professors")
    logger.info("  - check_schedule_conflicts")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        # Run startup checks
        asyncio.run(startup_checks())
        
        # Run the MCP server (this is synchronous and blocks)
        logger.info("Starting MCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
