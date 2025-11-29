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
  - [ ] Test with empty database
  - [ ] Test with stale data
  - [ ] Test with fresh data (should skip)

---

## Phase 3: Enhanced MCP Tools (Week 2-3)

### Task 3.1: Update `fetch_course_sections` MCP Tool

- [ ] Update `mcp_server/tools/schedule_optimizer.py`
- [ ] Modify `fetch_course_sections()` function
  - [ ] Add auto-population logic at start
  - [ ] Call `data_population_service.ensure_course_data(semester, university)`
  - [ ] Add try-except for graceful error handling
  - [ ] Return metadata about data source (cache/db/scraper)
- [ ] Update return format to include metadata
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
- [ ] Add logging for data access patterns
- [ ] Test with empty database
- [ ] Test with stale data
- [ ] Test with fresh data

### Task 3.2: Update `get_professor_grade` MCP Tool

- [ ] Modify `get_professor_grade()` and `_get_professor_grade_impl()`
- [ ] Add auto-enrichment logic
  - [ ] Check if professor exists in DB
  - [ ] Check if data is fresh
  - [ ] If missing/stale, call `data_population_service.ensure_professor_data()`
  - [ ] Fetch from DB after population
- [ ] Implement fallback chain
  - [ ] Primary: Database lookup
  - [ ] Secondary: Scrape RateMyProfessors
  - [ ] Tertiary: Return partial data with warning
- [ ] Update return format with metadata
- [ ] Add comprehensive error handling
  - [ ] Handle scraping failures
  - [ ] Handle sentiment analysis failures
  - [ ] Handle database failures
- [ ] Test all fallback scenarios
- [ ] Add logging for each step

### Task 3.3: Update `generate_optimized_schedule` MCP Tool

- [ ] Modify `generate_optimized_schedule()` function
- [ ] Add dependency checking
  - [ ] Ensure course data exists for all required courses
  - [ ] Ensure professor data exists for all professors in sections
  - [ ] Auto-populate if missing
- [ ] Add parallel data population
  - [ ] Use `asyncio.gather()` to populate multiple courses concurrently
  - [ ] Limit concurrency to avoid overwhelming scrapers
- [ ] Update error handling
  - [ ] Handle partial data availability
  - [ ] Provide meaningful error messages
  - [ ] Suggest alternatives if data unavailable
- [ ] Test with various scenarios
  - [ ] All data available
  - [ ] Some data missing
  - [ ] All data missing
  - [ ] Scraping failures

### Task 3.4: Update `compare_professors` MCP Tool

- [ ] Modify `compare_professors()` function
- [ ] Add auto-enrichment for all professors
  - [ ] Populate data for each professor
  - [ ] Handle failures for individual professors
  - [ ] Continue comparison with available data
- [ ] Update comparison logic
  - [ ] Handle missing data gracefully
  - [ ] Indicate data quality in results
  - [ ] Adjust recommendations based on data completeness
- [ ] Test comparison scenarios
  - [ ] All professors have data
  - [ ] Some professors missing data
  - [ ] Mixed data quality

### Task 3.5: Update `check_schedule_conflicts` MCP Tool

- [ ] Implement `get_section_by_id()` in Supabase service (currently TODO)
- [ ] Modify `check_schedule_conflicts()` function
- [ ] Add section data fetching
  - [ ] Fetch all sections by ID
  - [ ] Handle missing sections
  - [ ] Auto-populate if needed
- [ ] Test conflict detection
  - [ ] Time overlaps
  - [ ] Travel time conflicts
  - [ ] Missing section data

---

## Phase 4: REST API Enhancements (Week 3)

### Task 4.1: Update Simple CRUD Endpoints

- [ ] Update `api_server.py`
- [ ] Modify `GET /api/courses`
  - [ ] Add `auto_populate: bool = True` query parameter
  - [ ] If `auto_populate=true` and data missing, trigger population
  - [ ] Add metadata to response
  - [ ] Add error handling for population failures
- [ ] Modify `GET /api/professor/{name}`
  - [ ] Add `auto_populate: bool = True` query parameter
  - [ ] Auto-enrich if missing
  - [ ] Return metadata
- [ ] Modify `POST /api/courses/search`
  - [ ] Add auto-population for search results
  - [ ] Handle partial results
- [ ] Add response metadata to all endpoints
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
- [ ] Test all endpoints with `auto_populate=true/false`

### Task 4.2: Update Complex Operation Endpoints

- [ ] Verify `POST /api/schedule/optimize` uses MCP tools
  - [ ] Should already have auto-population via MCP tool
  - [ ] Add metadata to response
  - [ ] Test end-to-end flow
- [ ] Verify `POST /api/chat/message` uses Gemini with MCP tools
  - [ ] Ensure MCP tools are accessible to Gemini
  - [ ] Test AI can trigger data population
  - [ ] Add logging for MCP tool usage
- [ ] Add new endpoint `POST /api/professor/compare`
  - [ ] Accept list of professor names
  - [ ] Call `compare_professors` MCP tool
  - [ ] Return comparison with metadata
- [ ] Test all complex endpoints

### Task 4.3: Add Admin/Utility Endpoints

- [ ] Create `POST /api/admin/sync` endpoint
  - [ ] Trigger manual data sync
  - [ ] Accept parameters: entity_type, semester, university
  - [ ] Require admin authentication (future)
  - [ ] Return sync status
- [ ] Create `GET /api/admin/sync-status` endpoint
  - [ ] Return sync metadata for all entities
  - [ ] Show last sync times
  - [ ] Show sync statuses
- [ ] Create `POST /api/admin/cache/clear` endpoint
  - [ ] Clear in-memory cache
  - [ ] Return cache statistics
- [ ] Create `GET /health/cache` endpoint
  - [ ] Return cache hit rate
  - [ ] Return cache size
  - [ ] Return cache entries count
- [ ] Test admin endpoints
- [ ] Document admin endpoints in OpenAPI

---

## Phase 5: Caching Improvements (Week 3-4)

### Task 5.1: Enhance Cache Manager

- [ ] Update `utils/cache.py`
- [ ] Add cache statistics tracking
  - [ ] Track hits/misses
  - [ ] Track cache size
  - [ ] Track eviction count
- [ ] Implement LRU eviction policy
  - [ ] Track access times
  - [ ] Evict least recently used when size limit reached
  - [ ] Set max cache size (1000 entries or 10MB)
- [ ] Add cache warming functionality
  - [ ] `warm_cache(entity_type, **kwargs)` - Pre-populate cache
  - [ ] Warm common queries on startup
- [ ] Add cache monitoring
  - [ ] Log cache statistics periodically
  - [ ] Alert on low hit rate
- [ ] Test cache behavior
  - [ ] Test eviction policy
  - [ ] Test size limits
  - [ ] Test TTL expiration

### Task 5.2: Implement Smart Caching in Services

- [ ] Update `SupabaseService`
  - [ ] Add `@cache_manager.cached()` decorator to read methods
  - [ ] Use appropriate cache keys
  - [ ] Set appropriate TTLs
- [ ] Update `DataPopulationService`
  - [ ] Cache population results
  - [ ] Invalidate cache on new data
- [ ] Update MCP tools
  - [ ] Cache expensive operations
  - [ ] Cache professor grades
  - [ ] Cache optimized schedules
- [ ] Test caching integration
  - [ ] Verify cache hits
  - [ ] Verify cache invalidation
  - [ ] Measure performance improvement

---

## Phase 6: Error Handling & Resilience (Week 4)

### Task 6.1: Implement Comprehensive Error Handling

- [ ] Create custom exception classes
  - [ ] `DataNotFoundError` - Entity not found
  - [ ] `DataStaleError` - Data too old
  - [ ] `ScrapingError` - Scraping failed
  - [ ] `PopulationError` - Population failed
- [ ] Update all services with error handling
  - [ ] Catch specific exceptions
  - [ ] Log with context
  - [ ] Return user-friendly messages
- [ ] Implement retry logic
  - [ ] Use `tenacity` library (already in use)
  - [ ] Configure retries per operation type
  - [ ] Exponential backoff
- [ ] Add circuit breaker pattern
  - [ ] Track failure rates
  - [ ] Open circuit after threshold
  - [ ] Auto-recover after cooldown
- [ ] Test error scenarios
  - [ ] Database failures
  - [ ] Scraping failures
  - [ ] Network failures
  - [ ] Timeout scenarios

### Task 6.2: Implement Fallback Mechanisms

- [ ] Create fallback chain for each operation
  - [ ] Primary: Database
  - [ ] Secondary: Cache
  - [ ] Tertiary: Scraper
  - [ ] Final: Partial data with warnings
- [ ] Implement graceful degradation
  - [ ] Return partial results if some data unavailable
  - [ ] Include warnings in response
  - [ ] Suggest alternatives
- [ ] Test fallback scenarios
  - [ ] Each level of fallback
  - [ ] Complete failure handling
  - [ ] Partial data scenarios

---

## Phase 7: Testing & Quality Assurance (Week 4)

### Task 7.1: Unit Tests

- [ ] Write tests for `DataFreshnessService`
  - [ ] Test staleness detection
  - [ ] Test edge cases
  - [ ] Test with missing data
- [ ] Write tests for `DataPopulationService`
  - [ ] Test successful population
  - [ ] Test concurrent requests
  - [ ] Test lock behavior
  - [ ] Test error handling
- [ ] Write tests for enhanced Supabase methods
  - [ ] Test sync metadata CRUD
  - [ ] Test staleness queries
- [ ] Write tests for updated MCP tools
  - [ ] Test auto-population
  - [ ] Test fallback logic
  - [ ] Test error scenarios
- [ ] Achieve > 80% code coverage
- [ ] Run tests: `pytest --cov=mcp_server --cov-report=html`

### Task 7.2: Integration Tests

- [ ] Test end-to-end flows
  - [ ] Empty DB → auto-populate → return data
  - [ ] Stale data → refresh → return fresh
  - [ ] Cached data → skip DB → return cached
- [ ] Test MCP tool integration
  - [ ] Tools call correct services
  - [ ] Tools handle errors gracefully
  - [ ] Tools return expected format
- [ ] Test API endpoints
  - [ ] Simple endpoints with auto-population
  - [ ] Complex endpoints with MCP tools
  - [ ] Admin endpoints
- [ ] Test background job integration
  - [ ] On-demand execution
  - [ ] Scheduled execution
  - [ ] Metadata updates

### Task 7.3: Performance Tests

- [ ] Load testing with `locust` or `k6`
  - [ ] 100 concurrent users
  - [ ] 1000 requests/minute
  - [ ] Measure response times
- [ ] Cache effectiveness testing
  - [ ] Measure hit rate
  - [ ] Verify TTL behavior
  - [ ] Test eviction policy
- [ ] Database query optimization
  - [ ] Analyze slow queries
  - [ ] Add missing indexes
  - [ ] Optimize N+1 queries
- [ ] Verify performance requirements
  - [ ] < 100ms for cached queries (P95)
  - [ ] < 10s for fresh data (P95)
  - [ ] > 80% cache hit rate

### Task 7.4: Manual Testing

- [ ] Test with empty database
  - [ ] Verify auto-population works
  - [ ] Verify data is stored correctly
  - [ ] Verify subsequent requests use cache
- [ ] Test with stale data
  - [ ] Manually set old timestamps
  - [ ] Verify refresh triggers
  - [ ] Verify new data is fetched
- [ ] Test error scenarios
  - [ ] Disconnect database
  - [ ] Block scraping endpoints
  - [ ] Simulate timeouts
  - [ ] Verify graceful degradation
- [ ] Test admin endpoints
  - [ ] Manual sync trigger
  - [ ] Cache clearing
  - [ ] Health checks

---

## Phase 8: Documentation & Deployment (Week 4)

### Task 8.1: Code Documentation

- [ ] Update all docstrings
  - [ ] Add examples for complex functions
  - [ ] Document parameters and return types
  - [ ] Add usage notes
- [ ] Add inline comments for complex logic
- [ ] Update type hints for all functions
- [ ] Generate API documentation
  - [ ] Use `pdoc` or `sphinx`
  - [ ] Host documentation

### Task 8.2: API Documentation

- [ ] Update OpenAPI/Swagger docs
  - [ ] Document new endpoints
  - [ ] Document new query parameters
  - [ ] Document response metadata
- [ ] Add request/response examples
- [ ] Document error responses
- [ ] Update Postman collection (if exists)

### Task 8.3: Architecture Documentation

- [ ] Update `services/README.md`
  - [ ] Document hybrid architecture
  - [ ] Add data flow diagrams
  - [ ] Document caching strategy
  - [ ] Add troubleshooting guide
- [ ] Create architecture diagrams
  - [ ] Data flow diagram
  - [ ] Component diagram
  - [ ] Sequence diagrams for key flows
- [ ] Document deployment process
  - [ ] Environment variables
  - [ ] Database migrations
  - [ ] Initial data population

### Task 8.4: Deployment Preparation

- [ ] Create deployment checklist
  - [ ] Run database migrations
  - [ ] Update environment variables
  - [ ] Clear old cache
  - [ ] Trigger initial data sync
- [ ] Create rollback plan
  - [ ] Database rollback scripts
  - [ ] Code rollback procedure
  - [ ] Data backup strategy
- [ ] Set up monitoring
  - [ ] Add logging for key operations
  - [ ] Set up alerts for errors
  - [ ] Monitor cache hit rate
  - [ ] Monitor scraping frequency
- [ ] Create runbook
  - [ ] Common issues and solutions
  - [ ] Manual sync procedures
  - [ ] Cache management
  - [ ] Emergency procedures

### Task 8.5: Deployment

- [ ] Deploy to staging environment
  - [ ] Run migrations
  - [ ] Test all endpoints
  - [ ] Verify auto-population
  - [ ] Monitor for errors
- [ ] Perform smoke tests
  - [ ] Test critical paths
  - [ ] Verify data population
  - [ ] Check performance
- [ ] Deploy to production
  - [ ] Run migrations
  - [ ] Trigger initial data sync
  - [ ] Monitor closely for 24 hours
  - [ ] Verify cache warming
- [ ] Post-deployment verification
  - [ ] Check all endpoints
  - [ ] Verify data freshness
  - [ ] Monitor error rates
  - [ ] Check performance metrics

---

## Phase 9: Monitoring & Optimization (Ongoing)

### Task 9.1: Set Up Monitoring

- [ ] Configure logging
  - [ ] Structured JSON logs
  - [ ] Log rotation
  - [ ] Error aggregation
- [ ] Set up metrics collection
  - [ ] Cache hit rate
  - [ ] API response times
  - [ ] Scraping frequency
  - [ ] Error rates
- [ ] Create dashboards
  - [ ] System health dashboard
  - [ ] Performance dashboard
  - [ ] Data freshness dashboard
- [ ] Set up alerts
  - [ ] High error rate
  - [ ] Low cache hit rate
  - [ ] Slow response times
  - [ ] Failed scraping jobs

### Task 9.2: Performance Optimization

- [ ] Analyze slow queries
  - [ ] Use database query analyzer
  - [ ] Add missing indexes
  - [ ] Optimize complex queries
- [ ] Optimize cache usage
  - [ ] Adjust TTLs based on usage patterns
  - [ ] Implement cache warming for common queries
  - [ ] Tune cache size limits
- [ ] Optimize scraping
  - [ ] Batch scraping operations
  - [ ] Implement smart scheduling
  - [ ] Reduce redundant scraping
- [ ] Profile code for bottlenecks
  - [ ] Use `cProfile` or `py-spy`
  - [ ] Optimize hot paths
  - [ ] Reduce unnecessary operations

### Task 9.3: Continuous Improvement

- [ ] Collect user feedback
  - [ ] Response time satisfaction
  - [ ] Data accuracy
  - [ ] Feature requests
- [ ] Analyze usage patterns
  - [ ] Most requested courses/semesters
  - [ ] Peak usage times
  - [ ] Common error scenarios
- [ ] Iterate on implementation
  - [ ] Adjust staleness thresholds
  - [ ] Improve error messages
  - [ ] Add new features based on feedback
- [ ] Regular maintenance
  - [ ] Review and clean up logs
  - [ ] Archive old data
  - [ ] Update dependencies
  - [ ] Security patches

---

## Success Criteria Checklist

### Functional Success

- [ ] System works with empty database
- [ ] Auto-populates missing data on first request
- [ ] Direct DB access for simple operations (< 100ms)
- [ ] MCP tools for complex operations (< 5s)
- [ ] Cache hit rate > 80% after warmup
- [ ] All MCP tools have auto-enrichment
- [ ] All API endpoints return metadata
- [ ] Error handling provides meaningful messages

### Performance Success

- [ ] Cached queries < 100ms (P95)
- [ ] Fresh data queries < 10s (P95)
- [ ] Schedule optimization < 5s (P95)
- [ ] System handles 100 concurrent users
- [ ] System handles 1000 requests/minute

### Quality Success

- [ ] Code coverage > 80%
- [ ] All tests passing
- [ ] No critical bugs
- [ ] Documentation complete
- [ ] API docs updated
- [ ] Deployment successful

### User Experience Success

- [ ] No manual data seeding required
- [ ] Immediate value on first use
- [ ] Transparent data freshness
- [ ] Helpful error messages
- [ ] Fast response times
