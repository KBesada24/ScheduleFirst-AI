"""
Unit tests for MCP Tools
Tests fetch_course_sections, generate_optimized_schedule, get_professor_grade,
compare_professors, and check_schedule_conflicts
"""
import pytest
from datetime import datetime, time
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from mcp_server.tools.schedule_optimizer import (
    fetch_course_sections,
    generate_optimized_schedule,
    get_professor_grade,
    compare_professors,
    check_schedule_conflicts,
    _build_response,
    _get_professor_grade_impl,
)
from mcp_server.services.data_population_service import PopulationResult
from mcp_server.utils.exceptions import (
    CircuitBreakerOpenError,
    DatabaseError,
    DataNotFoundError,
)

from conftest import (
    create_mock_course,
    create_mock_section,
    create_mock_professor,
)

# Access underlying functions from FunctionTool wrappers
fetch_course_sections_fn = fetch_course_sections.fn
generate_optimized_schedule_fn = generate_optimized_schedule.fn
get_professor_grade_fn = get_professor_grade.fn
compare_professors_fn = compare_professors.fn
check_schedule_conflicts_fn = check_schedule_conflicts.fn


class TestBuildResponse:
    """Tests for _build_response helper function"""
    
    def test_successful_response(self):
        """Should build successful response with data"""
        response = _build_response(
            success=True,
            data={"courses": ["CSC101", "CSC201"]},
        )
        
        assert response["success"] is True
        assert response["courses"] == ["CSC101", "CSC201"]
        assert response["warnings"] == []
        assert response["data_quality"] == "full"
    
    def test_failed_response_with_error(self):
        """Should build failed response with error details"""
        response = _build_response(
            success=False,
            error="Something went wrong",
            error_code="TEST_ERROR",
            suggestions=["Try again", "Check input"],
        )
        
        assert response["success"] is False
        assert response["error"] == "Something went wrong"
        assert response["error_code"] == "TEST_ERROR"
        assert response["suggestions"] == ["Try again", "Check input"]
    
    def test_response_with_warnings(self):
        """Should include warnings in response"""
        response = _build_response(
            success=True,
            warnings=["Data may be stale", "Some courses not found"],
            data_quality="partial",
        )
        
        assert response["warnings"] == ["Data may be stale", "Some courses not found"]
        assert response["data_quality"] == "partial"


class TestFetchCourseSections:
    """Tests for fetch_course_sections MCP tool"""
    
    @pytest.mark.asyncio
    async def test_returns_sections_for_found_courses(self):
        """Should return sections when courses are found"""
        course = create_mock_course(course_code="CSC101")
        sections = [
            create_mock_section(course_id=course.id, section_number="001"),
            create_mock_section(course_id=course.id, section_number="002"),
        ]
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_course_data = AsyncMock(
                return_value=PopulationResult(success=True)
            )
            mock_supabase.search_courses = AsyncMock(return_value=[course])
            mock_supabase.get_sections_by_course = AsyncMock(return_value=sections)
            
            result = await fetch_course_sections_fn(
                course_codes=["CSC101"],
                semester="Fall 2025"
            )
            
            assert result["success"] is True
            assert result["total_courses"] == 1
            assert len(result["courses"]) == 1
            assert result["courses"][0]["course_code"] == "CSC101"
            assert len(result["courses"][0]["sections"]) == 2
    
    @pytest.mark.asyncio
    async def test_adds_warning_for_courses_not_found(self):
        """Should add warning when some courses not found"""
        course = create_mock_course(course_code="CSC101")
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_course_data = AsyncMock(
                return_value=PopulationResult(success=True)
            )
            # First course found, second not found
            mock_supabase.search_courses = AsyncMock(side_effect=[
                [course],
                []
            ])
            mock_supabase.get_sections_by_course = AsyncMock(return_value=[])
            
            result = await fetch_course_sections_fn(
                course_codes=["CSC101", "MISSING101"],
                semester="Fall 2025"
            )
            
            assert result["success"] is True
            assert any("not found" in w.lower() for w in result["warnings"])
    
    @pytest.mark.asyncio
    async def test_returns_degraded_when_all_courses_not_found(self):
        """Should return degraded data quality when all courses not found"""
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_course_data = AsyncMock(
                return_value=PopulationResult(success=True)
            )
            mock_supabase.search_courses = AsyncMock(return_value=[])
            
            result = await fetch_course_sections_fn(
                course_codes=["MISSING101", "MISSING102"],
                semester="Fall 2025"
            )
            
            assert result["data_quality"] == "degraded"
    
    @pytest.mark.asyncio
    async def test_handles_circuit_breaker_open(self):
        """Should handle CircuitBreakerOpenError gracefully"""
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population:
            mock_population.ensure_course_data = AsyncMock(
                side_effect=CircuitBreakerOpenError(
                    service_name="supabase",
                    retry_after_seconds=60,
                    failure_count=5
                )
            )
            
            result = await fetch_course_sections_fn(
                course_codes=["CSC101"],
                semester="Fall 2025"
            )
            
            assert result["success"] is False
            assert "error_code" in result
    
    @pytest.mark.asyncio
    async def test_handles_database_error(self):
        """Should handle DatabaseError gracefully"""
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population:
            mock_population.ensure_course_data = AsyncMock(
                side_effect=DatabaseError(operation="fetch", reason="timeout")
            )
            
            result = await fetch_course_sections_fn(
                course_codes=["CSC101"],
                semester="Fall 2025"
            )
            
            assert result["success"] is False
    
    @pytest.mark.asyncio
    async def test_includes_metadata_in_response(self):
        """Should include metadata in successful response"""
        course = create_mock_course()
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_course_data = AsyncMock(
                return_value=PopulationResult(success=True)
            )
            mock_supabase.search_courses = AsyncMock(return_value=[course])
            mock_supabase.get_sections_by_course = AsyncMock(return_value=[])
            
            result = await fetch_course_sections_fn(
                course_codes=["CSC101"],
                semester="Fall 2025"
            )
            
            assert "metadata" in result
            assert result["metadata"]["source"] == "hybrid"
            assert result["metadata"]["auto_populated"] is True


class TestGenerateOptimizedSchedule:
    """Tests for generate_optimized_schedule MCP tool"""
    
    @pytest.mark.asyncio
    async def test_generates_schedules_successfully(self):
        """Should generate optimized schedules"""
        mock_schedule = MagicMock()
        mock_schedule.rank = 1
        mock_schedule.total_credits = 12
        mock_schedule.overall_score = 85.0
        mock_schedule.preference_score = 80.0
        mock_schedule.professor_quality_score = 90.0
        mock_schedule.time_convenience_score = 85.0
        mock_schedule.average_professor_rating = 4.2
        mock_schedule.conflicts = []
        mock_schedule.slots = []
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.schedule_optimizer'
        ) as mock_optimizer:
            mock_population.ensure_course_data = AsyncMock(
                return_value=PopulationResult(success=True)
            )
            mock_optimizer.generate_optimized_schedules = AsyncMock(
                return_value=[mock_schedule]
            )
            
            result = await generate_optimized_schedule_fn(
                required_courses=["CSC101", "CSC201"],
                semester="Fall 2025",
                university="Baruch College"
            )
            
            assert result["success"] is True
            assert result["total_schedules"] == 1
    
    @pytest.mark.asyncio
    async def test_adds_warning_when_no_valid_schedules(self):
        """Should add warning when no valid schedules found"""
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.schedule_optimizer'
        ) as mock_optimizer:
            mock_population.ensure_course_data = AsyncMock(
                return_value=PopulationResult(success=True)
            )
            mock_optimizer.generate_optimized_schedules = AsyncMock(return_value=[])
            
            result = await generate_optimized_schedule_fn(
                required_courses=["CSC101"],
                semester="Fall 2025",
                university="Baruch College"
            )
            
            assert result["success"] is True
            assert any("no valid schedules" in w.lower() for w in result["warnings"])
    
    @pytest.mark.asyncio
    async def test_handles_circuit_breaker_open(self):
        """Should handle CircuitBreakerOpenError"""
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population:
            mock_population.ensure_course_data = AsyncMock(
                side_effect=CircuitBreakerOpenError(
                    service_name="supabase",
                    retry_after_seconds=60,
                    failure_count=5
                )
            )
            
            result = await generate_optimized_schedule_fn(
                required_courses=["CSC101"],
                semester="Fall 2025",
                university="Baruch College"
            )
            
            assert result["success"] is False


class TestGetProfessorGrade:
    """Tests for get_professor_grade MCP tool"""
    
    @pytest.mark.asyncio
    async def test_returns_professor_grade_successfully(self):
        """Should return professor grade when data exists"""
        professor = create_mock_professor(
            name="Dr. Smith",
            grade_letter="A",
            composite_score=92
        )
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_professor_data = AsyncMock(
                return_value=PopulationResult(success=True)
            )
            mock_supabase.get_professor_by_name = AsyncMock(return_value=professor)
            
            result = await get_professor_grade_fn(
                professor_name="Dr. Smith",
                university="Baruch College"
            )
            
            assert result["success"] is True
            assert result["professor_name"] == "Dr. Smith"
            assert result["grade_letter"] == "A"
            assert result["composite_score"] == 92
    
    @pytest.mark.asyncio
    async def test_returns_failure_when_population_fails(self):
        """Should return failure when data population fails"""
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population:
            mock_population.ensure_professor_data = AsyncMock(
                return_value=PopulationResult(
                    success=False, 
                    error="Professor not found"
                )
            )
            
            result = await get_professor_grade_fn(
                professor_name="Unknown Prof",
                university="Baruch College"
            )
            
            assert result["success"] is False
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_handles_data_not_found_error(self):
        """Should handle DataNotFoundError gracefully"""
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_professor_data = AsyncMock(
                return_value=PopulationResult(success=True)
            )
            mock_supabase.get_professor_by_name = AsyncMock(
                side_effect=DataNotFoundError(
                    entity_type="Professor",
                    identifier="Unknown"
                )
            )
            
            result = await get_professor_grade_fn(
                professor_name="Unknown",
                university="Baruch College"
            )
            
            assert result["success"] is False
            assert result["error_code"] == "DATA_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_includes_metadata_in_response(self):
        """Should include metadata in successful response"""
        professor = create_mock_professor()
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_professor_data = AsyncMock(
                return_value=PopulationResult(success=True)
            )
            mock_supabase.get_professor_by_name = AsyncMock(return_value=professor)
            
            result = await get_professor_grade_fn(
                professor_name="Dr. Smith",
                university="Baruch College"
            )
            
            assert "metadata" in result
            assert result["metadata"]["source"] == "hybrid"


class TestCompareProfessors:
    """Tests for compare_professors MCP tool"""
    
    @pytest.mark.asyncio
    async def test_compares_multiple_professors(self):
        """Should compare multiple professors and provide recommendation"""
        prof1 = create_mock_professor(
            name="Dr. Smith", grade_letter="A", composite_score=92
        )
        prof2 = create_mock_professor(
            name="Dr. Johnson", grade_letter="B", composite_score=80
        )
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_professor_data = AsyncMock(
                return_value=PopulationResult(success=True)
            )
            mock_supabase.get_professor_by_name = AsyncMock(
                side_effect=[prof1, prof2]
            )
            
            result = await compare_professors_fn(
                professor_names=["Dr. Smith", "Dr. Johnson"],
                university="Baruch College"
            )
            
            assert result["success"] is True
            assert result["total_professors"] == 2
            assert "recommendation" in result
            assert "Dr. Smith" in result["recommendation"]  # Higher grade
    
    @pytest.mark.asyncio
    async def test_handles_partial_data_availability(self):
        """Should handle when some professors not found"""
        prof1 = create_mock_professor(name="Dr. Smith")
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            # First professor found, second fails
            mock_population.ensure_professor_data = AsyncMock(
                side_effect=[
                    PopulationResult(success=True),
                    PopulationResult(success=False, error="Not found")
                ]
            )
            mock_supabase.get_professor_by_name = AsyncMock(return_value=prof1)
            
            result = await compare_professors_fn(
                professor_names=["Dr. Smith", "Dr. Unknown"],
                university="Baruch College"
            )
            
            assert result["success"] is True
            assert result["total_professors"] == 1
            assert any("could not fetch" in w.lower() for w in result["warnings"])
    
    @pytest.mark.asyncio
    async def test_returns_failure_when_no_data_available(self):
        """Should return failure when no professor data retrieved"""
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population:
            mock_population.ensure_professor_data = AsyncMock(
                return_value=PopulationResult(success=False, error="Not found")
            )
            
            result = await compare_professors_fn(
                professor_names=["Unknown1", "Unknown2"],
                university="Baruch College"
            )
            
            assert result["success"] is False
            assert result["error_code"] == "DATA_NOT_FOUND"


class TestCheckScheduleConflicts:
    """Tests for check_schedule_conflicts MCP tool"""
    
    @pytest.mark.asyncio
    async def test_detects_no_conflicts(self):
        """Should return no conflicts when sections don't overlap"""
        section1 = create_mock_section(
            days="MWF",
            start_time=time(9, 0),
            end_time=time(9, 50)
        )
        section2 = create_mock_section(
            days="MWF",
            start_time=time(10, 0),
            end_time=time(10, 50)
        )
        
        with patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase, patch(
            'mcp_server.tools.schedule_optimizer.schedule_optimizer'
        ) as mock_optimizer:
            mock_supabase.get_section_by_id = AsyncMock(
                side_effect=[section1, section2]
            )
            mock_optimizer.detect_conflicts.return_value = []
            
            result = await check_schedule_conflicts_fn(
                section_ids=[str(uuid4()), str(uuid4())]
            )
            
            assert result["success"] is True
            assert result["total_conflicts"] == 0
    
    @pytest.mark.asyncio
    async def test_detects_time_conflicts(self):
        """Should detect overlapping time conflicts"""
        section1 = create_mock_section(
            days="MWF",
            start_time=time(9, 0),
            end_time=time(10, 0)
        )
        section2 = create_mock_section(
            days="MWF",
            start_time=time(9, 30),
            end_time=time(10, 30)
        )
        
        mock_conflict = MagicMock()
        mock_conflict.conflict_type = "time_overlap"
        mock_conflict.severity = "high"
        mock_conflict.description = "Classes overlap on MWF"
        mock_conflict.suggestion = "Choose different sections"
        
        with patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase, patch(
            'mcp_server.tools.schedule_optimizer.schedule_optimizer'
        ) as mock_optimizer:
            mock_supabase.get_section_by_id = AsyncMock(
                side_effect=[section1, section2]
            )
            mock_optimizer.detect_conflicts.return_value = [mock_conflict]
            
            result = await check_schedule_conflicts_fn(
                section_ids=[str(uuid4()), str(uuid4())]
            )
            
            assert result["success"] is True
            assert result["total_conflicts"] == 1
            assert result["conflicts"][0]["type"] == "time_overlap"
    
    @pytest.mark.asyncio
    async def test_handles_missing_sections(self):
        """Should handle when some sections not found"""
        section1 = create_mock_section()
        
        with patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase, patch(
            'mcp_server.tools.schedule_optimizer.schedule_optimizer'
        ) as mock_optimizer:
            mock_supabase.get_section_by_id = AsyncMock(
                side_effect=[section1, DataNotFoundError("Section", "id")]
            )
            mock_optimizer.detect_conflicts.return_value = []
            
            result = await check_schedule_conflicts_fn(
                section_ids=[str(uuid4()), str(uuid4())]
            )
            
            assert result["success"] is True
            assert any("not found" in w.lower() for w in result["warnings"])
    
    @pytest.mark.asyncio
    async def test_returns_failure_when_no_valid_sections(self):
        """Should return failure when no valid sections found"""
        with patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_section_by_id = AsyncMock(
                side_effect=DataNotFoundError("Section", "id")
            )
            
            result = await check_schedule_conflicts_fn(
                section_ids=[str(uuid4())]
            )
            
            assert result["success"] is False
            assert result["error_code"] == "DATA_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_handles_circuit_breaker_open(self):
        """Should handle CircuitBreakerOpenError"""
        with patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_supabase.get_section_by_id = AsyncMock(
                side_effect=CircuitBreakerOpenError(
                    service_name="supabase",
                    retry_after_seconds=60,
                    failure_count=5
                )
            )
            
            result = await check_schedule_conflicts_fn(
                section_ids=[str(uuid4())]
            )
            
            assert result["success"] is False


class TestMCPToolsDataQuality:
    """Tests for data quality indicators in MCP tool responses"""
    
    @pytest.mark.asyncio
    async def test_fetch_sections_indicates_partial_on_population_warnings(self):
        """Should indicate partial data quality when population has warnings"""
        course = create_mock_course()
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_course_data = AsyncMock(
                return_value=PopulationResult(
                    success=True,
                    warnings=["Some data may be stale"],
                    is_partial=True
                )
            )
            mock_supabase.search_courses = AsyncMock(return_value=[course])
            mock_supabase.get_sections_by_course = AsyncMock(return_value=[])
            
            result = await fetch_course_sections_fn(
                course_codes=["CSC101"],
                semester="Fall 2025"
            )
            
            assert result["data_quality"] == "partial"
            assert "Some data may be stale" in result["warnings"]
    
    @pytest.mark.asyncio
    async def test_get_professor_grade_includes_warnings(self):
        """Should include population warnings in professor grade response"""
        professor = create_mock_professor()
        
        with patch(
            'mcp_server.tools.schedule_optimizer.data_population_service'
        ) as mock_population, patch(
            'mcp_server.tools.schedule_optimizer.supabase_service'
        ) as mock_supabase:
            mock_population.ensure_professor_data = AsyncMock(
                return_value=PopulationResult(
                    success=True,
                    warnings=["Could not fetch latest reviews"],
                    is_partial=True
                )
            )
            mock_supabase.get_professor_by_name = AsyncMock(return_value=professor)
            
            result = await get_professor_grade_fn(
                professor_name="Dr. Smith",
                university="Baruch College"
            )
            
            assert result["success"] is True
            assert result["data_quality"] == "partial"
            assert "Could not fetch latest reviews" in result["warnings"]
