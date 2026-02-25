# Requirements: Fix Missing `sync_metadata` Table

## Overview

The `sync_metadata` table is expected by the Python backend to track whether course and professor data has been recently scraped from external sources (CUNY Global Search, RateMyProfessors). The table is missing from the Supabase database, causing every AI chat request that involves course data to trigger a full CUNY web scrape (~22 seconds), regardless of whether the data was already scraped recently. This spec defines the requirements for adding the table so that the data freshness system works as designed.

---

## Functional Requirements

### FR-001: sync_metadata Table Creation
**Type**: Ubiquitous  
**Statement**: The Supabase database shall contain a `sync_metadata` table that tracks the synchronization status of each entity type per semester and university.  
**Acceptance Criteria**:
- [ ] Table `public.sync_metadata` exists in Supabase
- [ ] Table is queryable via the Supabase PostgREST API (i.e., `GET /rest/v1/sync_metadata` does not return a `PGRST205` error)
- [ ] Table schema matches the Pydantic model defined in `services/mcp_server/models/sync_metadata.py`

### FR-002: Course Freshness Check
**Type**: Event-driven  
**Statement**: WHEN a user asks the AI to search for classes, the system SHALL check if course data for the requested semester and university is already fresh (within 7 days) and skip re-scraping if it is.  
**Acceptance Criteria**:
- [ ] The `data_freshness_service.is_course_data_fresh()` method does not raise an exception when `sync_metadata` is queried
- [ ] On a first-time request, freshness check returns `False` (no record exists) → scrape is triggered
- [ ] On a subsequent request within 7 days, freshness check returns `True` → scrape is skipped
- [ ] The CUNY scraper is not invoked when fresh data exists in Supabase

### FR-003: Sync Status Tracking
**Type**: Event-driven  
**Statement**: WHEN a CUNY course sync begins or completes, the system SHALL record the status, timestamp, and any error in `sync_metadata`.  
**Acceptance Criteria**:
- [ ] `mark_sync_in_progress()` successfully inserts/updates a row with `sync_status = 'in_progress'`
- [ ] `mark_sync_complete()` successfully updates the row with `sync_status = 'success'` and a `last_sync` timestamp
- [ ] If the sync fails, `sync_status` is set to `'failed'` with an `error_message`
- [ ] None of the above methods throw uncaught exceptions when the table exists

### FR-004: Idempotent Migration
**Type**: Ubiquitous  
**Statement**: The SQL migration script shall be safe to run multiple times without causing errors or data loss.  
**Acceptance Criteria**:
- [ ] `CREATE TABLE IF NOT EXISTS` prevents duplicate table creation errors
- [ ] `ADD COLUMN IF NOT EXISTS` prevents errors if `courses` or `professors` already have the new columns
- [ ] Re-running the migration produces no errors and does not alter existing data

### FR-005: Index on Lookup Key
**Type**: Ubiquitous  
**Statement**: The system SHALL include an index on `(entity_type, semester, university)` in `sync_metadata` to support efficient lookup queries.  
**Acceptance Criteria**:
- [ ] Index `idx_sync_metadata_lookup` exists on the `sync_metadata` table
- [ ] The freshness check query does not perform a full table scan

---

## Non-Functional Requirements

### NFR-001: Performance
**Statement**: WHEN course data is fresh, the system SHALL respond to the AI's `fetch_course_sections` tool call without invoking the CUNY scraper, reducing tool call latency from ~22 seconds to under 500ms.  
**Acceptance Criteria**:
- [ ] Second identical request for same semester/university completes `fetch_course_sections` in under 500ms (no scrape)
- [ ] Freshness check adds no more than 50ms overhead to the request

### NFR-002: Reliability
**Statement**: IF the `sync_metadata` query fails for any reason, the system SHALL fall back gracefully and continue with a scrape rather than crashing.  
**Acceptance Criteria**:
- [ ] Existing `try/except` blocks in `data_freshness_service.py` catch errors and log warnings (already implemented — must remain intact)
- [ ] A `PGRST205` error is no longer thrown once migration is applied

---

## Constraints

- The fix must use the existing SQL migration at `services/migrations/001_hybrid_impl.sql` — no rewriting of Python code is required
- The Supabase project must be accessible (valid URL and service role key in `.env`)
- The migration must not delete or modify existing data in `courses` or `professors` tables

---

## Dependencies

- Supabase project with admin/service role access
- Existing tables: `courses`, `professors` (already created by `supabase/migrations/20240101_create_core_tables.sql`)
- Python service layer already implemented: `sync_metadata.py`, `supabase_service.py`, `data_freshness_service.py`, `data_population_service.py`

---

## Out of Scope

- Fixing the CUNY scraper timeout / CSS selector issues (separate problem)
- Fixing the `thought_signature` Gemini API error (separate problem)
- Adding a UI for viewing sync status
- Changing TTL values (7-day course TTL, 30-day review TTL are already configured)
- RLS (Row-Level Security) policies on `sync_metadata` (backend uses service role key, bypasses RLS)
