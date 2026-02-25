# Technical Design: Fix Missing `sync_metadata` Table

## Architecture Overview

The `sync_metadata` table is the lynchpin of the data freshness system. It sits between the AI tool layer and the external scrapers, acting as a cache-invalidation ledger. When working correctly, the flow is:

```
AI Chat Request
    └── fetch_course_sections (MCP Tool)
            └── DataPopulationService.ensure_course_data()
                    ├── [Cache check] In-memory cache (60s TTL)
                    ├── [DB check]   DataFreshnessService.is_course_data_fresh()
                    │                   └── SupabaseService.get_sync_metadata()
                    │                           └── SELECT from sync_metadata  ← THIS TABLE IS MISSING
                    │
                    ├── IF fresh → return immediately (no scrape)
                    └── IF stale → CUNYGlobalSearchScraper → upsert courses → update sync_metadata
```

Without the table, every call to `get_sync_metadata()` throws a `PGRST205 DatabaseError`, which is caught in `is_course_data_fresh()` and interpreted as "data is not fresh," unconditionally triggering the scraper.

---

## Data Model

### `sync_metadata` Table

```sql
CREATE TABLE IF NOT EXISTS sync_metadata (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type  VARCHAR(50) NOT NULL,          -- 'courses', 'professors', 'reviews'
    semester     VARCHAR(50),                   -- e.g. 'Spring 2026'
    university   VARCHAR(100),                  -- e.g. 'College of Staten Island'
    last_sync    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sync_status  VARCHAR(20) NOT NULL,          -- 'success', 'failed', 'in_progress'
    error_message TEXT,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sync_metadata_lookup
    ON sync_metadata(entity_type, semester, university);
```

### Corresponding Pydantic Model (already exists, no changes needed)

```python
# services/mcp_server/models/sync_metadata.py
class SyncMetadata(BaseModel):
    id: UUID
    entity_type: str          # 'courses' | 'professors' | 'reviews'
    semester: Optional[str]
    university: Optional[str]
    last_sync: datetime
    sync_status: str          # 'success' | 'failed' | 'in_progress'
    error_message: Optional[str]
    created_at: datetime
```

### Row Lifecycle

| Event | `sync_status` | `last_sync` | `error_message` |
|-------|--------------|-------------|-----------------|
| Sync starts | `in_progress` | — | `null` |
| Sync succeeds | `success` | now() | `null` |
| Sync fails | `failed` | — | error text |

---

## Component Interactions

### Affected Services (all already implemented)

| Component | File | Role |
|-----------|------|------|
| `SupabaseService` | `supabase_service.py` | `get_sync_metadata()`, `update_sync_metadata()`, `get_stale_entities()` |
| `DataFreshnessService` | `data_freshness_service.py` | TTL checks, `is_course_data_fresh()`, `mark_sync_in_progress()`, `mark_sync_complete()` |
| `DataPopulationService` | `data_population_service.py` | Orchestrates checks and triggers sync jobs |
| `schedule_optimizer.py` (MCP tool) | `tools/schedule_optimizer.py` | Entry point — calls `DataPopulationService.ensure_course_data()` |

### TTL Configuration (in `DataFreshnessService`)

| Entity | TTL |
|--------|-----|
| `courses` | 7 days |
| `professors` | 7 days |
| `reviews` | 30 days |

### Caching Layers

There are two caching layers stacked on top of `sync_metadata`:

1. **In-memory cache** (`cache_manager`, 60s TTL) — checked first in `ensure_course_data()`, keyed as `population:courses:{semester}:{university}`
2. **`sync_metadata` DB table** (7-day TTL) — checked second via `is_course_data_fresh()`

This means: after the first successful scrape, subsequent requests within 60 seconds skip the DB entirely. Requests within 7 days skip the scraper. Only after 7 days is a new scrape triggered.

---

## Migration Design

The fix is entirely a **database migration** — no Python code changes are required.

### Migration File (already exists)

[`services/migrations/001_hybrid_impl.sql`](file:///home/kbesada/Code/ScheduleFirst-AI/services/migrations/001_hybrid_impl.sql)

This file:
1. Alters `courses` table → adds `last_scraped` (TIMESTAMP WITH TIME ZONE) and `is_stale` (BOOLEAN) columns
2. Alters `professors` table → adds `last_updated` (TIMESTAMP WITH TIME ZONE) and `data_source` (VARCHAR 50) columns
3. Creates `sync_metadata` table with lookup index

All statements use `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` — **idempotent and safe to re-run**.

### Execution Method Options

| Option | How | Risk |
|--------|-----|------|
| **A: Supabase SQL Editor** (Recommended) | Dashboard → SQL Editor → paste → Run | Zero risk, immediate |
| **B: Supabase CLI** | `supabase db push` after adding to `supabase/migrations/` | Requires CLI setup |
| **C: psql direct** | `psql $DATABASE_URL < 001_hybrid_impl.sql` | Requires direct DB access credential |

---

## Error Handling (existing behavior after fix)

| Scenario | Behavior |
|----------|----------|
| Table missing (current) | `PGRST205` → caught in `is_course_data_fresh()` → returns `False` → scraper triggered every time |
| Table exists, no record | `get_sync_metadata()` returns `None` → `is_course_data_fresh()` returns `False` → scraper triggered (correct first-time behavior) |
| Table exists, fresh record | `get_sync_metadata()` returns metadata → TTL check passes → returns `True` → **no scrape** |
| Table exists, stale record | TTL check fails → returns `False` → scraper triggered (correct re-sync behavior) |
| DB temporarily unavailable | Circuit breaker opens → `DatabaseError` → caught → falls back to scrape |

---

## Security Considerations

- Backend uses the Supabase **service role key** (`SUPABASE_SERVICE_ROLE_KEY` in `.env`) for all DB operations — bypasses RLS
- `sync_metadata` tracks only scraping status, no user PII
- No new API endpoints are exposed by this change

---

## Testing Strategy

### Existing Unit Tests (no changes needed, already mock the DB)

- `test_data_freshness_service.py` — Tests all freshness/staleness states
- `test_supabase_service.py` — Tests `get_sync_metadata` and `update_sync_metadata`
- `test_data_population_service.py` — Tests orchestration logic

### Integration Verification (manual, after migration)

1. Run migration against Supabase
2. Restart the FastAPI server
3. Send an AI chat message asking for courses — observe logs:
   - ✅ No `PGRST205` errors
   - ✅ `mark_sync_in_progress` succeeds (or logs graceful warning if scrape not needed)
4. Wait for first scrape to complete, then send the same message again:
   - ✅ `is_course_data_fresh()` returns `True`
   - ✅ No "Starting scrape" log line — response returns in < 500ms
