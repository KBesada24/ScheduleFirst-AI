# ScheduleFirst AI - Backend Architecture

## Overview

ScheduleFirst AI uses a **hybrid data architecture** that combines database-first access with on-demand data population. This design ensures immediate responses for cached/stored data while automatically fetching fresh data when needed.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
│                          src/lib/api-client.ts                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API SERVER (FastAPI)                               │
│                         services/api_server.py                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ /api/courses    │  │ /api/professor  │  │ /api/schedule/optimize      │  │
│  │ /api/search     │  │ /api/compare    │  │ /api/chat/message           │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌───────────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐
│   MCP TOOLS (FastMCP) │  │  CACHE LAYER    │  │    DATA POPULATION SVC      │
│ tools/schedule_opt.py │  │  utils/cache.py │  │ services/data_population.py │
│                       │  │                 │  │                             │
│ • fetch_course_sect   │  │ • In-memory LRU │  │ • ensure_course_data()      │
│ • generate_schedule   │  │ • TTL-based     │  │ • ensure_professor_data()   │
│ • get_professor_grade │  │ • 300s default  │  │ • Concurrency locks         │
│ • compare_professors  │  │                 │  │                             │
│ • check_conflicts     │  │                 │  │                             │
└───────────────────────┘  └─────────────────┘  └─────────────────────────────┘
                    │                                       │
                    ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICES LAYER                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │  SupabaseService    │  │ ConstraintSolver    │  │ SentimentAnalyzer   │  │
│  │  (Database ops)     │  │ (Schedule optimize) │  │ (Gemini AI)         │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │ DataFreshnessService│  │ CUNYScraper         │  │ RateMyProfScraper   │  │
│  │ (TTL checks)        │  │ (Course data)       │  │ (Professor reviews) │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                 │                       │
                    ▼                 ▼                       ▼
┌───────────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐
│  SUPABASE (Postgres)  │  │ CUNY Global     │  │ RateMyProfessors            │
│                       │  │ Search          │  │ (GraphQL API)               │
│ • courses             │  │ (Web scraping)  │  │                             │
│ • course_sections     │  │                 │  │                             │
│ • professors          │  │                 │  │                             │
│ • professor_reviews   │  │                 │  │                             │
│ • sync_metadata       │  │                 │  │                             │
│ • user_schedules      │  │                 │  │                             │
└───────────────────────┘  └─────────────────┘  └─────────────────────────────┘
```

## Data Flow

### 1. Database-First Access (Fast Path)
```
Request → Cache Check → Database Query → Response
         (< 10ms)       (< 100ms)        Total: < 100ms
```

### 2. On-Demand Population (Slow Path)
```
Request → Cache Miss → DB Empty/Stale → DataPopulationService
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
              sync_courses_job         scrape_reviews_job       update_grades_job
                    │                         │                         │
                    ▼                         ▼                         ▼
              CUNY Scraper            RateMyProf Scraper        Sentiment Analysis
                    │                         │                         │
                    └─────────────────────────┼─────────────────────────┘
                                              ▼
                                     Database Insert
                                              │
                                              ▼
                                      Response (< 10s)
```

## Key Components

### MCP Server (`mcp_server/`)
The Model Context Protocol server exposes AI-callable tools:

| Tool | Purpose |
|------|---------|
| `fetch_course_sections` | Get course sections with auto-population |
| `generate_optimized_schedule` | AI-powered schedule optimization |
| `get_professor_grade` | Get professor rating with sentiment analysis |
| `compare_professors` | Side-by-side professor comparison |
| `check_schedule_conflicts` | Detect time/location conflicts |

### Services Layer (`mcp_server/services/`)

| Service | Responsibility |
|---------|---------------|
| `supabase_service` | All database CRUD operations |
| `constraint_solver` | Schedule optimization algorithm |
| `sentiment_analyzer` | Gemini-powered review analysis |
| `data_population_service` | On-demand data fetching coordination |
| `data_freshness_service` | TTL checking and staleness detection |
| `cuny_global_search_scraper` | CUNY course data scraping |
| `ratemyprof_scraper` | RateMyProfessors API integration |

### Utilities (`mcp_server/utils/`)

| Utility | Purpose |
|---------|---------|
| `cache.py` | In-memory LRU cache with TTL |
| `circuit_breaker.py` | Failure protection for external services |
| `exceptions.py` | Custom exception hierarchy |
| `logger.py` | Structured JSON logging |
| `validators.py` | Input validation helpers |

### Background Jobs (`background_jobs/`)

| Job | Schedule | Purpose |
|-----|----------|---------|
| `sync_cuny_courses` | Sunday 2 AM | Bulk course data refresh |
| `scrape_reviews` | Monday 3 AM | Professor review updates |
| `update_professor_grades` | Monday 5 AM | Recalculate grades from reviews |

## Data Freshness Strategy

### TTL Values
| Entity | TTL | Rationale |
|--------|-----|-----------|
| Course Data | 7 days | Course schedules change weekly |
| Professor Data | 7 days | Reviews accumulate slowly |
| Review Data | 30 days | Historical data, changes rarely |
| Cache Entries | 300 seconds | Balance freshness vs. performance |

### Freshness Check Flow
```python
# Pseudo-code for data access
async def get_data(entity_type, **params):
    # 1. Check cache
    cached = await cache.get(key)
    if cached:
        return cached  # < 10ms
    
    # 2. Check database
    db_data = await supabase.get(entity_type, params)
    
    # 3. Check freshness
    if db_data and await freshness_service.is_fresh(entity_type, params):
        await cache.set(key, db_data)
        return db_data  # < 100ms
    
    # 4. Trigger population if stale/missing
    await population_service.ensure_data(entity_type, params)
    
    # 5. Fetch fresh data
    fresh_data = await supabase.get(entity_type, params)
    await cache.set(key, fresh_data)
    return fresh_data  # < 10s
```

## Error Handling

### Exception Hierarchy
```
ScheduleOptimizerError (base)
├── DataNotFoundError      → 404 Not Found
├── DataStaleError         → 200 with warning
├── ValidationError        → 400 Bad Request
├── DatabaseError          → 503 Service Unavailable
├── ScrapingError          → 502 Bad Gateway
├── RateLimitError         → 429 Too Many Requests
├── CircuitBreakerOpenError → 503 Service Unavailable
└── ExternalServiceError   → 502 Bad Gateway
```

### Circuit Breaker Pattern
Each external service has a circuit breaker:

| Service | Failure Threshold | Recovery Timeout |
|---------|-------------------|------------------|
| RateMyProfessors | 5 failures | 60 seconds |
| CUNY Scraper | 5 failures | 60 seconds |
| Supabase | 10 failures | 30 seconds |
| Gemini API | 5 failures | 120 seconds |

**States:**
- `CLOSED`: Normal operation, requests pass through
- `OPEN`: Service failing, requests immediately rejected
- `HALF_OPEN`: Testing recovery, limited requests allowed

## Configuration

### Required Environment Variables
```bash
# API Keys
GEMINI_API_KEY=         # Google Gemini API key

# Supabase
SUPABASE_URL=           # Supabase project URL
SUPABASE_SERVICE_ROLE_KEY=  # Service role key
SUPABASE_ANON_KEY=      # Anonymous key

# Optional
DATABASE_URL=           # Direct PostgreSQL connection
REDIS_URL=              # Redis for distributed caching (future)
LOG_LEVEL=INFO          # Logging level
ENVIRONMENT=development # Environment name
```

### Performance Tuning
```bash
# Cache
CACHE_TTL=3600          # Default cache TTL (seconds)

# Scraping
SCRAPER_REQUEST_DELAY=2.0   # Delay between scraper requests
SCRAPER_MAX_RETRIES=3       # Max retry attempts

# Rate Limiting
RATE_LIMIT_REQUESTS=100     # Requests per period
RATE_LIMIT_PERIOD=60        # Period in seconds
```

## File Structure

```
services/
├── api_server.py              # FastAPI REST server
├── mcp_server/
│   ├── main.py                # MCP server entry point
│   ├── config.py              # Configuration management
│   ├── models/                # Pydantic data models
│   │   ├── api_models.py      # API response models
│   │   ├── course.py          # Course/section models
│   │   ├── professor.py       # Professor/review models
│   │   ├── schedule.py        # Schedule/constraint models
│   │   └── sync_metadata.py   # Sync tracking model
│   ├── services/              # Business logic
│   │   ├── constraint_solver.py
│   │   ├── cuny_global_search_scraper.py
│   │   ├── data_freshness_service.py
│   │   ├── data_population_service.py
│   │   ├── ratemyprof_scraper.py
│   │   ├── sentiment_analyzer.py
│   │   └── supabase_service.py
│   ├── tools/                 # MCP tool definitions
│   │   └── schedule_optimizer.py
│   └── utils/                 # Utilities
│       ├── cache.py
│       ├── circuit_breaker.py
│       ├── exceptions.py
│       ├── logger.py
│       └── validators.py
├── background_jobs/
│   ├── scheduler.py           # APScheduler setup
│   └── jobs/
│       ├── scrape_reviews.py
│       ├── sync_cuny_courses.py
│       └── update_professor_grades.py
└── migrations/
    └── 001_hybrid_impl.sql
```

## Related Documentation

- [Deployment Guide](../DEPLOYMENT.md)
- [Monitoring Guide](../MONITORING.md)
- [Runbook](../RUNBOOK.md)
- [API Documentation](../API_DOCUMENTATION.md)
