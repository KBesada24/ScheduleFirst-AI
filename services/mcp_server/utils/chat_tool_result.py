"""Helpers for selecting the best fetch_course_sections tool result within a chat turn."""

from typing import Any, Dict, Optional, Tuple


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _quality_rank(data_quality: Any) -> int:
    ranks = {
        "degraded": 0,
        "stale": 1,
        "partial": 2,
        "full": 3,
    }
    return ranks.get(str(data_quality).lower(), 1)


def _score_fetch_sections_result(result: Dict[str, Any]) -> Tuple[int, int, int, int, int]:
    success = 1 if bool(result.get("success")) else 0
    total_courses = _as_int(result.get("total_courses"), 0)
    has_courses = 1 if total_courses > 0 else 0
    quality = _quality_rank(result.get("data_quality"))
    warnings_count = len(result.get("warnings") or [])
    return (success, has_courses, total_courses, quality, -warnings_count)


def pick_better_fetch_sections_result(
    current: Optional[Dict[str, Any]], candidate: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Return the stronger fetch_course_sections result between current and candidate."""
    if not isinstance(candidate, dict):
        return current
    if not isinstance(current, dict):
        return candidate

    if _score_fetch_sections_result(candidate) > _score_fetch_sections_result(current):
        return candidate
    return current
