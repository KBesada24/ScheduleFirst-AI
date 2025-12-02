# Deployment Guide

## Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL database (or Supabase account)
- Google Gemini API key
- Chrome/Chromium (for web scraping)

## Environment Variables

### Required Variables

```bash
# Google Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# Supabase Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key
```

### Optional Variables

```bash
# Direct PostgreSQL (if not using Supabase client)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Environment
ENVIRONMENT=production  # or development
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json  # or text

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Cache
CACHE_TTL=3600

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# Scraping
SCRAPER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
SCRAPER_REQUEST_DELAY=2.0
SCRAPER_MAX_RETRIES=3

# Error Tracking (optional)
SENTRY_DSN=your_sentry_dsn
```

## Database Setup

### 1. Run Migrations

```bash
cd services

# If using Supabase CLI
supabase db push

# Or run SQL directly
psql $DATABASE_URL -f migrations/001_hybrid_impl.sql
```

### 2. Verify Tables

Required tables:
- `courses`
- `course_sections`
- `professors`
- `professor_reviews`
- `user_schedules`
- `sync_metadata`

```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';
```

### 3. Verify Indexes

```sql
-- Check indexes exist
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('courses', 'professors', 'sync_metadata');
```

## Backend Deployment

### Option 1: Direct Python

```bash
cd services

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements/base.txt

# Start API server
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000

# In separate terminal: Start background scheduler
python -m background_jobs.scheduler
```

### Option 2: Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Chrome for scraping
RUN apt-get update && apt-get install -y \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install -r requirements/base.txt

COPY . .

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t schedulefirst-backend .
docker run -p 8000:8000 --env-file .env schedulefirst-backend
```

### Option 3: Railway/Fly.io

```bash
# Railway
railway up

# Fly.io
fly deploy
```

## Initial Data Population

After deployment, trigger initial data sync:

```bash
# Via API endpoint
curl -X POST http://localhost:8000/api/admin/sync \
  -H "Content-Type: application/json" \
  -d '{"entity_type": "courses", "semester": "Spring 2025", "university": "Baruch College"}'

# Check sync status
curl http://localhost:8000/api/admin/sync-status?entity_type=courses&semester=Spring%202025&university=Baruch%20College
```

Or let auto-population work on first user request.

## Health Verification

### 1. Health Check Endpoint

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "environment": "production",
  "gemini_api": "configured",
  "circuit_breakers": {
    "ratemyprof": "closed",
    "cuny_scraper": "closed",
    "supabase": "closed",
    "gemini": "closed"
  }
}
```

### 2. API Endpoint Test

```bash
# Test courses endpoint
curl "http://localhost:8000/api/courses?semester=Spring%202025&university=Baruch%20College"

# Test root endpoint
curl http://localhost:8000/
```

### 3. MCP Server Test

```bash
cd services
python -c "from mcp_server.tools import mcp; print('MCP loaded successfully')"
```

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (`pytest`)
- [ ] Environment variables configured
- [ ] Database migrations tested locally
- [ ] Backup existing production data (if applicable)

### Deployment Steps

1. [ ] Run database migrations
2. [ ] Deploy backend service
3. [ ] Verify `/health` endpoint returns healthy
4. [ ] Trigger initial course sync for current semester
5. [ ] Verify cache warming (check response times)

### Post-Deployment

- [ ] Monitor error logs for 1 hour
- [ ] Verify API response times < 500ms for cached requests
- [ ] Check circuit breaker states (all should be "closed")
- [ ] Verify background scheduler is running
- [ ] Test critical user flows

## Rollback Procedure

### 1. Code Rollback

```bash
# Revert to previous version
git checkout previous-tag
docker build -t schedulefirst-backend .
docker run -p 8000:8000 --env-file .env schedulefirst-backend
```

### 2. Database Rollback

```sql
-- Reverse migration (example)
ALTER TABLE courses DROP COLUMN IF EXISTS last_scraped;
ALTER TABLE courses DROP COLUMN IF EXISTS is_stale;
ALTER TABLE professors DROP COLUMN IF EXISTS last_updated;
ALTER TABLE professors DROP COLUMN IF EXISTS data_source;
DROP TABLE IF EXISTS sync_metadata;
```

### 3. Data Restoration

```bash
# Restore from backup
pg_restore -d $DATABASE_URL backup.dump
```

## Scaling Considerations

### Horizontal Scaling

- API server is stateless - can run multiple instances
- Use Redis for distributed caching (future)
- Use a load balancer (nginx, HAProxy)

### Database Scaling

- Supabase handles connection pooling
- Add read replicas for heavy read workloads
- Consider table partitioning for large datasets

### Background Jobs

- Only run one instance of the scheduler
- Or use distributed locking (Redis) for multiple instances

## Troubleshooting

### Common Issues

**Issue**: Database connection fails
```
Solution: Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
```

**Issue**: Scraping fails with timeout
```
Solution: Increase SCRAPER_REQUEST_DELAY, check if Chrome is installed
```

**Issue**: Circuit breaker open
```
Solution: Wait for recovery timeout, check external service status
```

**Issue**: High memory usage
```
Solution: Reduce CACHE_TTL or cache size, check for memory leaks
```

See [Runbook](./RUNBOOK.md) for detailed troubleshooting procedures.
