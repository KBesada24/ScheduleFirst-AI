"""Primary/fallback orchestration for CUNY ingestion."""
from __future__ import annotations

from typing import Awaitable, Callable, List, Optional

from ..config import settings
from ..utils.logger import get_logger
from .browser_use_cuny_connector import BrowserUseCunyConnector
from .cuny_global_search_scraper import cuny_scraper
from .cuny_ingestion_contract import IngestionSourceResult


logger = get_logger(__name__)

FetchCoursesFn = Callable[[str, Optional[str], Optional[str]], Awaitable[IngestionSourceResult]]
BaselineCountFn = Callable[[str, str, str], Awaitable[Optional[int]]]


class CunyIngestionOrchestrator:
    def __init__(
        self,
        primary_fetch: Optional[FetchCoursesFn] = None,
        fallback_fetch: Optional[FetchCoursesFn] = None,
        fallback_enabled: Optional[bool] = None,
        browser_use_enabled: Optional[bool] = None,
        shadow_mode: Optional[bool] = None,
        baseline_count_provider: Optional[BaselineCountFn] = None,
    ):
        connector = BrowserUseCunyConnector(
            timeout_seconds=settings.cuny_browser_use_timeout,
            max_retries=settings.cuny_browser_use_max_retries,
        )
        self._primary_fetch = primary_fetch or connector.fetch_courses
        self._fallback_fetch = fallback_fetch or self._fetch_with_selenium
        self._fallback_enabled = (
            settings.cuny_selenium_fallback_enabled
            if fallback_enabled is None
            else fallback_enabled
        )
        if browser_use_enabled is None:
            self._browser_use_enabled = True if primary_fetch is not None else settings.cuny_browser_use_enabled
        else:
            self._browser_use_enabled = browser_use_enabled
        self._shadow_mode = settings.cuny_shadow_mode if shadow_mode is None else shadow_mode
        self._baseline_count_provider = baseline_count_provider

    async def fetch_courses(
        self,
        semester: str,
        university: Optional[str] = None,
        subject_code: Optional[str] = None,
    ) -> IngestionSourceResult:
        logger.info(
            "Starting CUNY ingestion orchestration",
            extra={"semester": semester, "university": university, "subject_code": subject_code},
        )

        if not self._browser_use_enabled:
            return await self._selenium_only(semester, university, subject_code)

        primary = await self._primary_fetch(semester, university, subject_code)
        logger.info(
            "Primary ingestion result",
            extra={
                "source": primary.source,
                "success": primary.success,
                "courses_count": len(primary.courses),
                "warnings_count": len(primary.warnings),
                "error": primary.error,
            },
        )
        should_fallback, reason = await self._should_trigger_fallback(
            primary,
            semester=semester,
            university=university,
            subject_code=subject_code,
        )
        logger.info(
            "Fallback decision computed",
            extra={
                "should_fallback": should_fallback,
                "reason": reason,
                "fallback_enabled": self._fallback_enabled,
                "shadow_mode": self._shadow_mode,
            },
        )

        if self._shadow_mode and not should_fallback and self._fallback_enabled:
            await self._run_shadow_compare(semester, university, subject_code)

        if not should_fallback:
            return primary

        if not self._fallback_enabled:
            return primary

        fallback = await self._fallback_fetch(semester, university, subject_code)
        logger.info(
            "Fallback ingestion result",
            extra={
                "source": fallback.source,
                "success": fallback.success,
                "courses_count": len(fallback.courses),
                "warnings_count": len(fallback.warnings),
                "error": fallback.error,
            },
        )
        if fallback.success:
            warnings = list(primary.warnings)
            if primary.error:
                warnings.append(f"Primary source failed: {primary.error}")
            if reason:
                warnings.append(reason)
            return IngestionSourceResult(
                success=True,
                source="selenium_fallback",
                courses=fallback.courses,
                warnings=warnings,
                fallback_used=True,
            )

        combined_error = "; ".join(
            [
                part
                for part in [
                    f"browser_use: {primary.error}" if primary.error else None,
                    f"selenium: {fallback.error}" if fallback.error else None,
                ]
                if part
            ]
        ) or "Both Browser-Use and Selenium ingestion failed"

        warnings = list(primary.warnings) + list(fallback.warnings)
        if reason:
            warnings.append(reason)

        return IngestionSourceResult(
            success=False,
            source="none",
            courses=[],
            warnings=warnings,
            error=combined_error,
            fallback_used=True,
        )

    async def _selenium_only(
        self,
        semester: str,
        university: Optional[str],
        subject_code: Optional[str],
    ) -> IngestionSourceResult:
        if not self._fallback_enabled:
            return IngestionSourceResult(
                success=False,
                source="none",
                courses=[],
                error="No ingestion source enabled",
            )

        selenium_result = await self._fallback_fetch(semester, university, subject_code)
        if selenium_result.success:
            return IngestionSourceResult(
                success=True,
                source="selenium_fallback",
                courses=selenium_result.courses,
                warnings=selenium_result.warnings,
                fallback_used=True,
            )

        return IngestionSourceResult(
            success=False,
            source="none",
            courses=[],
            warnings=selenium_result.warnings,
            error=selenium_result.error,
            fallback_used=True,
        )

    async def _should_trigger_fallback(
        self,
        primary: IngestionSourceResult,
        semester: str,
        university: Optional[str],
        subject_code: Optional[str],
    ) -> tuple[bool, Optional[str]]:
        if not primary.success:
            logger.info(
                "Fallback trigger: primary reported unsuccessful",
                extra={"primary_error": primary.error, "primary_source": primary.source},
            )
            return True, "Primary Browser-Use ingestion was unsuccessful"

        if primary.courses and subject_code:
            section_counts: List[int] = []
            for course in primary.courses:
                if not isinstance(course, dict):
                    continue
                sections = course.get("sections")
                if isinstance(sections, list):
                    section_counts.append(len(sections))

            if section_counts and sum(section_counts) == 0:
                warning = (
                    "Fallback triggered: Browser-Use returned courses but no sections, "
                    "indicating incomplete extraction"
                )
                primary.warnings.append(warning)
                logger.info(
                    "Fallback triggered: section-incomplete Browser-Use result",
                    extra={
                        "courses_count": len(primary.courses),
                        "subject_code": subject_code,
                        "semester": semester,
                        "university": university,
                    },
                )
                return True, warning

        if primary.courses:
            return False, None

        if not subject_code:
            logger.info("Fallback not triggered: request is not subject-scoped")
            return False, None

        if not university or not self._baseline_count_provider:
            warning = "Accepted empty Browser-Use subject result due to unknown baseline"
            primary.warnings.append(warning)
            logger.info(
                "Fallback not triggered: baseline provider unavailable",
                extra={"university": university, "has_baseline_provider": bool(self._baseline_count_provider)},
            )
            return False, warning

        baseline = await self._baseline_count_provider(semester, university, subject_code)
        if baseline is None:
            warning = "Accepted empty Browser-Use subject result due to unknown baseline"
            primary.warnings.append(warning)
            logger.info(
                "Fallback not triggered: baseline returned unknown",
                extra={"semester": semester, "university": university, "subject_code": subject_code},
            )
            return False, warning

        if baseline > 0:
            logger.info(
                "Fallback triggered: baseline indicates expected data",
                extra={"baseline": baseline, "subject_code": subject_code},
            )
            return True, "Fallback triggered: empty Browser-Use result conflicts with positive baseline"

        logger.info(
            "Fallback not triggered: baseline indicates no expected data",
            extra={"baseline": baseline, "subject_code": subject_code},
        )
        return False, None

    async def _run_shadow_compare(
        self,
        semester: str,
        university: Optional[str],
        subject_code: Optional[str],
    ) -> None:
        try:
            await self._fallback_fetch(semester, university, subject_code)
        except Exception as exc:  # pragma: no cover - best effort only
            logger.debug(f"Shadow mode fallback comparison failed: {exc}")

    async def _fetch_with_selenium(
        self,
        semester: str,
        university: Optional[str] = None,
        subject_code: Optional[str] = None,
    ) -> IngestionSourceResult:
        try:
            courses = await cuny_scraper.scrape_semester_courses(
                semester=semester,
                university=university,
                subject_code=subject_code,
            )
            return IngestionSourceResult(
                success=True,
                source="selenium",
                courses=courses,
            )
        except Exception as exc:
            return IngestionSourceResult(
                success=False,
                source="selenium",
                courses=[],
                error=str(exc),
            )

    def close(self) -> None:
        cuny_scraper.close()


cuny_ingestion_orchestrator = CunyIngestionOrchestrator()
