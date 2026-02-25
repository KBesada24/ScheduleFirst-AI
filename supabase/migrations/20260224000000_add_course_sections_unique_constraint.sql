-- Ensure upsert target for course_sections exists: (course_id, section_number)

WITH ranked_sections AS (
  SELECT
    ctid,
    ROW_NUMBER() OVER (
      PARTITION BY course_id, section_number
      ORDER BY updated_at DESC NULLS LAST, scraped_at DESC NULLS LAST, ctid DESC
    ) AS row_num
  FROM course_sections
)
DELETE FROM course_sections cs
USING ranked_sections rs
WHERE cs.ctid = rs.ctid
  AND rs.row_num > 1;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'course_sections_course_id_section_number_key'
  ) THEN
    ALTER TABLE course_sections
      ADD CONSTRAINT course_sections_course_id_section_number_key
      UNIQUE (course_id, section_number);
  END IF;
END $$;
