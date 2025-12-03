# CUNY Schedule Optimizer - Backend Services

Backend MCP (Model Context Protocol) server for the CUNY AI Schedule Optimizer. Built with Python, FastMCP, and integrates with Google Gemini AI.

## 🏗️ Architecture

```
services/
├── mcp_server/          # Main MCP server
│   ├── main.py          # Entry point
│   ├── config.py        # Configuration management
│   ├── models/          # Pydantic data models
│   ├── services/        # Business logic & scrapers
│   ├── tools/           # FastMCP tools
│   └── utils/           # Utilities (logging, cache, validators)
└── background_jobs/     # Scheduled tasks
    ├── scheduler.py     # APScheduler setup
    └── jobs/            # Job definitions
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Poetry (recommended) or pip
- PostgreSQL (or Supabase account)
- Google Gemini API key
- Chrome/Chromium (for web scraping)

### Installation

1. **Clone the repository**
```bash
cd services
```

2. **Install dependencies**
```bash
# Using Poetry (recommended)
poetry install

# Or using pip
pip install -r requirements/base.txt
```

3. **Set up environment variables**
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
GEMINI_API_KEY=your_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_key_here
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
```

4. **Run the MCP server**
```bash
# Using Poetry
poetry run python -m mcp_server.main

# Or directly
python -m mcp_server.main
```

## 📋 Available MCP Tools

The server exposes the following tools via FastMCP:

### 1. `fetch_course_sections`
Fetch available course sections from CUNY database.

**Parameters:**
- `course_codes`: List[str] - Course codes (e.g., ["CSC381", "MATH201"])
- `semester`: str - Semester (e.g., "Fall 2025")
- `university`: Optional[str] - CUNY school name

**Returns:** Course sections with professor, time, location, and enrollment data

### 2. `generate_optimized_schedule`
Generate optimized course schedules based on requirements and preferences.

**Parameters:**
- `required_courses`: List[str] - Required course codes
- `semester`: str - Semester
- `university`: str - CUNY school name
- `preferred_days`: Optional[List[str]] - Preferred days (e.g., ["MWF"])
- `earliest_start_time`: Optional[str] - Earliest class time (HH:MM)
- `latest_end_time`: Optional[str] - Latest class time (HH:MM)
- `min_professor_rating`: Optional[float] - Minimum professor rating
- `max_schedules`: int - Max schedules to return (default: 5)

**Returns:** Ranked optimized schedules with conflict detection

### 3. `get_professor_grade`
Get AI-generated grade (A-F) for a professor based on RateMyProfessors reviews.

**Parameters:**
- `professor_name`: str - Full name of professor
- `university`: str - CUNY school name
- `course_code`: Optional[str] - Course code to filter ratings

**Returns:** Professor grade, metrics, and review analysis

### 4. `compare_professors`
Compare multiple professors side-by-side.

**Parameters:**
- `professor_names`: List[str] - Professor names to compare
- `university`: str - CUNY school name
- `course_code`: Optional[str] - Course context

**Returns:** Comparison data with AI recommendation

### 5. `check_schedule_conflicts`
Check for conflicts in a set of course sections.

**Parameters:**
- `section_ids`: List[str] - Section IDs (UUIDs)

**Returns:** Detected conflicts with severity and suggestions

## 🤖 Background Jobs

Automated tasks run on a schedule:

### Course Sync Job
- **Schedule:** Every Sunday at 2 AM
- **Function:** Scrapes CUNY Global Search for course data
- **Updates:** Courses, sections, enrollment data

### Reviews Scrape Job
- **Schedule:** Every Monday at 3 AM
- **Function:** Scrapes RateMyProfessors for reviews
- **Updates:** Professor reviews and ratings

### Grades Update Job
- **Schedule:** Every Monday at 5 AM
- **Function:** Analyzes reviews and generates professor grades
- **Updates:** Professor composite scores and letter grades

### Running Background Jobs

```bash
# Start the scheduler
python -m background_jobs.scheduler
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_server --cov-report=html

# Run specific test file
pytest mcp_server/tests/test_schedule_optimizer.py
```

## 📊 Data Flow

```
CUNY Global Search → Scraper → PostgreSQL (Supabase)
                                      ↓
RateMyProfessors → Scraper → Review Storage
                                      ↓
                            Sentiment Analysis
                                      ↓
                            Professor Grades
                                      ↓
User Request → MCP Server → Gemini AI → Optimized Schedule
```

## 🔄 Hybrid Data Architecture

The backend uses a **database-first + on-demand population** strategy:

### Data Access Flow

1. **Cache Check** - In-memory LRU cache (< 10ms)
2. **Database Query** - Supabase PostgreSQL (< 100ms)
3. **Freshness Check** - Is data within TTL?
4. **Auto-Population** - If stale/missing, scrape fresh data (< 10s)

### Data Freshness TTLs

| Entity | TTL | 
|--------|-----|
| Course Data | 7 days |
| Professor Data | 7 days |
| Review Data | 30 days |
| Cache Entries | 300 seconds |

### Key Services

| Service | Purpose |
|---------|---------|
| `DataFreshnessService` | Checks if data is stale based on TTLs |
| `DataPopulationService` | Coordinates on-demand scraping |
| `CacheManager` | In-memory LRU cache with TTL |

### Error Resilience

- **Circuit Breakers** - Prevent cascading failures to external services
- **Fallback Chain** - Database → Cache → Scraper → Partial data with warnings
- **Retry Logic** - Exponential backoff for transient failures

See [Architecture Documentation](../docs/architecture/README.md) for detailed diagrams.

## 🔧 Configuration

All configuration is managed via environment variables in `.env`:

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `LOG_LEVEL` | Logging level (INFO, DEBUG, etc.) | No |
| `SCRAPER_REQUEST_DELAY` | Delay between scraper requests (seconds) | No |

## 📝 Logging

Logs are written to:
- **Console:** Structured JSON logs (production) or text (development)
- **Files:** 
  - `logs/app.log` - All logs (production only, with rotation)
  - `logs/error.log` - Error logs only (with rotation)

Configure via:
```env
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_MAX_BYTES=10485760  # 10MB per file
LOG_BACKUP_COUNT=5      # Keep 5 backup files
SENTRY_DSN=https://...  # Optional: Sentry error tracking
```

### Log Rotation

Logs automatically rotate when they reach `LOG_MAX_BYTES`. Old log files are preserved as backups.

### Log Cleanup

Use the cleanup script to archive and remove old logs:

```bash
# View log stats
python scripts/cleanup_logs.py --stats-only

# Archive logs older than 7 days, remove archives older than 30 days
python scripts/cleanup_logs.py

# Custom retention periods
python scripts/cleanup_logs.py --archive-days 3 --remove-days 14

# Dry run (preview actions)
python scripts/cleanup_logs.py --dry-run
```

### Error Tracking with Sentry

If `SENTRY_DSN` is configured, errors are automatically sent to Sentry for aggregation and alerting.

## 📊 Monitoring & Metrics

The backend exposes comprehensive monitoring endpoints:

### Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Overall system health with metrics summary |
| `GET /health/metrics` | Detailed metrics (requests, cache, jobs, errors) |
| `GET /health/cache` | Cache statistics and configuration |
| `GET /health/jobs` | Background job status and history |

### Metrics Collected

- **API Requests:** Count, response times, error rates per endpoint
- **Cache:** Hit rate, evictions, size
- **Background Jobs:** Run count, success/failure rate, duration
- **Scraping:** Success/failure count by scraper type
- **Usage Analytics:** Top courses, semesters, hourly distribution

### Example: View Metrics

```bash
curl http://localhost:8000/health/metrics
```

Response:
```json
{
  "uptime_seconds": 3600.5,
  "uptime_human": "1:00:00",
  "requests": {
    "total": 1500,
    "error_rate": 1.2,
    "by_endpoint": {...}
  },
  "cache": {
    "hit_rate": 85.5,
    "total_entries": 250,
    "hits": 1200,
    "misses": 200
  },
  "jobs": {
    "sync_cuny_courses": {
      "run_count": 5,
      "success_count": 5,
      "last_run": "2025-12-03T02:00:00Z"
    }
  }
}
```

### Alert Thresholds

The system logs warnings when thresholds are breached:

| Metric | Threshold | Severity |
|--------|-----------|----------|
| Cache hit rate | < 50% | Warning |
| Error rate | > 10% | Error |
| Avg response time | > 2000ms | Warning |
| Slow queries | > 500ms | Warning |

### Admin Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/admin/sync` | Trigger manual data sync |
| `GET /api/admin/sync-status` | Get sync metadata |
| `GET /api/admin/analytics` | Usage analytics summary |
| `POST /api/admin/cache/clear` | Clear the cache |
| `POST /api/feedback` | Submit user feedback |

## 🐛 Debugging

Enable debug mode:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

View detailed logs:
```bash
tail -f logs/app.log
```

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Database connection fails | Check `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` |
| Scraping timeout | Increase `SCRAPER_REQUEST_DELAY`, check Chrome installation |
| Circuit breaker open | Wait 60s for recovery, check external service status |
| Cache misses | Check cache TTL settings, verify cache is warming |
| Slow responses | Check cache hit rate, optimize database queries |

### Health Check

```bash
curl http://localhost:8000/health
```

Expected healthy response:
```json
{
  "status": "healthy",
  "database": "connected",
  "circuit_breakers": {
    "ratemyprof": "closed",
    "supabase": "closed"
  }
}
```

### Manual Sync

```bash
curl -X POST http://localhost:8000/api/admin/sync \
  -H "Content-Type: application/json" \
  -d '{"entity_type":"courses","semester":"Spring 2025","university":"Baruch College"}'
```

See [Operations Runbook](../docs/RUNBOOK.md) for detailed troubleshooting procedures.

## 🚢 Deployment

### Railway / Fly.io

1. **Set environment variables** in the dashboard
2. **Deploy:**
```bash
# Railway
railway up

# Fly.io
fly deploy
```

### Docker

```bash
# Build image
docker build -t cuny-mcp-server .

# Run container
docker run -p 8000:8000 --env-file .env cuny-mcp-server
```

## 📚 Additional Documentation

- [Architecture Guide](../docs/architecture/README.md)
- [Data Flow Diagrams](../docs/architecture/data-flow.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Monitoring Guide](../docs/MONITORING.md)
- [Operations Runbook](../docs/RUNBOOK.md)
- [Deployment Checklist](../docs/deployment-checklist.md)
- [Backend REST API](../docs/BACKEND_API.md)
- [Frontend API Documentation](../docs/API_DOCUMENTATION.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Support

- Issues: [GitHub Issues](https://github.com/your-repo/issues)
- Email: support@cunyschedule.com
- Discord: [Join our server](https://discord.gg/your-invite)

---

**Built with ❤️ for CUNY students**
