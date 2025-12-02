# Operations Runbook

## Quick Reference

| Issue | First Action |
|-------|--------------|
| API not responding | Check health endpoint, restart service |
| Database disconnected | Check Supabase status, verify credentials |
| Circuit breaker open | Wait for recovery, check external service |
| Slow responses | Check cache hit rate, check database |
| Scraping failures | Check Chrome installation, rate limits |

---

## Common Procedures

### 1. Manual Data Sync

**When to use:** Data is stale or missing for a semester/university.

```bash
# Sync courses for a semester
curl -X POST http://localhost:8000/api/admin/sync \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "courses",
    "semester": "Spring 2025",
    "university": "Baruch College",
    "force": true
  }'

# Check sync status
curl "http://localhost:8000/api/admin/sync-status?entity_type=courses&semester=Spring%202025&university=Baruch%20College"
```

**Expected response:**
```json
{
  "entity_type": "courses",
  "semester": "Spring 2025",
  "university": "Baruch College",
  "last_sync": "2025-12-02T21:00:00Z",
  "sync_status": "success"
}
```

### 2. Clear Cache

**When to use:** Stale data being served, cache inconsistency.

```python
# Via Python REPL
cd services
python

>>> from mcp_server.utils.cache import cache_manager
>>> import asyncio
>>> asyncio.run(cache_manager.clear())
>>> print("Cache cleared")
```

Or restart the API server (cache is in-memory).

### 3. Reset Circuit Breaker

**When to use:** Circuit breaker stuck open after service recovery.

```python
# Via Python REPL
cd services
python

>>> from mcp_server.utils.circuit_breaker import circuit_breaker_registry
>>> import asyncio
>>> asyncio.run(circuit_breaker_registry.reset_all())
>>> print("All circuit breakers reset")
```

Or restart the API server.

### 4. Check Background Job Status

**When to use:** Verify scheduled jobs are running.

```bash
# Check if scheduler process is running
ps aux | grep "background_jobs.scheduler"

# Check recent job logs
grep "STARTING\|COMPLETED" services/logs/app.log | tail -20
```

### 5. Force Professor Data Refresh

**When to use:** Professor has outdated grade/reviews.

```bash
curl -X POST http://localhost:8000/api/admin/sync \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "professor",
    "professor_name": "John Smith",
    "university": "Baruch College"
  }'
```

---

## Troubleshooting

### Issue: API Returns 503 Service Unavailable

**Symptoms:**
- `/health` returns `unhealthy`
- Database shows `disconnected`

**Investigation:**
```bash
# Check health endpoint
curl http://localhost:8000/health

# Check Supabase status
curl https://status.supabase.com/

# Check environment variables
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_ROLE_KEY
```

**Resolution:**
1. Verify Supabase credentials are correct
2. Check if Supabase is experiencing outage
3. Restart API server
4. If persistent, check network connectivity

### Issue: Circuit Breaker Open for RateMyProfessors

**Symptoms:**
- Professor grade requests failing
- Health shows `circuit_breakers.ratemyprof: "open"`

**Investigation:**
```bash
# Check recent RMP errors
grep "ratemyprof" services/logs/error.log | tail -20

# Check RMP status
curl -I https://www.ratemyprofessors.com
```

**Resolution:**
1. Wait for recovery timeout (60 seconds)
2. If RMP is down, data will come from cache/database
3. If rate limited, wait longer or reduce scraping frequency
4. Reset circuit breaker if service is healthy

### Issue: Slow API Responses

**Symptoms:**
- Response times > 500ms for cached requests
- Response times > 30s for fresh requests

**Investigation:**
```bash
# Check cache hit rate
python -c "from mcp_server.utils.cache import cache_manager; print(cache_manager.get_stats())"

# Check database query times (in logs)
grep "Database error\|timeout" services/logs/app.log | tail -20
```

**Resolution:**
1. If low cache hit rate:
   - Increase cache TTL
   - Pre-warm cache with common queries
2. If database slow:
   - Check Supabase dashboard for slow queries
   - Add missing indexes
3. If scraping slow:
   - Check external service response times
   - Increase timeout values

### Issue: Scraping Fails with Chrome Errors

**Symptoms:**
- Course sync job fails
- Errors mention WebDriver or Chrome

**Investigation:**
```bash
# Check Chrome installation
which chromium-browser || which google-chrome

# Check ChromeDriver
chromedriver --version

# Check scraper logs
grep "WebDriver\|Chrome" services/logs/error.log | tail -20
```

**Resolution:**
1. Install Chrome/Chromium:
   ```bash
   apt-get update && apt-get install -y chromium-browser
   ```
2. Install ChromeDriver:
   ```bash
   pip install webdriver-manager
   ```
3. Restart API server

### Issue: Data Not Auto-Populating

**Symptoms:**
- Empty responses for new semesters
- No scraping triggered

**Investigation:**
```bash
# Check population service logs
grep "DataPopulation\|ensure_" services/logs/app.log | tail -20

# Check freshness service
grep "is_fresh\|stale" services/logs/app.log | tail -20
```

**Resolution:**
1. Check if `auto_populate=true` (default) in request
2. Check sync_metadata for errors
3. Manually trigger sync (see procedure #1)
4. Check circuit breakers aren't blocking scrapers

### Issue: Memory Usage High

**Symptoms:**
- Service using > 1GB RAM
- OOM kills

**Investigation:**
```bash
# Check process memory
ps aux | grep "api_server\|uvicorn"

# Check cache size
python -c "from mcp_server.utils.cache import cache_manager; print(cache_manager.get_stats())"
```

**Resolution:**
1. Reduce cache size limit in config
2. Decrease cache TTL
3. Restart service to clear memory
4. Check for memory leaks in custom code

---

## Emergency Procedures

### Complete Service Restart

```bash
# Stop all services
pkill -f "api_server"
pkill -f "background_jobs.scheduler"

# Clear logs (optional)
rm services/logs/*.log

# Restart
cd services
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 &
python -m background_jobs.scheduler &
```

### Rollback to Previous Version

```bash
# Stop services
pkill -f "api_server"

# Checkout previous version
git log --oneline -5  # Find last good commit
git checkout <commit-hash>

# Restart
cd services
pip install -r requirements/base.txt
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 &
```

### Database Rollback

```sql
-- Connect to database
psql $DATABASE_URL

-- Check current state
SELECT * FROM sync_metadata ORDER BY last_sync DESC LIMIT 10;

-- Delete bad sync data if needed
DELETE FROM sync_metadata WHERE sync_status = 'failed';

-- Reset stale flags
UPDATE courses SET is_stale = false;
```

---

## Contact & Escalation

1. **First line:** Check this runbook, check logs
2. **Second line:** Check external service status pages
3. **Escalation:** Review recent deployments, code changes
