# Backend REST API Documentation

Complete reference for the CUNY Schedule Optimizer backend REST API.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.schedulefirst.ai` (example)

## Authentication

Currently, the API is unauthenticated. Future versions will require JWT tokens from Supabase Auth.

## Response Format

All endpoints return responses in the following format:

```json
{
  "data": { ... },
  "metadata": {
    "source": "hybrid|database|cache|scraper",
    "last_updated": "2025-12-03T00:00:00Z",
    "is_fresh": true,
    "auto_populated": false,
    "count": 10
  }
}
```

### Error Response Format

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "suggestions": ["Suggestion 1", "Suggestion 2"]
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `DATA_NOT_FOUND` | 404 | Requested entity not found |
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `CIRCUIT_BREAKER_OPEN` | 503 | External service temporarily unavailable |
| `DATABASE_ERROR` | 503/500 | Database operation failed |
| `SCRAPING_ERROR` | 502 | Web scraping failed |
| `EXTERNAL_SERVICE_ERROR` | 502 | External service call failed |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## Endpoints

### Health & Status

#### GET /health

Check service health status.

**Response**:
```json
{
  "status": "healthy|degraded|unhealthy",
  "database": "connected|disconnected",
  "environment": "production|development",
  "gemini_api": "configured|not configured",
  "circuit_breakers": {
    "ratemyprof": "closed|open|half_open",
    "cuny_scraper": "closed|open|half_open",
    "supabase": "closed|open|half_open",
    "gemini": "closed|open|half_open"
  }
}
```

---

### Courses

#### GET /api/courses

Get all courses for a semester.

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `semester` | string | Yes | - | Semester (e.g., "Spring 2025") |
| `university` | string | No | "Baruch College" | CUNY school name |
| `auto_populate` | boolean | No | true | Auto-fetch if data missing/stale |

**Example**:
```bash
curl "http://localhost:8000/api/courses?semester=Spring%202025&university=Baruch%20College"
```

**Response**:
```json
{
  "data": {
    "courses": [
      {
        "id": "uuid",
        "course_code": "CSC 101",
        "name": "Introduction to Computing",
        "credits": 3,
        "department": "Computer Science",
        "university": "Baruch College",
        "semester": "Spring 2025"
      }
    ],
    "count": 150
  },
  "metadata": {
    "source": "hybrid",
    "last_updated": "2025-12-03T00:00:00Z",
    "is_fresh": true,
    "auto_populated": false,
    "count": 150
  }
}
```

#### POST /api/courses/search

Search courses with filters.

**Request Body**:
```json
{
  "course_code": "CSC",
  "semester": "Spring 2025",
  "university": "Baruch College",
  "department": "Computer Science",
  "modality": "In-Person"
}
```

**Response**: Same format as GET /api/courses

---

### Schedule Optimization

#### POST /api/schedule/optimize

Generate optimized course schedules.

**Request Body**:
```json
{
  "course_codes": ["CSC 101", "MATH 201", "ENG 101"],
  "semester": "Spring 2025",
  "university": "Baruch College",
  "constraints": {
    "required_course_codes": ["CSC 101", "MATH 201"],
    "preferred_days": ["MWF"],
    "earliest_start_time": "09:00",
    "latest_end_time": "17:00",
    "min_professor_rating": 4.0,
    "max_hours_per_day": 6,
    "min_credits": 12,
    "max_credits": 18
  }
}
```

**Response**:
```json
{
  "schedules": [
    {
      "rank": 1,
      "total_credits": 12,
      "overall_score": 85.5,
      "preference_score": 90.0,
      "professor_quality_score": 80.0,
      "time_convenience_score": 85.0,
      "average_professor_rating": 4.2,
      "conflicts": [],
      "classes": [
        {
          "course_code": "CSC 101",
          "course_name": "Introduction to Computing",
          "section_id": "uuid",
          "professor": "John Smith",
          "professor_grade": "A",
          "days": "MWF",
          "time": "09:00 - 10:15",
          "location": "NVC 14-235"
        }
      ]
    }
  ],
  "count": 5,
  "courses": {
    "CSC 101": {"id": "uuid", "name": "Introduction to Computing"}
  },
  "total_sections": 45
}
```

#### POST /api/schedule/validate

Validate adding/removing a section.

**Request Body**:
```json
{
  "schedule_id": "uuid",
  "section_id": "uuid",
  "action": "add"
}
```

**Response**:
```json
{
  "valid": true,
  "conflicts": [],
  "warnings": [],
  "suggestions": []
}
```

---

### Professor Data

#### GET /api/professor/{professor_name}

Get professor information and grades.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `professor_name` | string | Full name of professor (URL encoded) |

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `university` | string | No | "Baruch College" | CUNY school name |
| `auto_populate` | boolean | No | true | Auto-fetch if data missing/stale |

**Example**:
```bash
curl "http://localhost:8000/api/professor/John%20Smith?university=Baruch%20College"
```

**Response**:
```json
{
  "data": {
    "professor": {
      "id": "uuid",
      "name": "John Smith",
      "university": "Baruch College",
      "department": "Computer Science",
      "grade_letter": "A",
      "composite_score": 85.5,
      "average_rating": 4.2,
      "average_difficulty": 3.1,
      "review_count": 45,
      "last_updated": "2025-12-01T00:00:00Z"
    },
    "reviews": [
      {
        "id": "uuid",
        "course_code": "CSC 101",
        "rating": 5,
        "difficulty": 3,
        "comment": "Great professor!",
        "date": "2024-05-15"
      }
    ],
    "review_count": 45
  },
  "metadata": {
    "source": "hybrid",
    "last_updated": "2025-12-01T00:00:00Z",
    "is_fresh": true,
    "auto_populated": false,
    "count": 1
  }
}
```

#### POST /api/professor/compare

Compare multiple professors.

**Request Body**:
```json
{
  "professor_names": ["John Smith", "Jane Doe", "Bob Wilson"],
  "university": "Baruch College",
  "course_code": "CSC 101"
}
```

**Response**:
```json
{
  "data": {
    "success": true,
    "total_professors": 3,
    "professors": [
      {
        "professor_name": "John Smith",
        "grade_letter": "A",
        "composite_score": 85.5,
        "average_rating": 4.2,
        "average_difficulty": 3.1,
        "review_count": 45
      }
    ],
    "recommendation": "Based on ratings and reviews, John Smith (Grade: A) is recommended.",
    "course_code": "CSC 101"
  },
  "metadata": {
    "source": "hybrid",
    "is_fresh": true,
    "auto_populated": true,
    "count": 3
  }
}
```

---

### AI Chat

#### POST /api/chat/message

Send a message to the AI assistant.

**Request Body**:
```json
{
  "message": "Help me build a schedule with CSC 101 and MATH 201",
  "context": {
    "currentCourses": [
      {"code": "ENG 101", "name": "English Composition"}
    ],
    "semester": "Spring 2025",
    "university": "Baruch College"
  }
}
```

**Response**:
```json
{
  "message": "I'd recommend starting with CSC 101 in the morning...",
  "suggestions": [],
  "context": { ... }
}
```

---

### Admin Endpoints

#### POST /api/admin/sync

Trigger manual data synchronization.

**Request Body**:
```json
{
  "entity_type": "courses",
  "semester": "Spring 2025",
  "university": "Baruch College",
  "force": false
}
```

**Response**:
```json
{
  "success": true,
  "request": {
    "entity_type": "courses",
    "semester": "Spring 2025",
    "university": "Baruch College",
    "force": false
  }
}
```

#### GET /api/admin/sync-status

Get sync status for an entity.

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_type` | string | Yes | Type of entity (courses, professors) |
| `semester` | string | Yes | Semester |
| `university` | string | Yes | University name |

**Example**:
```bash
curl "http://localhost:8000/api/admin/sync-status?entity_type=courses&semester=Spring%202025&university=Baruch%20College"
```

**Response**:
```json
{
  "id": "uuid",
  "entity_type": "courses",
  "semester": "Spring 2025",
  "university": "Baruch College",
  "last_sync": "2025-12-03T00:00:00Z",
  "sync_status": "success",
  "error_message": null,
  "created_at": "2025-11-01T00:00:00Z"
}
```

---

## MCP Tools Reference

These tools are used internally by the AI and can be called via the MCP protocol.

### fetch_course_sections

Fetch available course sections from CUNY database.

**Parameters**:
- `course_codes`: List[str] - Course codes (e.g., ["CSC381", "MATH201"])
- `semester`: str - Semester (e.g., "Fall 2025")
- `university`: Optional[str] - CUNY school name

### generate_optimized_schedule

Generate optimized course schedules based on requirements and preferences.

**Parameters**:
- `required_courses`: List[str] - Required course codes
- `semester`: str - Semester
- `university`: str - CUNY school name
- `preferred_days`: Optional[List[str]] - Preferred days
- `earliest_start_time`: Optional[str] - Earliest class time (HH:MM)
- `latest_end_time`: Optional[str] - Latest class time (HH:MM)
- `min_professor_rating`: Optional[float] - Minimum rating (0-5)
- `max_schedules`: int - Max schedules to return (default: 5)

### get_professor_grade

Get AI-generated grade for a professor.

**Parameters**:
- `professor_name`: str - Full name of professor
- `university`: str - CUNY school name
- `course_code`: Optional[str] - Course code filter

### compare_professors

Compare multiple professors side-by-side.

**Parameters**:
- `professor_names`: List[str] - Professor names to compare
- `university`: str - CUNY school name
- `course_code`: Optional[str] - Course context

### check_schedule_conflicts

Check for conflicts in a set of course sections.

**Parameters**:
- `section_ids`: List[str] - Section IDs (UUIDs)

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| All endpoints | 100 requests | 60 seconds |
| `/api/admin/*` | 10 requests | 60 seconds |
| `/api/schedule/optimize` | 20 requests | 60 seconds |

Exceeding rate limits returns HTTP 429 with `Retry-After` header.

---

## Data Freshness

The API uses a hybrid data architecture with automatic freshness management:

| Data Type | TTL | Behavior |
|-----------|-----|----------|
| Course Data | 7 days | Auto-refresh if stale |
| Professor Data | 7 days | Auto-refresh if stale |
| Review Data | 30 days | Auto-refresh if stale |
| Cache Entries | 5 minutes | In-memory LRU cache |

When `auto_populate=true` (default), stale or missing data triggers background scraping.

---

## WebSocket Support

Future versions will support WebSocket connections for real-time updates:

```javascript
const ws = new WebSocket('wss://api.schedulefirst.ai/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle schedule updates, sync progress, etc.
};
```

---

## SDK Examples

### JavaScript/TypeScript

```typescript
import { apiClient } from '@/lib/api-client';

// Get courses
const courses = await apiClient.get('/api/courses', {
  params: { semester: 'Spring 2025', university: 'Baruch College' }
});

// Optimize schedule
const schedules = await apiClient.post('/api/schedule/optimize', {
  course_codes: ['CSC 101', 'MATH 201'],
  semester: 'Spring 2025',
  university: 'Baruch College',
  constraints: { preferred_days: ['MWF'] }
});
```

### Python

```python
import httpx

async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
    # Get courses
    response = await client.get("/api/courses", params={
        "semester": "Spring 2025",
        "university": "Baruch College"
    })
    courses = response.json()
    
    # Optimize schedule
    response = await client.post("/api/schedule/optimize", json={
        "course_codes": ["CSC 101", "MATH 201"],
        "semester": "Spring 2025",
        "university": "Baruch College",
        "constraints": {"preferred_days": ["MWF"]}
    })
    schedules = response.json()
```

### cURL

```bash
# Get courses
curl "http://localhost:8000/api/courses?semester=Spring%202025&university=Baruch%20College"

# Optimize schedule
curl -X POST http://localhost:8000/api/schedule/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "course_codes": ["CSC 101", "MATH 201"],
    "semester": "Spring 2025",
    "university": "Baruch College",
    "constraints": {"preferred_days": ["MWF"]}
  }'
```

---

## Changelog

### v1.0.0 (2025-12-03)
- Initial release with hybrid data architecture
- Auto-population of missing/stale data
- Circuit breaker pattern for external services
- MCP tools integration
- Admin sync endpoints
