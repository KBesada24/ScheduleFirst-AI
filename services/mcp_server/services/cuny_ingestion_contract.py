"""Shared contracts for CUNY ingestion sources and orchestration."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class IngestionSourceResult:
    """Normalized result returned by Browser-Use and Selenium ingestion sources."""

    success: bool
    source: str
    courses: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "source": self.source,
            "courses": self.courses,
            "warnings": self.warnings,
            "error": self.error,
            "fallback_used": self.fallback_used,
        }


class CunyIngestionConnector(Protocol):
    async def fetch_courses(
        self,
        semester: str,
        university: Optional[str] = None,
        subject_code: Optional[str] = None,
    ) -> IngestionSourceResult:
        ...
