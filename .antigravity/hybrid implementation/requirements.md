# Hybrid Implementation Requirements

## Functional Requirements

### FR1: Data Freshness Management

**FR1.1**: System SHALL track last update timestamp for all data entities

- Course data: `last_scraped` timestamp
- Professor data: `last_updated` timestamp
- Review data: `scraped_at` timestamp

**FR1.2**: System SHALL define staleness thresholds for each data type

- Course sections: 7 days
- Professor information: 7 days
- Professor reviews: 30 days
- Optimized schedules (cache): 1 hour

**FR1.3**: System SHALL provide method to check if data is fresh

- `is_course_data_fresh(semester, university) -> bool`
- `is_professor_data_fresh(professor_id) -> bool`
- `is_review_data_fresh(professor_id) -> bool`

### FR2: On-Demand Data Population

**FR2.1**: System SHALL support on-demand execution of background jobs

- `sync_courses_job(semester, university)` - callable directly
- `scrape_reviews_job(professor_name, university)` - callable directly
- `update_grades_job(professor_id)` - callable directly

**FR2.2**: System SHALL automatically populate missing data when requested

- If course data missing → trigger course scraper
- If professor data missing → trigger professor scraper
- If reviews missing → trigger review scraper

**FR2.3**: System SHALL handle concurrent data population requests

- Use locks to prevent duplicate scraping
- Queue requests if scraper already running
- Return cached results while scraping in background

### FR3: Enhanced MCP Tools

**FR3.1**: `fetch_course_sections` tool SHALL auto-populate missing data

- Check if course data exists in DB
- If missing or stale, trigger scraper
- Return fresh data from DB

**FR3.2**: `get_professor_grade` tool SHALL auto-enrich professor data

- Check if professor exists in DB
- If missing, scrape RateMyProfessors
- Perform sentiment analysis
- Store results in DB
- Return grade and metrics

**FR3.3**: `generate_optimized_schedule` tool SHALL ensure all dependencies exist

- Verify course data available
- Verify professor data available
- Auto-populate if missing
- Generate optimized schedules

**FR3.4**: All MCP tools SHALL implement fallback mechanisms

- Primary: Database lookup
- Secondary: Web scraping
- Tertiary: Partial data with warnings

### FR4: REST API Enhancements

**FR4.1**: Simple endpoints SHALL use direct database access

- `GET /api/courses` - Direct DB query
- `GET /api/sections` - Direct DB query
- `POST /api/courses/search` - Direct DB query with filters

**FR4.2**: Complex endpoints SHALL use MCP tools

- `POST /api/schedule/optimize` - Use MCP tool
- `POST /api/professor/compare` - Use MCP tool
- `POST /api/chat/message` - Use Gemini with MCP tools

**FR4.3**: Endpoints SHALL support auto-population flag

- `?auto_populate=true` (default) - Auto-fetch missing data
- `?auto_populate=false` - Return empty if data missing

**FR4.4**: Endpoints SHALL return metadata about data source

```json
{
  "data": [...],
  "metadata": {
    "source": "cache|database|scraper",
    "last_updated": "2025-11-26T16:00:00Z",
    "is_fresh": true,
    "auto_populated": false
  }
}
```

### FR5: Error Handling

**FR5.1**: System SHALL handle scraping failures gracefully

- Log error with context
- Return partial data if available
- Provide user-friendly error message

**FR5.2**: System SHALL implement retry logic for transient failures

- 3 retry attempts with exponential backoff
- Different strategies for different error types
- Circuit breaker for persistent failures

**FR5.3**: System SHALL provide fallback responses

- Return cached data if scraping fails
- Return partial data with warnings
- Never return 500 errors for missing data

### FR6: Caching

**FR6.1**: System SHALL implement multi-level caching

- Level 1: In-memory cache (1 hour TTL)
- Level 2: Database (7-30 day TTL)
- Level 3: Web scraping (fresh data)

**FR6.2**: System SHALL use cache keys with appropriate granularity

- `courses:{semester}:{university}`
- `professor:{name}:{university}`
- `schedule:{hash(constraints)}`
- `reviews:{professor_id}`

**FR6.3**: System SHALL support cache invalidation

- Manual invalidation via admin endpoint
- Automatic invalidation on data update
- TTL-based expiration

---

## Non-Functional Requirements

### NFR1: Performance

**NFR1.1**: Cached queries SHALL respond in < 100ms (P95)

**NFR1.2**: Fresh data queries (with scraping) SHALL complete in < 10s (P95)

**NFR1.3**: Schedule optimization SHALL complete in < 5s (P95)

**NFR1.4**: System SHALL achieve > 80% cache hit rate after warmup period

**NFR1.5**: Database queries SHALL use appropriate indexes

- Index on `(semester, university)` for courses
- Index on `(name, university)` for professors
- Index on `professor_id` for reviews

### NFR2: Scalability

**NFR2.1**: System SHALL handle concurrent scraping requests

- Max 5 concurrent scraping operations
- Queue additional requests
- Use semaphore for rate limiting

**NFR2.2**: System SHALL support horizontal scaling

- Stateless API servers
- Shared cache (future: Redis)
- Database connection pooling

**NFR2.3**: System SHALL handle increased load

- Support 100 concurrent users
- Support 1000 requests/minute
- Graceful degradation under load

### NFR3: Reliability

**NFR3.1**: System SHALL have > 99% uptime for API endpoints

**NFR3.2**: System SHALL recover from scraper failures

- Continue serving cached data
- Retry failed scrapes on next request
- Log failures for monitoring

**NFR3.3**: System SHALL handle database connection failures

- Automatic reconnection
- Connection pooling with health checks
- Fallback to cached data

### NFR4: Security

**NFR4.1**: System SHALL implement rate limiting

- 100 requests/minute per IP for API endpoints
- 10 scraping requests/hour per IP
- Configurable limits per endpoint

**NFR4.2**: System SHALL validate all inputs

- Course codes: `^[A-Z]{2,4}\s?\d{3,4}$`
- Semesters: `^(Fall|Spring|Summer|Winter)\s\d{4}$`
- Professor names: Sanitized, max 100 chars

**NFR4.3**: System SHALL respect scraping ethics

- Obey robots.txt
- 2-second delay between requests
- User-agent identification
- Respect rate limits

**NFR4.4**: System SHALL secure sensitive data

- API keys in environment variables
- No credentials in logs
- HTTPS for all external requests

### NFR5: Observability

**NFR5.1**: System SHALL log all data access operations

```python
logger.info("Data access", extra={
    "operation": "fetch_courses",
    "source": "cache|db|scraper",
    "duration_ms": 150,
    "cache_hit": True,
    "semester": "Fall 2025",
    "university": "Baruch College"
})
```

**NFR5.2**: System SHALL track key metrics

- Cache hit rate
- Scraping frequency
- API response times (P50, P95, P99)
- Error rates by type
- Data freshness distribution

**NFR5.3**: System SHALL provide health check endpoints

- `GET /health` - Overall system health
- `GET /health/db` - Database connectivity
- `GET /health/cache` - Cache statistics
- `GET /health/scrapers` - Scraper status

### NFR6: Maintainability

**NFR6.1**: Code SHALL follow existing project structure

- Services in `mcp_server/services/`
- Models in `mcp_server/models/`
- Utils in `mcp_server/utils/`
- Jobs in `background_jobs/jobs/`

**NFR6.2**: Code SHALL include comprehensive docstrings

- All public functions documented
- Parameters and return types specified
- Examples for complex functions

**NFR6.3**: Code SHALL include type hints

- All function signatures typed
- Pydantic models for data validation
- mypy compatibility

**NFR6.4**: Code SHALL include unit tests

- > 80% code coverage
- Test happy paths and error cases
- Mock external dependencies

---

## Data Requirements

### DR1: Database Schema Updates

**DR1.1**: Add staleness tracking fields

```sql
-- courses table
ALTER TABLE courses ADD COLUMN last_scraped TIMESTAMP;
ALTER TABLE courses ADD COLUMN is_stale BOOLEAN DEFAULT FALSE;

-- professors table
ALTER TABLE professors ADD COLUMN last_updated TIMESTAMP;
ALTER TABLE professors ADD COLUMN data_source VARCHAR(50); -- 'ratemyprof', 'manual', etc.

-- Add sync tracking table
CREATE TABLE sync_metadata (
    id UUID PRIMARY KEY,
    entity_type VARCHAR(50), -- 'courses', 'professors', 'reviews'
    semester VARCHAR(50),
    university VARCHAR(100),
    last_sync TIMESTAMP,
    sync_status VARCHAR(20), -- 'success', 'failed', 'in_progress'
    created_at TIMESTAMP DEFAULT NOW()
);
```

**DR1.2**: Add indexes for performance

```sql
CREATE INDEX idx_courses_semester_university ON courses(semester, university);
CREATE INDEX idx_professors_name_university ON professors(name, university);
CREATE INDEX idx_reviews_professor_id ON professor_reviews(professor_id);
CREATE INDEX idx_sync_metadata_lookup ON sync_metadata(entity_type, semester, university);
```

### DR2: Cache Storage

**DR2.1**: In-memory cache structure

```python
{
    "courses:Fall 2025:Baruch College": {
        "data": [...],
        "expires_at": datetime,
        "created_at": datetime
    }
}
```

**DR2.2**: Cache size limits

- Max 1000 entries in memory
- LRU eviction policy
- Max 10MB total cache size

---

## API Requirements

### AR1: New Service Endpoints

**AR1.1**: Data Freshness Service

```python
class DataFreshnessService:
    async def is_course_data_fresh(semester: str, university: str) -> bool
    async def is_professor_data_fresh(professor_id: UUID) -> bool
    async def get_last_sync(entity_type: str, semester: str, university: str) -> Optional[datetime]
    async def mark_sync_complete(entity_type: str, semester: str, university: str)
```

**AR1.2**: Data Population Service

```python
class DataPopulationService:
    async def ensure_course_data(semester: str, university: str) -> bool
    async def ensure_professor_data(professor_name: str, university: str) -> bool
    async def populate_missing_data(entity_type: str, **kwargs) -> Dict
```

**AR1.3**: Enhanced Supabase Service

```python
class SupabaseService:
    # New methods
    async def get_sync_metadata(entity_type: str, semester: str, university: str) -> Optional[SyncMetadata]
    async def update_sync_metadata(entity_type: str, semester: str, university: str, status: str)
    async def get_stale_entities(entity_type: str, ttl_seconds: int) -> List[Dict]
```

### AR2: Modified Background Jobs

**AR2.1**: Jobs SHALL accept parameters for on-demand execution

```python
async def sync_courses_job(
    semester: Optional[str] = None,
    university: Optional[str] = None,
    force: bool = False
) -> Dict[str, Any]
```

**AR2.2**: Jobs SHALL return execution metadata

```json
{
  "success": true,
  "entities_processed": 150,
  "duration_seconds": 45.2,
  "errors": [],
  "timestamp": "2025-11-26T16:00:00Z"
}
```

---

## Testing Requirements

### TR1: Unit Tests

**TR1.1**: Test data freshness logic

- Fresh data returns True
- Stale data returns False
- Missing data returns False

**TR1.2**: Test auto-population logic

- Missing data triggers scraper
- Fresh data skips scraper
- Concurrent requests handled correctly

**TR1.3**: Test fallback mechanisms

- DB failure → scraper
- Scraper failure → partial data
- All failures → error response

### TR2: Integration Tests

**TR2.1**: Test end-to-end flows

- Empty DB → auto-populate → return data
- Stale data → refresh → return fresh data
- Cached data → skip DB → return cached

**TR2.2**: Test MCP tool integration

- Tools call correct services
- Tools handle errors gracefully
- Tools return expected format

### TR3: Performance Tests

**TR3.1**: Load testing

- 100 concurrent requests
- Response time < 100ms for cached
- Response time < 10s for fresh

**TR3.2**: Cache effectiveness

- Measure hit rate
- Verify TTL expiration
- Test eviction policy

---

## Documentation Requirements

### DOC1: Code Documentation

**DOC1.1**: Update all docstrings with new functionality

**DOC1.2**: Add inline comments for complex logic

**DOC1.3**: Update type hints for all functions

### DOC2: API Documentation

**DOC2.1**: Update OpenAPI/Swagger docs for modified endpoints

**DOC2.2**: Document new query parameters (`auto_populate`)

**DOC2.3**: Document response metadata fields

### DOC3: Architecture Documentation

**DOC3.1**: Update README.md with new architecture

**DOC3.2**: Create data flow diagrams

**DOC3.3**: Document caching strategy

---

## Dependencies

### Existing Dependencies

- FastAPI
- FastMCP
- Supabase client
- Google Gemini API
- Selenium
- APScheduler
- Pydantic

### New Dependencies (if needed)

- `asyncio.Lock` - For concurrent request handling (built-in)
- `functools.lru_cache` - For simple caching (built-in)
- No additional external dependencies required

---

## Constraints

### Technical Constraints

- Must maintain backward compatibility with existing API
- Must work with existing database schema (can add fields)
- Must not break existing frontend integration
- Must respect RateMyProfessors rate limits

### Business Constraints

- Minimize LLM API costs
- Maintain < 5s response time for critical paths
- Support current user load (estimated 100 concurrent users)

### Time Constraints

- Implementation should be completed in 4 weeks
- Phased rollout to minimize risk
- Can be deployed incrementally
