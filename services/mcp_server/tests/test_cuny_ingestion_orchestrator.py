"""Unit tests for CUNY ingestion orchestrator."""
from unittest.mock import AsyncMock

import pytest

from mcp_server.services.cuny_ingestion_contract import IngestionSourceResult
from mcp_server.services.cuny_ingestion_orchestrator import CunyIngestionOrchestrator


@pytest.mark.asyncio
async def test_primary_success_without_fallback():
    primary = AsyncMock(
        return_value=IngestionSourceResult(
            success=True,
            source="browser_use",
            courses=[{"course_code": "CSC 101", "sections": [{"section_number": "01"}]}],
        )
    )
    fallback = AsyncMock()
    orchestrator = CunyIngestionOrchestrator(
        primary_fetch=primary,
        fallback_fetch=fallback,
        fallback_enabled=True,
    )

    result = await orchestrator.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="CSC",
    )

    assert result.success is True
    assert result.source == "browser_use"
    assert result.fallback_used is False
    fallback.assert_not_called()


@pytest.mark.asyncio
async def test_primary_failure_fallback_success():
    primary = AsyncMock(
        return_value=IngestionSourceResult(
            success=False,
            source="browser_use",
            courses=[],
            error="primary timeout",
        )
    )
    fallback = AsyncMock(
        return_value=IngestionSourceResult(
            success=True,
            source="selenium",
            courses=[{"course_code": "CSC 101", "sections": []}],
        )
    )
    orchestrator = CunyIngestionOrchestrator(
        primary_fetch=primary,
        fallback_fetch=fallback,
        fallback_enabled=True,
    )

    result = await orchestrator.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="CSC",
    )

    assert result.success is True
    assert result.source == "selenium_fallback"
    assert result.fallback_used is True
    assert any("primary timeout" in warning.lower() for warning in result.warnings)


@pytest.mark.asyncio
async def test_both_fail_returns_degraded_result():
    primary = AsyncMock(
        return_value=IngestionSourceResult(
            success=False,
            source="browser_use",
            courses=[],
            error="primary failed",
        )
    )
    fallback = AsyncMock(
        return_value=IngestionSourceResult(
            success=False,
            source="selenium",
            courses=[],
            error="fallback failed",
        )
    )
    orchestrator = CunyIngestionOrchestrator(
        primary_fetch=primary,
        fallback_fetch=fallback,
        fallback_enabled=True,
    )

    result = await orchestrator.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="CSC",
    )

    assert result.success is False
    assert result.source == "none"
    assert result.fallback_used is True
    assert result.error is not None


@pytest.mark.asyncio
async def test_fallback_disabled_keeps_primary_result():
    primary = AsyncMock(
        return_value=IngestionSourceResult(
            success=False,
            source="browser_use",
            courses=[],
            error="primary failed",
        )
    )
    fallback = AsyncMock()
    orchestrator = CunyIngestionOrchestrator(
        primary_fetch=primary,
        fallback_fetch=fallback,
        fallback_enabled=False,
    )

    result = await orchestrator.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="CSC",
    )

    assert result.success is False
    assert result.source == "browser_use"
    assert result.fallback_used is False
    fallback.assert_not_called()


@pytest.mark.asyncio
async def test_empty_subject_result_with_positive_baseline_triggers_fallback():
    primary = AsyncMock(
        return_value=IngestionSourceResult(
            success=True,
            source="browser_use",
            courses=[],
        )
    )
    fallback = AsyncMock(
        return_value=IngestionSourceResult(
            success=True,
            source="selenium",
            courses=[{"course_code": "CSC 101", "sections": []}],
        )
    )

    async def baseline(*_args, **_kwargs):
        return 10

    orchestrator = CunyIngestionOrchestrator(
        primary_fetch=primary,
        fallback_fetch=fallback,
        fallback_enabled=True,
        baseline_count_provider=baseline,
    )

    result = await orchestrator.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="CSC",
    )

    assert result.success is True
    assert result.source == "selenium_fallback"
    assert result.fallback_used is True


@pytest.mark.asyncio
async def test_empty_subject_result_unknown_baseline_does_not_fallback():
    primary = AsyncMock(
        return_value=IngestionSourceResult(
            success=True,
            source="browser_use",
            courses=[],
        )
    )
    fallback = AsyncMock()

    async def baseline(*_args, **_kwargs):
        return None

    orchestrator = CunyIngestionOrchestrator(
        primary_fetch=primary,
        fallback_fetch=fallback,
        fallback_enabled=True,
        baseline_count_provider=baseline,
    )

    result = await orchestrator.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="CSC",
    )

    assert result.success is True
    assert result.source == "browser_use"
    assert result.fallback_used is False
    assert any("unknown baseline" in warning.lower() for warning in result.warnings)
    fallback.assert_not_called()


@pytest.mark.asyncio
async def test_section_incomplete_subject_result_triggers_fallback():
    primary = AsyncMock(
        return_value=IngestionSourceResult(
            success=True,
            source="browser_use",
            courses=[
                {"course_code": "CSC 126", "sections": []},
                {"course_code": "CSC 220", "sections": []},
            ],
        )
    )
    fallback = AsyncMock(
        return_value=IngestionSourceResult(
            success=True,
            source="selenium",
            courses=[{"course_code": "CSC 126", "sections": [{"section_number": "01"}]}],
        )
    )
    orchestrator = CunyIngestionOrchestrator(
        primary_fetch=primary,
        fallback_fetch=fallback,
        fallback_enabled=True,
    )

    result = await orchestrator.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="CSC",
    )

    assert result.success is True
    assert result.source == "selenium_fallback"
    assert result.fallback_used is True
    assert any("incomplete" in warning.lower() for warning in result.warnings)


@pytest.mark.asyncio
async def test_section_incomplete_unscoped_result_does_not_fallback():
    primary = AsyncMock(
        return_value=IngestionSourceResult(
            success=True,
            source="browser_use",
            courses=[{"course_code": "HIS 101", "sections": []}],
        )
    )
    fallback = AsyncMock()
    orchestrator = CunyIngestionOrchestrator(
        primary_fetch=primary,
        fallback_fetch=fallback,
        fallback_enabled=True,
    )

    result = await orchestrator.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code=None,
    )

    assert result.success is True
    assert result.source == "browser_use"
    fallback.assert_not_called()
