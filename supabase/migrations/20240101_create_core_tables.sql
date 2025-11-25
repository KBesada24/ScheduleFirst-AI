CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  major TEXT,
  graduation_year INT,
  preferences JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_code TEXT NOT NULL,
  subject_code TEXT,
  course_number TEXT,
  name TEXT NOT NULL,
  description TEXT,
  credits INT,
  department TEXT,
  university TEXT,
  semester TEXT NOT NULL,
  last_scraped TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(course_code, university, semester)
);

CREATE TABLE IF NOT EXISTS professors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  ratemyprof_id TEXT,
  university TEXT,
  department TEXT,
  average_rating NUMERIC(3,2),
  average_difficulty NUMERIC(3,2),
  review_count INT,
  grade_letter CHAR(1),
  composite_score NUMERIC(3,0),
  last_updated TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_sections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
  section_number TEXT NOT NULL,
  professor_id UUID REFERENCES professors(id) ON DELETE SET NULL,
  professor_name TEXT,
  days TEXT,
  start_time TIME,
  end_time TIME,
  location TEXT,
  modality TEXT,
  enrolled INT,
  capacity INT,
  scraped_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS professor_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  professor_id UUID REFERENCES professors(id) ON DELETE CASCADE,
  review_text TEXT,
  rating NUMERIC(3,2),
  difficulty NUMERIC(3,2),
  sentiment_positive INT,
  sentiment_aspects JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  scraped_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  semester TEXT,
  name TEXT DEFAULT 'My Schedule',
  sections UUID[],
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_courses_code ON courses(course_code);
CREATE INDEX IF NOT EXISTS idx_courses_semester ON courses(semester);
CREATE INDEX IF NOT EXISTS idx_courses_university ON courses(university);
CREATE INDEX IF NOT EXISTS idx_sections_professor ON course_sections(professor_id);
CREATE INDEX IF NOT EXISTS idx_sections_professor_name ON course_sections(professor_name);
CREATE INDEX IF NOT EXISTS idx_sections_time ON course_sections(days, start_time);
CREATE INDEX IF NOT EXISTS idx_professors_name ON professors(name);
CREATE INDEX IF NOT EXISTS idx_reviews_professor ON professor_reviews(professor_id);
CREATE INDEX IF NOT EXISTS idx_schedules_user ON user_schedules(user_id);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'courses') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE courses;
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'course_sections') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE course_sections;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'professors') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE professors;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'user_schedules') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE user_schedules;
  END IF;
END $$;