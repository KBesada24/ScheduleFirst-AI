-- Migration: 001_hybrid_impl.sql
-- Description: Add staleness tracking and sync metadata tables

-- 1. Update courses table
ALTER TABLE courses 
ADD COLUMN IF NOT EXISTS last_scraped TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS is_stale BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_courses_semester_university ON courses(semester, university);

-- 2. Update professors table
ALTER TABLE professors 
ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'manual';

CREATE INDEX IF NOT EXISTS idx_professors_name_university ON professors(name, university);

-- 3. Create sync_metadata table
CREATE TABLE IF NOT EXISTS sync_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL, -- 'courses', 'professors', 'reviews'
    semester VARCHAR(50),
    university VARCHAR(100),
    last_sync TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sync_status VARCHAR(20) NOT NULL, -- 'success', 'failed', 'in_progress'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sync_metadata_lookup ON sync_metadata(entity_type, semester, university);
