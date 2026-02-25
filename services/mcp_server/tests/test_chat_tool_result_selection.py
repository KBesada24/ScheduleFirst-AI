"""Unit tests for selecting the best fetch_course_sections tool result."""

from mcp_server.utils.chat_tool_result import pick_better_fetch_sections_result


def test_prefers_result_with_courses_over_degraded_empty_followup():
    first = {
        "success": True,
        "data_quality": "full",
        "total_courses": 1,
        "courses": [{"course_code": "CSC 126", "sections": []}],
        "warnings": [],
    }
    second = {
        "success": True,
        "data_quality": "degraded",
        "total_courses": 0,
        "courses": [],
        "warnings": ["Courses not found: CSC126"],
    }

    picked = pick_better_fetch_sections_result(first, second)

    assert picked == first


def test_prefers_new_result_when_it_has_more_courses():
    first = {
        "success": True,
        "data_quality": "partial",
        "total_courses": 1,
        "courses": [{"course_code": "CSC 126", "sections": []}],
        "warnings": ["minor warning"],
    }
    second = {
        "success": True,
        "data_quality": "full",
        "total_courses": 2,
        "courses": [
            {"course_code": "CSC 126", "sections": []},
            {"course_code": "CSC 220", "sections": []},
        ],
        "warnings": [],
    }

    picked = pick_better_fetch_sections_result(first, second)

    assert picked == second
