import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from services.api_server import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_get_courses_auto_populate():
    """Test GET /api/courses with auto_populate=True"""
    with patch('services.api_server.supabase_service') as mock_supabase, \
         patch('services.api_server.data_population_service') as mock_pop, \
         patch('services.api_server.data_freshness_service') as mock_fresh:
        
        # Setup mocks
        mock_pop.ensure_course_data = AsyncMock(return_value=True)
        
        # Mock course object
        mock_course = MagicMock()
        mock_course.model_dump.return_value = {"course_code": "CSC101", "name": "Intro to CS"}
        
        mock_supabase.get_courses_by_semester = AsyncMock(return_value=[mock_course])
        mock_fresh.is_course_data_fresh = AsyncMock(return_value=True)
        mock_fresh.get_last_sync = AsyncMock(return_value=None)
        
        # Execute
        response = client.get("/api/courses?semester=Fall 2025&auto_populate=true")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "data" in data
        assert "metadata" in data
        assert "courses" in data["data"]
        
        # Check metadata
        assert data["metadata"]["auto_populated"] is True
        assert data["metadata"]["is_fresh"] is True
        
        # Verify population triggered
        mock_pop.ensure_course_data.assert_called_once()

@pytest.mark.asyncio
async def test_get_professor_auto_populate():
    """Test GET /api/professor/{name} with auto_populate=True"""
    with patch('services.api_server.supabase_service') as mock_supabase, \
         patch('services.api_server.data_population_service') as mock_pop, \
         patch('services.api_server.data_freshness_service') as mock_fresh:
        
        # Setup mocks
        mock_pop.ensure_professor_data = AsyncMock(return_value=True)
        
        mock_prof = MagicMock()
        mock_prof.id = "123"
        mock_prof.model_dump.return_value = {"name": "Test Prof", "university": "Baruch College"}
        mock_prof.last_updated = None
        
        mock_supabase.get_professor_by_name = AsyncMock(return_value=mock_prof)
        mock_supabase.get_reviews_by_professor = AsyncMock(return_value=[])
        mock_fresh.is_professor_data_fresh = AsyncMock(return_value=True)
        
        # Execute
        response = client.get("/api/professor/Test Prof?auto_populate=true")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["professor"]["name"] == "Test Prof"
        assert data["metadata"]["auto_populated"] is True
        
        mock_pop.ensure_professor_data.assert_called_once()

@pytest.mark.asyncio
async def test_compare_professors_endpoint():
    """Test POST /api/professor/compare"""
    with patch('services.api_server.compare_professors') as mock_compare:
        
        # Setup mock
        mock_compare.return_value = {
            "success": True,
            "professors": [],
            "recommendation": "Prof A is better"
        }
        
        # Execute
        response = client.post("/api/professor/compare", json={
            "professor_names": ["Prof A", "Prof B"],
            "university": "Baruch College"
        })
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["success"] is True
        assert data["metadata"]["source"] == "hybrid"
        
        mock_compare.assert_called_once()
