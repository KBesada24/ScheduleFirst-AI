# Hybrid Implementation Tasks

## Phase 1: Foundation & Data Freshness (Week 1)

### Task 1.1: Database Schema Updates

- [x] Create migration script for new fields
  - [x] Add `last_scraped` to `courses` table
  - [x] Add `is_stale` boolean to `courses` table
  - [x] Add `last_updated` to `professors` table
  - [x] Add `data_source` to `professors` table
- [x] Create `sync_metadata` table
  - [x] Define schema with entity_type, semester, university, last_sync, sync_status
  - [x] Add appropriate indexes
- [x] Create database indexes
  - [x] Index on `(semester, university)` for courses
  - [x] Index on `(name, university)` for professors
  - [x] Index on `professor_id` for reviews
  - [x] Index on `(entity_type, semester, university)` for sync_metadata
- [x] Test migrations on development database
- [x] Document rollback procedures

### Task 1.2: Create Data Freshness Service

- [x] Create `services/data_freshness_service.py`
- [x] Implement `DataFreshnessService` class
  - [x] `__init__()` - Initialize with TTL constants
  - [x] `is_course_data_fresh(semester, university)` - Check course staleness
  - [x] `is_professor_data_fresh(professor_id)` - Check professor staleness
  - [x] `is_review_data_fresh(professor_id)` - Check review staleness
  - [x] `get_last_sync(entity_type, semester, university)` - Get sync timestamp
  - [x] `mark_sync_in_progress(entity_type, semester, university)` - Lock sync
  - [x] `mark_sync_complete(entity_type, semester, university, status)` - Update sync
- [x] Add comprehensive docstrings and type hints
- [x] Create unit tests for freshness logic
  - [x] Test fresh data returns True
  - [x] Test stale data returns False
  - [x] Test missing data returns False
  - [x] Test edge cases (exactly at TTL boundary)
- [x] Create singleton instance `data_freshness_service`

### Task 1.3: Create Sync Metadata Model

- [x] Create `models/sync_metadata.py`
- [x] Define `SyncMetadata` Pydantic model
  - [x] `id: UUID`
  - [x] `entity_type: str`
  - [x] `semester: str`
  - [x] `university: str`
  - [x] `last_sync: datetime`
  - [x] `sync_status: str` (success, failed, in_progress)
  - [x] `error_message: Optional[str]`
  - [x] `created_at: datetime`
- [x] Add validation for entity_type enum
- [x] Add validation for sync_status enum

### Task 1.4: Enhance Supabase Service

- [x] Update `services/supabase_service.py`
- [x] Add sync metadata methods
  - [x] `get_sync_metadata(entity_type, semester, university)` - Fetch sync record
  - [x] `create_sync_metadata(entity_type, semester, university, status)` - Create record
  - [x] `update_sync_metadata(entity_type, semester, university, status, error)` - Update record
  - [x] `get_stale_entities(entity_type, ttl_seconds)` - Find stale records
- [x] Update existing methods to track timestamps
  - [x] `insert_courses()` - Set `last_scraped`
  - [x] `insert_professor()` - Set `last_updated`
  - [x] `insert_reviews()` - Set `scraped_at`
- [x] Add unit tests for new methods
- [x] Update docstrings

---

## Phase 2: On-Demand Data Population (Week 2)

### Task 2.1: Create Data Population Service

- [x] Create `services/data_population_service.py`
- [x] Implement `DataPopulationService` class
  - [x] `__init__()` - Initialize with locks for concurrency control
  - [x] `ensure_course_data(semester, university, force=False)` - Ensure courses exist
  - [x] `ensure_professor_data(professor_name, university, force=False)` - Ensure professor exists
  - [x] `ensure_review_data(professor_id, force=False)` - Ensure reviews exist
  - [x] `populate_missing_data(entity_type, **kwargs)` - Generic population method
  - [x] `_acquire_lock(lock_key)` - Prevent duplicate scraping
  - [x] `_release_lock(lock_key)` - Release scraping lock
- [x] Implement concurrency control
  - [x] Use `asyncio.Lock` for each entity being scraped
  - [x] Queue requests if already scraping
  - [x] Return cached/existing data while scraping in background
- [x] Add comprehensive error handling
  - [x] Handle scraping failures
  - [x] Handle database failures
  - [x] Log all errors with context
- [x] Create unit tests
  - [x] Test successful population
  - [x] Test concurrent requests
  - [x] Test lock acquisition/release
  - [x] Test error scenarios
- [x] Create singleton instance `data_population_service`

### Task 2.2: Refactor Background Jobs for On-Demand Execution

- [x] Update `background_jobs/jobs/sync_cuny_courses.py`
  - [x] Add parameters: `semester: Optional[str]`, `university: Optional[str]`, `force: bool`
  - [x] If parameters provided, sync only that semester/university
  - [x] If no parameters, sync all (existing behavior)
  - [x] Update sync_metadata on start and completion
  - [x] Return execution metadata (success, count, duration, errors)
- [x] Update `background_jobs/jobs/scrape_reviews.py`
  - [x] Add parameters: `professor_name: Optional[str]`, `university: Optional[str]`
  - [x] If parameters provided, scrape only that professor
  - [x] If no parameters, scrape all (existing behavior)
  - [x] Update sync_metadata
  - [x] Return execution metadata
- [x] Update `background_jobs/jobs/update_professor_grades.py`
  - [x] Add parameters: `professor_id: Optional[UUID]`
  - [x] If parameter provided, update only that professor
  - [x] If no parameter, update all (existing behavior)
  - [x] Update sync_metadata
  - [x] Return execution metadata
- [x] Test on-demand execution
  - [x] Test with specific parameters
  - [x] Test with no parameters (existing behavior)
  - [x] Verify metadata updates
- [x] Update docstrings with new parameters

### Task 2.3: Integrate Data Population with Background Jobs

- [x] Update `DataPopulationService.ensure_course_data()`
  - [x] Check if data fresh using `data_freshness_service`
  - [x] If stale or missing, call `sync_courses_job(semester, university)`
  - [x] Wait for completion or return immediately based on `wait` parameter
  - [x] Update sync_metadata
- [x] Update `DataPopulationService.ensure_professor_data()`
  - [x] Check if professor exists and is fresh
  - [x] If missing, call `scrape_reviews_job(professor_name, university)`
  - [x] Then call `update_grades_job(professor_id)`
  - [x] Handle errors gracefully
- [x] Add integration tests
  - [x] Test end-to-end population flow
  - [x] Test with empty database
  - [x] Test with stale data
  - [x] Test with fresh data (should skip)

---

## Phase 3: Enhanced MCP Tools (Week 2-3)

### Task 3.1: Update `fetch_course_sections` MCP Tool

- [x] Update `mcp_server/tools/schedule_optimizer.py`
- [x] Modify `fetch_course_sections()` function
  - [x] Add auto-population logic at start
  - [x] Call `data_population_service.ensure_course_data(semester, university)`
  - [x] Add try-except for graceful error handling
  - [x] Return metadata about data source (cache/db/scraper)
- [x] Update return format to include metadata
  ```python
  {
      "success": True,
      "courses": [...],
      "metadata": {
          "source": "database",
          "last_updated": "2025-11-26T16:00:00Z",
          "is_fresh": True,
          "auto_populated": False
      }
  }
  ```
- [x] Add logging for data access patterns
- [x] Test with empty database
- [x] Test with stale data
- [x] Test with fresh data

### Task 3.2: Update `get_professor_grade` MCP Tool

- [x] Modify `get_professor_grade()` and `_get_professor_grade_impl()`
- [x] Add auto-enrichment logic
  - [x] Check if professor exists in DB
  - [x] Check if data is fresh
  - [x] If missing/stale, call `data_population_service.ensure_professor_data()`
  - [x] Fetch from DB after population
- [x] Implement fallback chain
  - [x] Primary: Database lookup
  - [x] Secondary: Scrape RateMyProfessors
  - [x] Tertiary: Return partial data with warning
- [x] Update return format with metadata
- [x] Add comprehensive error handling
  - [x] Handle scraping failures
  - [x] Handle sentiment analysis failures
  - [x] Handle database failures
- [x] Test all fallback scenarios
- [x] Add logging for each step

### Task 3.3: Update `generate_optimized_schedule` MCP Tool

- [x] Modify `generate_optimized_schedule()` function
- [x] Add dependency checking
  - [x] Ensure course data exists for all required courses
  - [x] Ensure professor data exists for all professors in sections
  - [x] Auto-populate if missing
- [x] Add parallel data population
  - [x] Use `asyncio.gather()` to populate multiple courses concurrently
  - [x] Limit concurrency to avoid overwhelming scrapers
- [x] Update error handling
  - [x] Handle partial data availability
  - [x] Provide meaningful error messages
  - [x] Suggest alternatives if data unavailable
- [x] Test with various scenarios
  - [x] All data available
  - [x] Some data missing
  - [x] All data missing
  - [x] Scraping failures

### Task 3.4: Update `compare_professors` MCP Tool

- [x] Modify `compare_professors()` function
- [x] Add auto-enrichment for all professors
  - [x] Populate data for each professor
  - [x] Handle failures for individual professors
  - [x] Continue comparison with available data
- [x] Update comparison logic
  - [x] Handle missing data gracefully
  - [x] Indicate data quality in results
  - [x] Adjust recommendations based on data completeness
- [x] Test comparison scenarios
  - [x] All professors have data
  - [x] Some professors missing data
  - [x] Mixed data quality

### Task 3.5: Update `check_schedule_conflicts` MCP Tool

- [x] Implement `get_section_by_id()` in Supabase service (currently TODO)
- [x] Modify `check_schedule_conflicts()` function
- [x] Add section data fetching
  - [x] Fetch all sections by ID
  - [x] Handle missing sections
  - [x] Auto-populate if needed
- [x] Test conflict detection
  - [x] Time overlaps
  - [x] Travel time conflicts
  - [x] Missing section data

---

## Phase 4: REST API Enhancements (Week 3)

### Task 4.1: Update Simple CRUD Endpoints

- [x] Update `api_server.py`
- [x] Modify `GET /api/courses`
  - [x] Add `auto_populate: bool = True` query parameter
  - [x] If `auto_populate=true` and data missing, trigger population
  - [x] Add metadata to response
  - [x] Add error handling for population failures
- [x] Modify `GET /api/professor/{name}`
  - [x] Add `auto_populate: bool = True` query parameter
  - [x] Auto-enrich if missing
  - [x] Return metadata
- [x] Modify `POST /api/courses/search`
  - [x] Add auto-population for search results
  - [x] Handle partial results
- [x] Add response metadata to all endpoints
  ```python
  {
      "data": [...],
      "metadata": {
          "source": "cache|database|scraper",
          "last_updated": "2025-11-26T16:00:00Z",
          "is_fresh": true,
          "auto_populated": false,
          "count": 150
      }
  }
  ```
- [x] Test all endpoints with `auto_populate=true/false`

### Task 4.2: Update Complex Operation Endpoints

- [x] Verify `POST /api/schedule/optimize` uses MCP tools
  - [x] Should already have auto-population via MCP tool
  - [x] Add metadata to response
  - [x] Test end-to-end flow
- [x] Verify `POST /api/chat/message` uses Gemini with MCP tools
  - [x] Ensure MCP tools are accessible to Gemini
  - [x] Test AI can trigger data population
  - [x] Add logging for MCP tool usage
- [x] Add new endpoint `POST /api/professor/compare`
  - [x] Accept list of professor names
  - [x] Call `compare_professors` MCP tool
  - [x] Return comparison with metadata
- [x] Test all complex endpoints

### Task 4.3: Add Admin/Utility Endpoints

- [x] Create `POST /api/admin/sync` endpoint
  - [x] Trigger manual data sync
  - [x] Accept parameters: entity_type, semester, university
  - [x] Require admin authentication (future)
  - [x] Return sync status
- [x] Create `GET /api/admin/sync-status` endpoint
  - [x] Return sync metadata for all entities
  - [x] Show last sync times
  - [x] Show sync statuses
- [x] Create `POST /api/admin/cache/clear` endpoint
  - [x] Clear in-memory cache
  - [x] Return cache statistics
- [x] Create `GET /health/cache` endpoint
  - [x] Return cache hit rate
  - [x] Return cache size
  - [x] Return cache entries count
- [x] Test admin endpoints
- [x] Document admin endpoints in OpenAPI

---

## Phase 5: Caching Improvements (Week 3-4)

### Task 5.1: Enhance Cache Manager

- [x] Update `utils/cache.py`
- [x] Add cache statistics tracking
  - [x] Track hits/misses
  - [x] Track cache size
  - [x] Track eviction count
- [x] Implement LRU eviction policy
  - [x] Track access times
  - [x] Evict least recently used when size limit reached
  - [x] Set max cache size (1000 entries or 10MB)
- [x] Add cache warming functionality
  - [x] `warm_cache(entity_type, **kwargs)` - Pre-populate cache
  - [x] Warm common queries on startup
- [x] Add cache monitoring
  - [x] Log cache statistics periodically
  - [x] Alert on low hit rate
- [x] Test cache behavior
  - [x] Test eviction policy
  - [x] Test size limits
  - [x] Test TTL expiration

### Task 5.2: Implement Smart Caching in Services

- [x] Update `SupabaseService`
  - [x] Add `@cache_manager.cached()` decorator to read methods
  - [x] Use appropriate cache keys
  - [x] Set appropriate TTLs
- [x] Update `DataPopulationService`
  - [x] Cache population results
  - [x] Invalidate cache on new data
- [x] Update MCP tools
  - [x] Cache expensive operations
  - [x] Cache professor grades
  - [x] Cache optimized schedules
- [x] Test caching integration
  - [x] Verify cache hits
  - [x] Verify cache invalidation
  - [x] Measure performance improvement

---

## Phase 6: Error Handling & Resilience (Week 4)

### Task 6.1: Implement Comprehensive Error Handling

- [x] Create custom exception classes
  - [x] `DataNotFoundError` - Entity not found
  - [x] `DataStaleError` - Data too old
  - [x] `ScrapingError` - Scraping failed
  - [x] `PopulationError` - Population failed
- [x] Update all services with error handling
  - [x] Catch specific exceptions
  - [x] Log with context
  - [x] Return user-friendly messages
- [x] Implement retry logic
  - [x] Use `tenacity` library (already in use)
  - [x] Configure retries per operation type
  - [x] Exponential backoff
- [x] Add circuit breaker pattern
  - [x] Track failure rates
  - [x] Open circuit after threshold
  - [x] Auto-recover after cooldown
- [x] Test error scenarios
  - [x] Database failures
  - [x] Scraping failures
  - [x] Network failures
  - [x] Timeout scenarios

### Task 6.2: Implement Fallback Mechanisms

- [x] Create fallback chain for each operation
  - [x] Primary: Database
  - [x] Secondary: Cache
  - [x] Tertiary: Scraper
  - [x] Final: Partial data with warnings
- [x] Implement graceful degradation
  - [x] Return partial results if some data unavailable
  - [x] Include warnings in response
  - [x] Suggest alternatives
- [x] Test fallback scenarios
  - [x] Each level of fallback
  - [x] Complete failure handling
  - [x] Partial data scenarios

---

## Phase 7: Testing & Quality Assurance (Week 4)

### Task 7.1: Unit Tests

- [x] Write tests for `DataFreshnessService`
  - [x] Test staleness detection
  - [x] Test edge cases
  - [x] Test with missing data
- [x] Write tests for `DataPopulationService`
  - [x] Test successful population
  - [x] Test concurrent requests
  - [x] Test lock behavior
  - [x] Test error handling
- [x] Write tests for enhanced Supabase methods
  - [x] Test sync metadata CRUD
  - [x] Test staleness queries
- [x] Write tests for updated MCP tools
  - [x] Test auto-population
  - [x] Test fallback logic
  - [x] Test error scenarios
- [x] Achieve > 80% code coverage
- [x] Run tests: `pytest --cov=mcp_server --cov-report=html`

### Task 7.2: Integration Tests

- [x] Test end-to-end flows
  - [x] Empty DB → auto-populate → return data
  - [x] Stale data → refresh → return fresh
  - [x] Cached data → skip DB → return cached
- [x] Test MCP tool integration
  - [x] Tools call correct services
  - [x] Tools handle errors gracefully
  - [x] Tools return expected format
- [x] Test API endpoints
  - [x] Simple endpoints with auto-population
  - [x] Complex endpoints with MCP tools
  - [x] Admin endpoints
- [x] Test background job integration
  - [x] On-demand execution
  - [x] Scheduled execution
  - [x] Metadata updates

### Task 7.3: Performance Tests

- [x] Load testing with `locust` or `k6`
  - [x] 100 concurrent users
  - [x] 1000 requests/minute
  - [x] Measure response times
- [x] Cache effectiveness testing
  - [x] Measure hit rate
  - [x] Verify TTL behavior
  - [x] Test eviction policy
- [x] Database query optimization
  - [x] Analyze slow queries
  - [x] Add missing indexes
  - [x] Optimize N+1 queries
- [x] Verify performance requirements
  - [x] < 100ms for cached queries (P95)
  - [x] < 10s for fresh data (P95)
  - [x] > 80% cache hit rate

### Task 7.4: Manual Testing

- [x] Test with empty database
  - [x] Verify auto-population works
  - [x] Verify data is stored correctly
  - [x] Verify subsequent requests use cache
- [x] Test with stale data
  - [x] Manually set old timestamps
  - [x] Verify refresh triggers
  - [x] Verify new data is fetched
- [x] Test error scenarios
  - [x] Disconnect database
  - [x] Block scraping endpoints
  - [x] Simulate timeouts
  - [x] Verify graceful degradation
- [x] Test admin endpoints
  - [x] Manual sync trigger
  - [x] Cache clearing
  - [x] Health checks

---

## Phase 8: Documentation & Deployment (Week 4)

### Task 8.1: Code Documentation

- [x] Update all docstrings
  - [x] Add examples for complex functions
  - [x] Document parameters and return types
  - [x] Add usage notes
- [x] Add inline comments for complex logic
- [x] Update type hints for all functions
- [x] Generate API documentation
  - [x] Use `pdoc` or `sphinx`
  - [x] Host documentation

### Task 8.2: API Documentation

- [x] Update OpenAPI/Swagger docs
  - [x] Document new endpoints
  - [x] Document new query parameters
  - [x] Document response metadata
- [x] Add request/response examples
- [x] Document error responses
- [x] Update Postman collection (if exists)

### Task 8.3: Architecture Documentation

- [x] Update `services/README.md`
  - [x] Document hybrid architecture
  - [x] Add data flow diagrams
  - [x] Document caching strategy
  - [x] Add troubleshooting guide
- [x] Create architecture diagrams
  - [x] Data flow diagram
  - [x] Component diagram
  - [x] Sequence diagrams for key flows
- [x] Document deployment process
  - [x] Environment variables
  - [x] Database migrations
  - [x] Initial data population

### Task 8.4: Deployment Preparation

- [x] Create deployment checklist
  - [x] Run database migrations
  - [x] Update environment variables
  - [x] Clear old cache
  - [x] Trigger initial data sync
- [x] Create rollback plan
  - [x] Database rollback scripts
  - [x] Code rollback procedure
  - [x] Data backup strategy
- [x] Set up monitoring
  - [x] Add logging for key operations
  - [x] Set up alerts for errors
  - [x] Monitor cache hit rate
  - [x] Monitor scraping frequency
- [x] Create runbook
  - [x] Common issues and solutions
  - [x] Manual sync procedures
  - [x] Cache management
  - [x] Emergency procedures

### Task 8.5: Deployment

- [x] Deploy to staging environment
  - [x] Run migrations
  - [x] Test all endpoints
  - [x] Verify auto-population
  - [x] Monitor for errors
- [x] Perform smoke tests
  - [x] Test critical paths
  - [x] Verify data population
  - [x] Check performance
- [x] Deploy to production
  - [x] Run migrations
  - [x] Trigger initial data sync
  - [x] Monitor closely for 24 hours
  - [x] Verify cache warming
- [x] Post-deployment verification
  - [x] Check all endpoints
  - [x] Verify data freshness
  - [x] Monitor error rates
  - [x] Check performance metrics

---

## Phase 9: Monitoring & Optimization (Ongoing)

### Task 9.1: Set Up Monitoring

- [x] Configure logging
  - [x] Structured JSON logs
  - [x] Log rotation
  - [x] Error aggregation
- [x] Set up metrics collection
  - [x] Cache hit rate
  - [x] API response times
  - [x] Scraping frequency
  - [x] Error rates
- [x] Create dashboards
  - [x] System health dashboard
  - [x] Performance dashboard
  - [x] Data freshness dashboard
- [x] Set up alerts
  - [x] High error rate
  - [x] Low cache hit rate
  - [x] Slow response times
  - [x] Failed scraping jobs

### Task 9.2: Performance Optimization

- [x] Analyze slow queries
  - [x] Use database query analyzer
  - [x] Add missing indexes
  - [x] Optimize complex queries
- [x] Optimize cache usage
  - [x] Adjust TTLs based on usage patterns
  - [x] Implement cache warming for common queries
  - [x] Tune cache size limits
- [x] Optimize scraping
  - [x] Batch scraping operations
  - [x] Implement smart scheduling
  - [x] Reduce redundant scraping
- [x] Profile code for bottlenecks
  - [x] Use `cProfile` or `py-spy`
  - [x] Optimize hot paths
  - [x] Reduce unnecessary operations

### Task 9.3: Continuous Improvement

- [x] Collect user feedback
  - [x] Response time satisfaction
  - [x] Data accuracy
  - [x] Feature requests
- [x] Analyze usage patterns
  - [x] Most requested courses/semesters
  - [x] Peak usage times
  - [x] Common error scenarios
- [x] Iterate on implementation
  - [x] Adjust staleness thresholds
  - [x] Improve error messages
  - [x] Add new features based on feedback
- [x] Regular maintenance
  - [x] Review and clean up logs
  - [x] Archive old data
  - [x] Update dependencies
  - [x] Security patches

---

## Success Criteria Checklist

### Functional Success

- [x] System works with empty database
- [x] Auto-populates missing data on first request
- [x] Direct DB access for simple operations (< 100ms)
- [x] MCP tools for complex operations (< 5s)
- [x] Cache hit rate > 80% after warmup
- [x] All MCP tools have auto-enrichment
- [x] All API endpoints return metadata
- [x] Error handling provides meaningful messages

### Performance Success

- [x] Cached queries < 100ms (P95)
- [x] Fresh data queries < 10s (P95)
- [x] Schedule optimization < 5s (P95)
- [x] System handles 100 concurrent users
- [x] System handles 1000 requests/minute

### Quality Success

- [x] Code coverage > 80%
- [x] All tests passing
- [x] No critical bugs
- [x] Documentation complete
- [x] API docs updated
- [x] Deployment successful

### User Experience Success

- [x] No manual data seeding required
- [x] Immediate value on first use
- [x] Transparent data freshness
- [x] Helpful error messages
- [x] Fast response times
