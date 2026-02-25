"""Unit tests for BrowserUse CUNY connector."""
from unittest.mock import AsyncMock

import pytest

from mcp_server.services.browser_use_cuny_connector import BrowserUseCunyConnector


@pytest.mark.asyncio
async def test_connector_success_path_returns_contract_result():
    connector = BrowserUseCunyConnector(timeout_seconds=1, max_retries=0)
    expected_courses = [{"course_code": "CSC 101", "sections": []}]
    connector._fetch_once = AsyncMock(return_value=expected_courses)

    result = await connector.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="CSC",
    )

    assert result.success is True
    assert result.source == "browser_use"
    assert result.courses == expected_courses
    assert result.error is None


@pytest.mark.asyncio
async def test_connector_timeout_path_returns_unsuccessful_result():
    connector = BrowserUseCunyConnector(timeout_seconds=1, max_retries=0)
    connector._fetch_once = AsyncMock(side_effect=TimeoutError("timed out"))

    result = await connector.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="CSC",
    )

    assert result.success is False
    assert result.source == "browser_use"
    assert result.error is not None
    assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_connector_subject_no_match_returns_warning():
    connector = BrowserUseCunyConnector(timeout_seconds=1, max_retries=0)
    connector._fetch_once = AsyncMock(return_value=[])

    result = await connector.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="ZZZ",
    )

    assert result.success is True
    assert result.courses == []
    assert any("subject" in warning.lower() for warning in result.warnings)


@pytest.mark.asyncio
async def test_connector_empty_result_without_subject_adds_warning():
    connector = BrowserUseCunyConnector(timeout_seconds=1, max_retries=0)
    connector._fetch_once = AsyncMock(return_value=[])

    result = await connector.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
    )

    assert result.success is True
    assert result.courses == []
    assert any("empty" in warning.lower() for warning in result.warnings)


@pytest.mark.asyncio
async def test_fetch_once_uses_cloud_when_api_key_present():
    connector = BrowserUseCunyConnector(timeout_seconds=1, max_retries=0)
    connector.cloud_api_key = "test-key"
    connector._run_browser_use_cloud_workflow = AsyncMock(
        return_value={"courses": [{"course_code": "CSC 126", "sections": [{"section_number": "01"}]}]}
    )
    connector._run_browser_use_local_workflow = AsyncMock(return_value=[])

    courses = await connector._fetch_once(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="CSC",
    )

    assert len(courses) == 1
    connector._run_browser_use_cloud_workflow.assert_awaited_once()
    connector._run_browser_use_local_workflow.assert_not_called()


def test_normalize_parses_fenced_json_response():
    connector = BrowserUseCunyConnector(timeout_seconds=1, max_retries=0)
    raw_result = """```json
    {"courses":[{"course_code":"CSC 126","sections":[{"section_number":"01"}]}]}
    ```"""

    normalized = connector._normalize_courses(raw_result)

    assert len(normalized) == 1
    assert normalized[0]["course_code"] == "CSC 126"
    assert len(normalized[0]["sections"]) == 1


@pytest.mark.asyncio
async def test_connector_warns_when_courses_have_zero_sections():
    connector = BrowserUseCunyConnector(timeout_seconds=1, max_retries=0)
    connector._fetch_once = AsyncMock(return_value=[{"course_code": "CSC 126", "sections": []}])

    result = await connector.fetch_courses(
        semester="Spring 2026",
        university="College of Staten Island",
        subject_code="CSC",
    )

    assert result.success is True
    assert any("zero sections" in warning.lower() for warning in result.warnings)
