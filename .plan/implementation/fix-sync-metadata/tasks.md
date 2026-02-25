# Implementation Tasks: Fix Missing `sync_metadata` Table

## Summary

The entire Python implementation is already complete. The only required action is running one SQL migration against the Supabase database. The tasks below cover execution, verification, and housekeeping to keep the migrations directory in sync.

---

## Phase 1: Apply the Database Migration

### TASK-001: Run the SQL migration in Supabase
**Refs**: FR-001, FR-004, FR-005  
**Estimated time**: 5 minutes  
**Owner**: Developer (manual step)

- [ ] Open the [Supabase Dashboard](https://app.supabase.com) for the ScheduleFirst-AI project
- [ ] Navigate to **SQL Editor → New Query**
- [ ] Open [`services/migrations/001_hybrid_impl.sql`](file:///home/kbesada/Code/ScheduleFirst-AI/services/migrations/001_hybrid_impl.sql) and paste the full contents
- [ ] Click **Run**
- [ ] Confirm the output shows no errors (expected: `CREATE TABLE`, `CREATE INDEX`, `ALTER TABLE` success messages)
- [ ] Navigate to **Table Editor** and verify `sync_metadata` appears in the list

---

## Phase 2: Move Migration to Canonical Location

### TASK-002: Move migration file to `supabase/migrations/`
**Estimated time**: 5 minutes  
**Rationale**: The existing migration lives in `services/migrations/` (not the Supabase CLI-managed directory). Moving it ensures it's tracked alongside the other migrations and won't be accidentally re-applied out of sequence.

- [x] Rename the file with a proper timestamp prefix: `20260101000000_add_sync_metadata.sql`
- [x] Move it to: `supabase/migrations/20260101000000_add_sync_metadata.sql`
- [ ] Keep (or delete) the original at `services/migrations/001_hybrid_impl.sql` — your choice, but document it

> [!NOTE]
> This task is housekeeping only. The migration is already applied in Task-001, so this won't re-run it. It just keeps the repo organized.

---

## Phase 3: Verification

### TASK-003: Verify no `PGRST205` errors in logs
**Estimated time**: 5 minutes  
**Refs**: FR-002, FR-003, NFR-002

- [ ] Start the FastAPI backend: `cd services && python api_server.py`
- [ ] Open the app and send a chat message asking for course information (e.g., "What sections of CSC 126 are available for Spring 2026?")
- [ ] Check server logs — confirm `PGRST205` / `Could not find the table 'public.sync_metadata'` errors are **gone**
- [ ] Confirm `mark_sync_in_progress` log appears (or at minimum, no error from it)

### TASK-004: Verify freshness caching on repeat requests
**Estimated time**: 10 minutes  
**Refs**: FR-002, NFR-001

- [ ] After the first scrape completes (even if it returns 0 courses), send the exact same message again
- [ ] Check logs — confirm **no** "Starting scrape" or "Chrome WebDriver initialized" log entries
- [ ] Confirm the `fetch_course_sections` tool call returns in under 500ms (check the slow request warning threshold — it fires above 2000ms)
- [ ] Confirm `data_quality` in the tool result shows `'full'` or at least no scraping cascade

### TASK-005: Run existing unit tests
**Estimated time**: 5 minutes  
**Refs**: All FRs

Run the test suite to confirm no regressions:

```bash
cd /home/kbesada/Code/ScheduleFirst-AI/services
python -m pytest mcp_server/tests/test_data_freshness_service.py -v
python -m pytest mcp_server/tests/test_supabase_service.py -v
python -m pytest mcp_server/tests/test_data_population_service.py -v
```

- [x] All tests pass (these use mocks and don't require the real DB)

---

## Dependencies Graph

```
TASK-001 (required)
    └── TASK-003 (verify fix)
            └── TASK-004 (verify caching)
                    └── TASK-005 (regression tests)

TASK-002 (independent housekeeping, can be done anytime)
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration alters columns that already exist in `courses`/`professors` | Low | Low | `ADD COLUMN IF NOT EXISTS` makes it safe |
| Supabase SQL Editor not accessible | Very low | High | Use psql or Supabase CLI as fallback |
| First scrape after fix still returns 0 courses (CUNY selector issue) | High | Medium | This is a separate issue (CUNY scraper timeout). The fix still resolves the repeated scraping — after the first attempt (successful or not), the status is recorded and subsequent requests won't re-scrape for 7 days |
| Tests fail after migration | Very low | Low | Tests use mocks, no real DB connection |

---

## Rollback Plan

If the migration causes unexpected issues:

```sql
-- Drop the new table (only if needed — has no FKs to other tables)
DROP TABLE IF EXISTS sync_metadata;

-- Reverse column additions (if desired)
ALTER TABLE courses DROP COLUMN IF EXISTS is_stale;
ALTER TABLE courses DROP COLUMN IF EXISTS last_scraped;
ALTER TABLE professors DROP COLUMN IF EXISTS data_source;
ALTER TABLE professors DROP COLUMN IF EXISTS last_updated;
```

> [!CAUTION]
> Rolling back after data has been written will lose any existing `sync_metadata` rows. Only roll back if there's a critical issue.
