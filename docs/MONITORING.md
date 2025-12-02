# Monitoring Guide

## Health Endpoints

### Primary Health Check

```bash
GET /health
```

**Response Fields:**

| Field | Values | Meaning |
|-------|--------|---------|
| `status` | `healthy`, `degraded`, `unhealthy` | Overall system health |
| `database` | `connected`, `disconnected` | Database connection status |
| `environment` | `development`, `production` | Current environment |
| `gemini_api` | `configured`, `not configured` | Gemini API key status |
| `circuit_breakers` | Object with breaker states | External service health |

**Status Interpretation:**

- **healthy**: All services operational
- **degraded**: Some circuit breakers open, but system functional
- **unhealthy**: Database disconnected or critical failure

### Circuit Breaker States

| State | Meaning | Action |
|-------|---------|--------|
| `closed` | Normal operation | None needed |
| `open` | Service failing, requests blocked | Check external service |
| `half_open` | Testing recovery | Monitor closely |

## Logging

### Log Location

- **Console**: All logs (structured JSON in production)
- **Files** (production only):
  - `services/logs/app.log` - All logs
  - `services/logs/error.log` - Error logs only

### Log Format

**JSON Format (Production):**
```json
{
  "timestamp": "2025-12-02T21:00:00Z",
  "level": "INFO",
  "logger": "mcp_server.services.supabase_service",
  "message": "Inserted 150 courses",
  "module": "supabase_service",
  "function": "insert_courses",
  "line": 145
}
```

**Text Format (Development):**
```
2025-12-02 21:00:00 | INFO     | mcp_server.services.supabase_service | Inserted 150 courses
```

### Key Log Patterns to Monitor

#### Success Patterns
```
INFO | Database connected
INFO | Inserted/updated N courses
INFO | Scraped N reviews for professor
INFO | Cache hit: courses:...
```

#### Warning Patterns
```
WARNING | Course not found: CSC999
WARNING | Circuit breaker 'ratemyprof' opened after 5 failures
WARNING | Data is stale, triggering refresh
WARNING | Cache miss: ...
```

#### Error Patterns
```
ERROR | Database error during get_courses: timeout
ERROR | Scraping failed for RateMyProfessors: 429 rate limit
ERROR | Failed to parse course element
ERROR | Circuit breaker open, request rejected
```

### Log Level Configuration

```bash
# Environment variable
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# More verbose for development
LOG_LEVEL=DEBUG
```

## Metrics to Track

### Response Times

| Endpoint | Target P95 | Alert Threshold |
|----------|------------|-----------------|
| `GET /health` | < 50ms | > 200ms |
| `GET /api/courses` (cached) | < 100ms | > 500ms |
| `GET /api/courses` (fresh) | < 10s | > 30s |
| `POST /api/schedule/optimize` | < 5s | > 15s |

### Cache Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Hit rate | > 80% | < 50% |
| Size | < 800 entries | > 900 entries |
| Evictions/hour | < 50 | > 200 |

Access via logging or add endpoint:
```python
cache_manager.get_stats()
# Returns: { hits, misses, evictions, sets, total_entries }
```

### Circuit Breaker Metrics

| Metric | Alert Condition |
|--------|-----------------|
| State changes | > 5 per hour |
| Open duration | > 5 minutes |
| Failure count | > 10 in 5 minutes |

### Scraping Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Courses scraped/sync | > 100 | < 50 |
| Scrape duration | < 5 minutes | > 15 minutes |
| Scrape failures | 0 | > 3 |

## Alerting Recommendations

### Critical Alerts (Page immediately)

- Health status = `unhealthy`
- Database disconnected for > 1 minute
- All circuit breakers open
- Error rate > 10% in 5 minutes

### Warning Alerts (Investigate within 1 hour)

- Health status = `degraded`
- Any circuit breaker open
- Cache hit rate < 50%
- Response time P95 > threshold

### Info Alerts (Review daily)

- Sync job completed with errors
- High eviction rate
- Unusual traffic patterns

## Monitoring Commands

### Check System Status

```bash
# Health check
curl -s http://localhost:8000/health | jq .

# Check specific circuit breaker (via logs)
grep "circuit breaker" services/logs/app.log | tail -20

# Check recent errors
grep "ERROR" services/logs/error.log | tail -50
```

### Check Data Freshness

```bash
# Check sync status
curl -s "http://localhost:8000/api/admin/sync-status?entity_type=courses&semester=Spring%202025&university=Baruch%20College" | jq .
```

### Check Cache Performance

```python
# In Python REPL
from mcp_server.utils.cache import cache_manager
print(cache_manager.get_stats())
```

## Dashboard Recommendations

If setting up a monitoring dashboard (Grafana, Datadog, etc.):

### System Health Panel
- Health endpoint status (healthy/degraded/unhealthy)
- Database connection status
- Circuit breaker states (visual indicator)

### Performance Panel
- Response time histogram
- Request rate (requests/minute)
- Error rate percentage

### Cache Panel
- Hit rate gauge (target: > 80%)
- Cache size (entries)
- Eviction rate

### Data Freshness Panel
- Last sync time per entity type
- Stale entity count
- Sync job success/failure rate

### Background Jobs Panel
- Job execution history
- Duration per job
- Success/failure counts

## Periodic Maintenance

### Daily
- Review error logs
- Check cache hit rate
- Verify all circuit breakers closed

### Weekly
- Review sync job history
- Clean up old log files
- Check database query performance

### Monthly
- Analyze usage patterns
- Review and adjust TTL values
- Update dependencies
