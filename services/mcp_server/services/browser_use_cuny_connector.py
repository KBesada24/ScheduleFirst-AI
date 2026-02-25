"""Browser-Use primary connector for CUNY Global Search ingestion."""
import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings
from ..utils.logger import get_logger
from .cuny_ingestion_contract import IngestionSourceResult


logger = get_logger(__name__)


SEARCH_URL = "https://globalsearch.cuny.edu/CFGlobalSearchTool/search.jsp"
BROWSER_USE_TASKS_URL = "https://api.browser-use.com/api/v2/tasks"
BROWSER_USE_TASK_LOGS_URL = "https://api.browser-use.com/api/v2/tasks/{task_id}/logs"


class BrowserUseCunyConnector:
    """Fetches CUNY courses using Browser-Use as the primary automation runtime."""

    def __init__(
        self,
        timeout_seconds: int = 45,
        max_retries: int = 1,
    ):
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.cloud_api_key = getattr(settings, "browser_use_api_key", None) or os.getenv("BROWSER_USE_API_KEY")

    async def fetch_courses(
        self,
        semester: str,
        university: Optional[str] = None,
        subject_code: Optional[str] = None,
    ) -> IngestionSourceResult:
        warnings: List[str] = []
        last_error: Optional[str] = None

        for attempt in range(self.max_retries + 1):
            try:
                courses = await asyncio.wait_for(
                    self._fetch_once(
                        semester=semester,
                        university=university,
                        subject_code=subject_code,
                    ),
                    timeout=self.timeout_seconds,
                )

                if not courses:
                    if subject_code:
                        warnings.append(
                            f"No course results returned for requested subject '{subject_code}'."
                        )
                    else:
                        warnings.append("Browser-Use returned an empty result set.")

                if courses and all(not course.get("sections") for course in courses if isinstance(course, dict)):
                    warnings.append(
                        "Browser-Use returned courses but zero sections; extraction may be incomplete."
                    )

                total_courses = len(courses)
                total_sections = 0
                zero_section_courses = 0
                for course in courses:
                    if not isinstance(course, dict):
                        continue
                    sections = course.get("sections")
                    if isinstance(sections, list):
                        section_count = len(sections)
                    else:
                        section_count = 0
                    total_sections += section_count
                    if section_count == 0:
                        zero_section_courses += 1

                logger.info(
                    "Browser-Use extraction quality summary",
                    extra={
                        "total_courses": total_courses,
                        "total_sections": total_sections,
                        "zero_section_courses": zero_section_courses,
                        "semester": semester,
                        "university": university,
                        "subject_code": subject_code,
                    },
                )

                return IngestionSourceResult(
                    success=True,
                    source="browser_use",
                    courses=courses,
                    warnings=warnings,
                )

            except (asyncio.TimeoutError, TimeoutError) as exc:
                last_error = str(exc) or "timed out"
                warnings.append(f"Browser-Use attempt {attempt + 1} timed out")
                logger.warning(
                    "Browser-Use ingestion timeout",
                    extra={
                        "attempt": attempt + 1,
                        "semester": semester,
                        "university": university,
                        "failure_classification": "timeout",
                    },
                )
            except Exception as exc:  # pragma: no cover - defensive guardrail
                last_error = str(exc)
                warnings.append(f"Browser-Use attempt {attempt + 1} failed")
                failure_classification = self._classify_failure(str(exc))
                logger.warning(
                    "Browser-Use ingestion failure",
                    extra={
                        "attempt": attempt + 1,
                        "error": str(exc),
                        "failure_classification": failure_classification,
                    },
                )

        return IngestionSourceResult(
            success=False,
            source="browser_use",
            courses=[],
            warnings=warnings,
            error=last_error or "Browser-Use ingestion failed",
        )

    async def _fetch_once(
        self,
        semester: str,
        university: Optional[str] = None,
        subject_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        prompt = self._build_task_prompt(semester, university, subject_code)

        if self.cloud_api_key:
            raw = await self._run_browser_use_cloud_workflow(prompt)
        else:
            raw = await self._run_browser_use_local_workflow(prompt)

        return self._normalize_courses(raw)

    def _build_task_prompt(
        self,
        semester: str,
        university: Optional[str],
        subject_code: Optional[str],
    ) -> str:
        return (
            "Use CUNY Global Search to extract all matching courses and all visible sections. "
            "Follow this sequence: apply filters, run search, expand each course row, and extract each section row. "
            f"Start URL: {SEARCH_URL}. Semester: {semester}. "
            f"University: {university or 'all universities'}. Subject: {subject_code or 'all subjects'}. "
            "Do not finish after finding only course codes. Include section-level records when present. "
            "Return only JSON that matches the required schema."
        )

    async def _run_browser_use_cloud_workflow(self, prompt: str) -> Any:
        headers = {
            "X-Browser-Use-API-Key": str(self.cloud_api_key),
            "Content-Type": "application/json",
        }
        payload = {
            "task": prompt,
            "llm": settings.cuny_browser_use_llm,
            "startUrl": SEARCH_URL,
            "allowedDomains": ["globalsearch.cuny.edu"],
            "maxSteps": settings.cuny_browser_use_max_steps,
            "vision": "auto",
            "structuredOutput": json.dumps(self._structured_output_schema()),
        }

        timeout = httpx.Timeout(self.timeout_seconds + 15)
        async with httpx.AsyncClient(timeout=timeout) as client:
            create_response = await client.post(BROWSER_USE_TASKS_URL, headers=headers, json=payload)
            create_response.raise_for_status()

            task_data = create_response.json()
            task_id = task_data.get("id")
            if not task_id:
                raise RuntimeError("Browser-Use cloud task did not return an id")

            logger.info("Browser-Use cloud task created", extra={"task_id": task_id})
            completed_task = await self._poll_task_completion(client, headers, task_id)

            terminal_status = completed_task.get("status")
            if terminal_status != "finished":
                log_download_url = await self._get_task_logs_download_url(client, headers, task_id)
                error_text = f"Browser-Use cloud task ended with status '{terminal_status}'"
                if log_download_url:
                    error_text = f"{error_text}; logs={log_download_url}"
                raise RuntimeError(error_text)

            output = completed_task.get("output")
            if output is not None:
                return output

            detailed_task = await self._fetch_task_details(client, headers, task_id)
            return detailed_task.get("output")

    async def _poll_task_completion(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str],
        task_id: str,
    ) -> Dict[str, Any]:
        poll_interval = max(1, int(settings.cuny_browser_use_poll_interval))
        elapsed = 0

        while elapsed <= self.timeout_seconds:
            task_details = await self._fetch_task_details(client, headers, task_id)
            status = task_details.get("status")

            if status in {"finished", "stopped"}:
                return task_details

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError("Browser-Use cloud task polling timed out")

    async def _fetch_task_details(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str],
        task_id: str,
    ) -> Dict[str, Any]:
        response = await client.get(f"{BROWSER_USE_TASKS_URL}/{task_id}", headers=headers)
        response.raise_for_status()
        return response.json()

    async def _get_task_logs_download_url(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str],
        task_id: str,
    ) -> Optional[str]:
        try:
            logs_url = BROWSER_USE_TASK_LOGS_URL.format(task_id=task_id)
            response = await client.get(logs_url, headers=headers)
            response.raise_for_status()
            payload = response.json()
            return payload.get("downloadUrl")
        except Exception:
            return None

    async def _run_browser_use_local_workflow(self, prompt: str) -> Any:
        try:
            from browser_use import Agent, Browser  # type: ignore
        except ImportError as exc:
            raise RuntimeError("browser-use dependency is not installed") from exc

        browser = Browser(headless=True)
        agent = Agent(task=prompt, browser=browser)
        result = await agent.run()

        if hasattr(browser, "close"):
            maybe_close = browser.close()
            if asyncio.iscoroutine(maybe_close):
                await maybe_close

        return result

    def _structured_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "courses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "course_code": {"type": "string"},
                            "title": {"type": "string"},
                            "college": {"type": "string"},
                            "term": {"type": "string"},
                            "sections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "section_number": {"type": "string"},
                                        "class_number": {"type": "string"},
                                        "instruction_mode": {"type": "string"},
                                        "professor": {"type": "string"},
                                        "days": {"type": "string"},
                                        "time": {"type": "string"},
                                        "location": {"type": "string"},
                                        "status": {"type": "string"},
                                    },
                                },
                            },
                        },
                        "required": ["course_code", "sections"],
                    },
                }
            },
            "required": ["courses"],
        }

    def _normalize_courses(self, raw_result: Any) -> List[Dict[str, Any]]:
        if raw_result is None:
            return []

        if isinstance(raw_result, list):
            normalized = [course for course in raw_result if isinstance(course, dict)]
            return [self._normalize_course_shape(course) for course in normalized]

        if isinstance(raw_result, dict):
            courses = raw_result.get("courses", [])
            if isinstance(courses, list):
                normalized = [course for course in courses if isinstance(course, dict)]
                return [self._normalize_course_shape(course) for course in normalized]
            return []

        if isinstance(raw_result, str):
            parsed = self._try_parse_json_from_string(raw_result)
            if parsed is None:
                return []
            return self._normalize_courses(parsed)

        return []

    def _normalize_course_shape(self, course: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(course)
        sections = normalized.get("sections")
        if not isinstance(sections, list):
            normalized["sections"] = []
            return normalized

        normalized["sections"] = [section for section in sections if isinstance(section, dict)]
        return normalized

    def _try_parse_json_from_string(self, text: str) -> Optional[Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        fenced = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except json.JSONDecodeError:
                return None

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return None

        return None

    def _classify_failure(self, error_message: str) -> str:
        message = error_message.lower()

        if "timed out" in message or "timeout" in message:
            return "timeout"
        if "status 'stopped'" in message:
            return "navigation"
        if "json" in message or "parse" in message:
            return "parse"
        if "subject" in message or "filter" in message:
            return "filter_mismatch"
        if "section" in message:
            return "expansion"
        return "navigation"
