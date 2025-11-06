# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**ScheduleFirst AI** is a CUNY AI Schedule Optimizer - an AI-powered course planning assistant that helps CUNY students optimize their academic schedules by integrating real-time course data with AI-driven professor evaluation and schedule conflict detection.

**Tech Stack:**
- **Frontend**: React + TypeScript + Vite with React Router
- **UI Framework**: Radix UI components with Tailwind CSS
- **Backend**: Python FastMCP server (planned) with Google Gemini AI integration
- **Database**: Supabase (PostgreSQL with pgvector)
- **Authentication**: Supabase Auth

## Common Commands

### Development
```bash
# Start development server (port 3000)
pnpm dev

# Build for production
pnpm build

# Build without stopping on TypeScript errors
pnpm build-no-errors

# Preview production build
pnpm preview
```

### Code Quality
```bash
# Run ESLint
pnpm lint

# Generate Supabase types (requires SUPABASE_PROJECT_ID env var)
pnpm types:supabase
```

### Backend Services (Python)
```bash
# Navigate to services directory first
cd services

# Install Python dependencies
poetry install

# Start MCP server (port 8000)
poetry run python -m mcp_server.main

# Run background jobs scheduler
python -m background_jobs.scheduler

# Run tests
pytest

# Run tests with coverage
pytest --cov=mcp_server --cov-report=html
```

## Architecture Overview

### Frontend Architecture
The frontend follows a **component-based React architecture** with React Router for navigation:

1. **Authentication Flow**: Implemented via Supabase Auth with `AuthProvider` context
   - Public routes: `/`, `/login`, `/signup`
   - Protected routes: `/dashboard`, `/success`
   - Auth protection via `PrivateRoute` HOC

2. **Routing Pattern**: Uses React Router v6 with conditional Tempo routes
   - Main app routes defined in `App.tsx`
   - Development routes via `tempo-routes` (when `VITE_TEMPO=true`)

3. **Component Organization**:
   - `components/auth/` - Authentication forms
   - `components/dashboard/` - Dashboard widgets
   - `components/pages/` - Page-level components
   - `components/schedule/` - Schedule-specific components (CourseCard, CourseSearch, ProfessorCard, ScheduleGrid)
   - `components/ui/` - Reusable Radix UI components (40+ components)

4. **Data Layer**: Centralized Supabase queries and React hooks
   - `lib/supabase-queries.ts` - Direct database query functions
   - `lib/supabase-hooks.ts` - React hooks wrapping queries
   - `supabase/supabase.ts` - Supabase client initialization
   - `supabase/auth.tsx` - Authentication context provider

### Backend Architecture (Python Services)
The backend is designed as a **Model Context Protocol (MCP) server** using FastMCP:

1. **MCP Server Structure** (`services/mcp_server/`):
   - `main.py` - Entry point and server initialization
   - `config.py` - Environment configuration management
   - `models/` - Pydantic data models for courses, professors, schedules
   - `services/` - Business logic (database ops, scrapers, sentiment analysis, Gemini client)
   - `tools/` - FastMCP tool definitions (exposed to Gemini AI)
   - `utils/` - Logging, caching, validation utilities

2. **MCP Tools** (AI-callable functions):
   - `fetch_course_sections()` - Get available course sections from database
   - `generate_optimized_schedule()` - Generate ranked schedule recommendations
   - `get_professor_grade()` - AI-generated professor grades (A-F)
   - `compare_professors()` - Side-by-side professor comparison
   - `check_schedule_conflicts()` - Detect scheduling conflicts

3. **Background Jobs** (`services/background_jobs/`):
   - Scheduled via APScheduler
   - Weekly course sync from CUNY Global Search (Sundays 2 AM)
   - Weekly RateMyProfessors scraping (Mondays 3 AM)
   - Weekly professor grade updates (Mondays 5 AM)

4. **Data Flow**:
   ```
   CUNY Global Search → Scraper → Supabase PostgreSQL
   RateMyProfessors → Scraper → Review Storage → Sentiment Analysis → Professor Grades
   User Request → Frontend → MCP Server → Gemini AI (with tools) → Optimized Schedule
   ```

### Database Schema (Supabase PostgreSQL)
**Core Tables**:
- `users` - Student profiles with major, graduation year, preferences
- `courses` - Course catalog with course_code, name, credits, department, university, semester
- `course_sections` - Section details: professor, days, times, location, modality, enrollment
- `professors` - Professor profiles with average_rating, grade_letter, composite_score
- `professor_reviews` - Scraped reviews with sentiment analysis data
- `user_schedules` - Saved schedules (array of section UUIDs)

**Key Features**:
- Real-time subscriptions enabled
- Indexed for performance (course_code, professor_name, time slots)
- Foreign key relationships enforced
- pgvector extension for semantic search (planned)

## Key Patterns & Conventions

### Frontend Patterns

1. **Query Pattern**: Use React hooks from `supabase-hooks.ts` for data fetching
   ```typescript
   // Preferred: Use hooks
   const { courses, loading, error } = useCourseSearch({ semester: "Fall 2025" });
   
   // When needed: Direct queries
   const courses = await searchCourses({ query: "algorithms" });
   ```

2. **Authentication Pattern**: Always use `useAuth()` hook
   ```typescript
   const { user, loading, signIn, signOut } = useAuth();
   ```

3. **Component Imports**: Use `@/` alias for absolute imports
   ```typescript
   import { Button } from "@/components/ui/button";
   import { useCourseSearch } from "@/lib/supabase-hooks";
   ```

4. **Loading States**: Use `LoadingSpinner` or `LoadingScreen` components
   ```typescript
   if (loading) return <LoadingSpinner />;
   ```

### Backend Patterns

1. **MCP Tool Definition**: Use `@mcp.tool` decorator
   ```python
   @mcp.tool
   async def fetch_course_sections(course_codes: list[str], semester: str) -> dict:
       # Implementation
   ```

2. **Error Handling**: Always wrap in try-except with logging
   ```python
   try:
       # Logic
   except Exception as e:
       logger.error(f"Error: {e}")
       return {'error': str(e), 'data': []}
   ```

3. **Database Access**: Use Supabase service for database operations
   ```python
   from services.supabase_service import SupabaseService
   db = SupabaseService()
   ```

## Important Configuration

### Environment Variables

**Frontend** (`.env` in root):
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_TEMPO=false  # Set to "true" for Tempo devtools
```

**Backend** (`services/.env`):
```env
GEMINI_API_KEY=your-gemini-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://user:pass@host:5432/db
LOG_LEVEL=INFO
SCRAPER_REQUEST_DELAY=2.0
```

### Path Aliases
- `@/*` resolves to `./src/*` (configured in `vite.config.ts` and `tsconfig.json`)

## Data Source Information

**Primary Course Data**: CUNY Global Search (https://globalsearch.cuny.edu/)
- Scraped weekly via web scraping (Selenium + BeautifulSoup)
- Covers all 25 CUNY schools
- See `CUNY-Global-Integration.md` for detailed scraping implementation

**Professor Ratings**: RateMyProfessors
- Scraped with respectful rate limiting (1 request/second)
- Sentiment analysis using Transformers (Hugging Face)
- AI-generated grades (A-F) based on review analysis

## Testing & Seeding

### Database Seeding
The app includes seeding utilities for development:

```typescript
import { seedDatabase, clearDatabase } from "@/lib/seed-database";

// Seed with sample data
await seedDatabase();

// Clear all data (caution!)
await clearDatabase();
```

Or use the Admin UI at `/admin` to seed/clear via buttons.

### Testing Backend
```bash
cd services

# Run specific test
pytest mcp_server/tests/test_schedule_optimizer.py

# Test database sync
pytest mcp_server/tests/test_cuny_scraper.py
```

## Critical Implementation Notes

1. **Monorepo Structure**: Root contains frontend, `services/` contains Python backend
   - Frontend and backend are separate but share types via documentation
   - No shared npm/pnpm workspace for Python code

2. **Supabase Integration**: Fully connected with comprehensive query functions
   - All query functions in `lib/supabase-queries.ts`
   - React hooks in `lib/supabase-hooks.ts`
   - RLS (Row Level Security) disabled by default - enable as needed for production

3. **Gemini AI Integration**: Backend uses Google Gemini 2.0-flash
   - Cost-effective alternative to OpenAI ($0.075/1M input tokens vs $5/1M)
   - Function calling for MCP tool invocation
   - System prompts in `services/mcp_server/services/gemini_client.py`

4. **Conflict Detection**: Automatic schedule conflict checking
   - Checks time overlaps between sections
   - Validates campus travel time feasibility
   - Runs automatically when adding sections to schedules

5. **Windows Development**: This codebase is Windows-compatible
   - Uses PowerShell for shell commands
   - Path separators handled correctly
   - Python virtual environment in `.venv/`

## Production Considerations

- **Frontend Deployment**: Vercel (automatic from `main` branch)
- **Backend Deployment**: Railway or Fly.io for Python services
- **Database**: Supabase managed PostgreSQL with automatic backups
- **Monitoring**: Implement error tracking (Sentry recommended)
- **Rate Limiting**: Respect robots.txt for CUNY Global Search and RateMyProfessors
- **GDPR Compliance**: Implement data privacy policy, user data deletion capability

## Related Documentation

- `CUNY-PRD.md` - Complete Product Requirements Document
- `CUNY-Global-Integration.md` - CUNY Global Search scraping implementation guide
- `SUPABASE_GUIDE.md` - Complete Supabase integration guide with examples
- `services/README.md` - Backend services documentation
- `README.md` - Basic Vite + React template information
