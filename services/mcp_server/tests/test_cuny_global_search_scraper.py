import pytest
from unittest.mock import AsyncMock
from bs4 import BeautifulSoup
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import NoSuchElementException

from mcp_server.services.cuny_global_search_scraper import CUNYGlobalSearchScraper


class TestCourseHeaderExtraction:
    def test_extracts_course_name_from_preceding_div_header(self):
        html = """
        <html>
          <body>
            <div class="course-header">ACC 100 - Introduction to Accounting</div>
            <table class="classinfo">
              <tr><th>CLASS</th></tr>
              <tr><td>10234</td><td>D001</td><td>TuTh 04:40PM - 06:20PM</td><td>2M 203</td><td>Yaqing Zhang</td></tr>
            </table>
          </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_="classinfo")

        scraper = CUNYGlobalSearchScraper()
        extracted = scraper._extract_course_name_from_context(table, soup)

        assert extracted is not None
        assert "ACC 100" in extracted


class TestBackNavigation:
    def test_uses_modify_search_criteria_input_without_browser_back(self):
        scraper = CUNYGlobalSearchScraper()

        mock_driver = MagicMock()
        mock_button = MagicMock()

        # Existing selectors fail until the more flexible selector is tried.
        def find_element_side_effect(by, selector):
            if "contains(@value, 'Modify Search')" in selector:
                return mock_button
            raise NoSuchElementException("not found")

        mock_driver.find_element.side_effect = find_element_side_effect
        scraper.driver = mock_driver

        with patch("mcp_server.services.cuny_global_search_scraper.WebDriverWait") as wait_cls:
            wait_instance = MagicMock()
            wait_instance.until.return_value = True
            wait_cls.return_value = wait_instance

            scraper._navigate_back_to_step2()

        mock_button.click.assert_called_once()
        mock_driver.back.assert_not_called()

    def test_uses_cuny_search_criteria_css_selector(self):
        scraper = CUNYGlobalSearchScraper()

        mock_driver = MagicMock()
        mock_button = MagicMock()

        def find_element_side_effect(by, selector):
            if by == "css selector" and selector == "a#searchlink":
                return mock_button
            raise NoSuchElementException("not found")

        mock_driver.find_element.side_effect = find_element_side_effect
        scraper.driver = mock_driver

        with patch("mcp_server.services.cuny_global_search_scraper.WebDriverWait") as wait_cls:
            wait_instance = MagicMock()
            wait_instance.until.return_value = True
            wait_cls.return_value = wait_instance

            scraper._navigate_back_to_step2()

        mock_button.click.assert_called_once()
        mock_driver.back.assert_not_called()


class TestSubjectFiltering:
    @pytest.mark.asyncio
    async def test_scrape_semester_courses_forwards_subject_code(self):
        scraper = CUNYGlobalSearchScraper()

        with patch.object(scraper, "_get_cuny_schools", return_value=[{"name": "College of Staten Island"}]):
            scraper._scrape_school_courses = AsyncMock(return_value=[])

            await scraper.scrape_semester_courses(
                semester="Spring 2026",
                university="College of Staten Island",
                subject_code="CSC",
            )

            scraper._scrape_school_courses.assert_awaited_once_with(
                school_name="College of Staten Island",
                semester="Spring 2026",
                subject_code="CSC",
            )
