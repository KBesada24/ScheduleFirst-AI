"""
CUNY Schedule Optimizer MCP Server
Backend services for AI-powered course scheduling
"""

__version__ = "0.1.0"
__author__ = "CUNY Schedule Optimizer Team"

from .config import settings
from .utils.logger import get_logger

__all__ = ["settings", "get_logger"]
