# CUNY AI Schedule Optimizer - Product Requirements Document (PRD)

## 1. Product Overview & Vision

### 1.1 Executive Summary
CUNY AI Schedule Optimizer is an AI-powered course planning assistant designed to help CUNY students optimize their academic schedules. The platform integrates real-time course data from CUNYfirst Schedule Builder with AI-driven professor evaluation and schedule conflict detection to provide personalized course recommendations.

### 1.2 Purpose & Problem Statement
CUNY students face significant challenges when planning their schedules:
- CUNYfirst Schedule Builder lacks intelligent scheduling recommendations
- No centralized platform to compare professor ratings across multiple CUNY schools
- Manual conflict detection is time-consuming and error-prone
- Students lack data-driven guidance on whether specific professor-course combinations are worthwhile
- Difficulty optimizing schedules based on personal preferences (time slots, campus locations, professor quality)

### 1.3 Vision Statement
Empower CUNY students to build optimal academic schedules by combining intelligent AI-driven recommendations, real-time professor quality insights, and constraint-based scheduling algorithms.

### 1.4 Target Users
- CUNY undergraduate and graduate students (initial focus)
- Students across all 25 CUNY schools
- Students from all academic disciplines
- Primary demographic: Ages 18-30, tech-savvy, enrolled in 12-18 credits per semester

### 1.5 Success Metrics & KPIs
- User acquisition: 500+ active CUNY student users within 3 months
- Engagement: 60%+ weekly active usage rate
- NPS (Net Promoter Score): Target 50+
- Schedule optimization: 70%+ of users report improved schedule satisfaction
- Professor rating accuracy: 85%+ alignment with RateMyProfessors aggregate data
- System uptime: 99.5%
- Average response time: <2 seconds for schedule optimization queries
- User retention: 40%+ after 4 weeks

---

## 2. Product Scope & Features

### 2.1 Core Features (MVP - Phase 1)

#### 2.1.1 Schedule Optimization Engine
- **Intelligent Schedule Suggestions**: AI analyzes user preferences and generates optimal class schedules
  - Input: Required courses, preferred time slots, campus preferences, max/min class hours per day
  - Output: 3-5 optimized schedule recommendations ranked by preference score
  - Algorithm: Constraint satisfaction solver with Gemini AI refinement
  - Response time: < 3 seconds

#### 2.1.2 Professor Evaluation System
- **AI-Powered Professor Grades**: Analyze aggregated RateMyProfessors reviews to assign A-F grades
  - Input: Professor name, subject, university
  - Output: Letter grade (A-F), composite score (0-100), aspect breakdowns
  - Aspects analyzed: Teaching clarity, grading fairness, engagement, accessibility
  - Data freshness: Updated weekly

#### 2.1.3 Schedule Conflict Detection
- **Automatic Conflict Prevention**: Identify and prevent course time conflicts
  - Detect overlapping class times
  - Identify unrealistic travel times between campuses
  - Flag scheduling constraints (prerequisites, corequisites)
  - Suggest alternative sections in real-time

#### 2.1.4 Course Search & Discovery
- **Advanced Course Search**:
  - Filter by: Department, course code, credits, time slot, professor, campus location, course modality
  - Sort by: Professor rating, class size, times offered
  - Display: Course description, prerequisites, enrollment cap, current enrollment

#### 2.1.5 Professor Comparison Tool
- **Side-by-side Professor Comparison**: Compare 2-4 professors teaching the same course
  - Show ratings, difficulty scores, review highlights, key feedback themes
  - Recommend best professor-course combinations
  - Historical enrollment trends

### 2.2 Phase 2 Features (Post-MVP)

#### 2.2.1 Personalization Engine
- **Learning Style Matching**: Adapt professor recommendations based on student learning style
  - Learning style assessment quiz
  - Match with professor teaching methods from reviews
  - Personalized confidence scores

#### 2.2.2 Real-Time Monitoring
- **Schedule Availability Alerts**: Notify when preferred courses become available
  - Push notifications when sections open/close
  - Alert when new professor sections added
  - Early registration suggestions

#### 2.2.3 Degree Audit Integration
- **DegreeWorks Integration** (if API available): Pull required courses automatically
  - Map required courses to available sections
  - Suggest course sequences
  - Compliance checking

#### 2.2.4 Schedule Sharing & Collaboration
- **Share & Get Feedback**: Share proposed schedules with peers/advisors
  - Generate shareable schedule links
  - Collect feedback from advisors
  - Compare schedules with classmates

---

## 3. Functional Requirements

### 3.1 User Authentication & Profiles
- **FR-1.1**: System shall authenticate users via CUNY SSO (LDAP/CUNYfirst integration)
- **FR-1.2**: Users can create local email-based backup accounts
- **FR-1.3**: User profiles shall store: major, graduation year, preferences, saved schedules
- **FR-1.4**: Data persistence: All user data encrypted at rest in Supabase PostgreSQL

### 3.2 Course Data Management
- **FR-2.1**: System shall sync course data from CUNYfirst API weekly
- **FR-2.2**: For each course section, store: course ID, name, credits, professor, time slots, room, campus, enrollment cap, modality
- **FR-2.3**: System shall handle courses across all CUNY schools (25 institutions)
- **FR-2.4**: Data validation: Flag courses with missing data, prevent stale data serving

### 3.3 Professor Rating Pipeline
- **FR-3.1**: System shall scrape RateMyProfessors data weekly for all CUNY professors
- **FR-3.2**: System shall cache RateMyProfessors ratings with timestamps
- **FR-3.3**: Sentiment analysis: Extract and classify 5 sentiment aspects from each review
  - Teaching clarity, grading fairness, engagement, accessibility, class difficulty
- **FR-3.4**: Scoring formula: Weighted average of aspects with recency decay
- **FR-3.5**: System shall generate professor "grades" A-F with < 5 minute latency

### 3.4 AI Schedule Optimization
- **FR-4.1**: System shall accept user preferences as input (required courses, time constraints, campus preference)
- **FR-4.2**: System shall generate 3-5 optimized schedules within 3 seconds
- **FR-4.3**: Each schedule shall be ranked with a preference score (0-100)
- **FR-4.4**: System shall validate all generated schedules for conflicts
- **FR-4.5**: Optimization criteria: Minimize travel time, maximize professor ratings, respect user time preferences, balance course load

### 3.5 Conflict Detection
- **FR-5.1**: System shall detect overlapping class times (same section cannot have overlaps)
- **FR-5.2**: System shall identify unrealistic travel times between campuses (< 10 min walking assumed)
- **FR-5.3**: System shall check prerequisites/corequisites
- **FR-5.4**: Real-time validation: Conflicts detected and reported before schedule submission

### 3.6 User Interface
- **FR-6.1**: Dashboard shall display: current schedule, optimization suggestions, upcoming classes
- **FR-6.2**: Schedule Builder: Drag-and-drop course selection, visual timetable
- **FR-6.3**: Professor cards: Show rating, grade, top reviews, difficulty level
- **FR-6.4**: Responsive design: Works on desktop (primary), tablet, mobile devices
- **FR-6.5**: Accessibility: WCAG 2.1 AA compliance

---

## 4. Non-Functional Requirements

### 4.1 Performance
- **NFR-1.1**: Schedule optimization response time: < 3 seconds (p95)
- **NFR-1.2**: Course search results: < 500ms
- **NFR-1.3**: Professor rating lookup: < 1 second (from cache)
- **NFR-1.4**: Page load time: < 2 seconds (Largest Contentful Paint)
- **NFR-1.5**: API response time: < 100ms for all endpoints

### 4.2 Reliability & Availability
- **NFR-2.1**: System uptime: 99.5% (monthly)
- **NFR-2.2**: Graceful degradation: Service available even if RateMyProfessors scraper fails
- **NFR-2.3**: Database backup: Daily automated backups, 30-day retention
- **NFR-2.4**: Error handling: Comprehensive error messages, automatic error logging

### 4.3 Scalability
- **NFR-3.1**: System shall support 10,000+ concurrent users
- **NFR-3.2**: Database connection pooling: Max 100 concurrent connections
- **NFR-3.3**: Caching strategy: Redis-like caching for professor ratings, course search results
- **NFR-3.4**: Horizontal scaling: Load balanced across multiple instances

### 4.4 Security
- **NFR-4.1**: All data encryption: TLS 1.3 in transit, AES-256 at rest
- **NFR-4.2**: Authentication: OAuth 2.0 via Supabase
- **NFR-4.3**: Authorization: Row-Level Security (RLS) in Supabase PostgreSQL
- **NFR-4.4**: Rate limiting: 100 requests/minute per user, 10,000 requests/hour per IP
- **NFR-4.5**: GDPR compliance: Data privacy policy, user data deletion capability
- **NFR-4.6**: Input validation: Prevent SQL injection, XSS attacks
- **NFR-4.7**: Secrets management: Environment variables, no hardcoded credentials

### 4.5 Maintainability
- **NFR-5.1**: Code documentation: README, inline comments, API documentation (OpenAPI)
- **NFR-5.2**: Logging: Structured JSON logging, centralized log aggregation
- **NFR-5.3**: Monitoring: Real-time dashboards for API performance, database health, error rates
- **NFR-5.4**: CI/CD: Automated testing, linting, deployment pipeline

### 4.6 Compliance & Legal
- **NFR-6.1**: Terms of Service: Clear usage restrictions, data privacy policy
- **NFR-6.2**: RateMyProfessors: Respect robots.txt, rate limiting on scraper (1 request/second)
- **NFR-6.3**: CUNY Data: No storage of sensitive CUNY data beyond course catalog
- **NFR-6.4**: Accessibility: WCAG 2.1 AA standards

---

## 5. Technical Architecture

### 5.1 Technology Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Frontend** | Next.js 15 | 15.x | React Server Components, App Router, built-in optimizations, Vercel deployment |
| **Frontend Auth** | Supabase Auth | Latest | OAuth 2.0, CUNY SSO integration, built-in MFA support |
| **Backend API/Middleware** | Next.js API Routes / Server Actions | 15.x | Minimal overhead, integrates with frontend, easy deployment |
| **AI/LLM Integration** | Google Gemini API | 2.0-flash | Lower cost than OpenAI, excellent function calling, multimodal support |
| **MCP Framework** | FastMCP (Python) | Latest | Easy tool definition, async support, Gemini-compatible |
| **Database** | Supabase PostgreSQL | 14+ | pgvector for embeddings, real-time subscriptions, built-in auth |
| **Vector Store** | pgvector (PostgreSQL) | Latest | Semantic search for courses, stored in same DB |
| **Caching** | Supabase (edge caching) | N/A | Cache layer in Vercel Edge Network |
| **Sentiment Analysis** | Transformers (Hugging Face) | Latest | Fine-tuned models for reviews, deployed in Python backend |
| **Data Scraping** | BeautifulSoup4 + Selenium | Latest | RateMyProfessors data collection |
| **Task Scheduling** | APScheduler (Python) | 3.10+ | Weekly data sync, scheduled updates |
| **Deployment** | Vercel (Frontend) + Railway/Fly.io (Backend) | Latest | Seamless Next.js deployment, Python backend support |
| **Package Manager** | pnpm | 8+ | Faster installs, monorepo-friendly workspace support |
| **Environment Management** | dotenv | Latest | Secure secret management |

### 5.2 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (Next.js 15)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Dashboard   │  │ Schedule     │  │  Professor   │       │
│  │  Component   │  │  Builder     │  │  Cards       │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────┬────────────────────────────────────────────────┘
             │ (API Calls via fetch/axios)
┌────────────┴──────────────────────────────────────────────────┐
│          EDGE LAYER (Vercel Edge Network / Middleware)        │
│           Rate limiting, Request logging, Auth verification   │
└────────────┬──────────────────────────────────────────────────┘
             │ (Routed via API Routes / Server Actions)
┌────────────┴──────────────────────────────────────────────────┐
│              NEXT.JS API LAYER (Next.js 15)                   │
│  ┌────────────────────┐  ┌─────────────────────────────────┐ │
│  │  API Routes for    │  │  Server Actions for mutations   │ │
│  │  Data fetching     │  │  Form submissions, DB updates   │ │
│  └────────────────────┘  └─────────────────────────────────┘ │
└────────────┬──────────────────────────────────────────────────┘
             │ (HTTP calls)
┌────────────┴──────────────────────────────────────────────────┐
│           MCP SERVER LAYER (FastMCP - Python)                 │
│  ┌──────────────────┐  ┌──────────────────────────────────┐  │
│  │ Professor        │  │ Schedule Optimizer Tools         │  │
│  │ Evaluation Tools │  │ ├─ Schedule Conflict Check       │  │
│  │ ├─ Fetch Reviews │  │ ├─ Generate Optimized Schedules │  │
│  │ ├─ Sentiment     │  │ ├─ Rank Schedules by Pref Score │  │
│  │ │ Analysis       │  │ └─ Suggest Alternatives         │  │
│  │ └─ Grade Gen     │  └──────────────────────────────────┘  │
│  └──────────────────┘         Routed via Google Gemini        │
└────────────┬──────────────────────────────────────────────────┘
             │ (HTTP to external services)
┌────────────┴──────────────────────────────────────────────────┐
│              DATABASE LAYER (Supabase PostgreSQL)             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Courses     │  │ Professors   │  │ User         │        │
│  │  Table       │  │ Reviews      │  │ Schedules    │        │
│  │  (indexed)   │  │ (embeddings) │  │ (RLS)        │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│  ┌──────────────────────────────────────────────────────┐     │
│  │         pgvector for semantic search                 │     │
│  └──────────────────────────────────────────────────────┘     │
└────────────┬──────────────────────────────────────────────────┘
             │ (Background jobs)
┌────────────┴──────────────────────────────────────────────────┐
│        EXTERNAL INTEGRATIONS (Data Sources)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ CUNYfirst    │  │ RateMyProf   │  │ Google       │        │
│  │ Schedule     │  │ Reviews      │  │ Gemini API   │        │
│  │ Builder API  │  │ (Scraper)    │  │ (AI/LLM)     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Data Flow: Schedule Optimization

```
User Input
    ↓
    │ (Required courses, preferences)
    ↓
Next.js Server Action
    ↓
    │ Fetch course sections from Supabase
    ├─ Validate against conflicts
    └─ Get cached professor ratings
    ↓
Call Gemini API with function tools
    ↓
    │ Gemini decides to call MCP tools
    ├─ fetch_course_sections()
    ├─ check_scheduling_constraints()
    ├─ get_professor_grades()
    └─ generate_optimized_schedule()
    ↓
MCP Server (FastMCP - Python)
    ├─ Constraint satisfaction solver
    ├─ Sentiment analysis on reviews
    └─ Schedule optimization algorithm
    ↓
Return structured JSON results
    ↓
Gemini AI ranks & formats results
    ↓
Next.js returns to client
    ↓
React renders schedule recommendations
```

---

## 6. Repository Structure & Monorepo Organization

### 6.1 Monorepo vs Polyrepo Decision: MONOREPO ✅

**Rationale for Monorepo**:
- Shared types between frontend and backend (course structures, professor ratings)
- Atomic commits across frontend/backend changes
- Easier dependency management (both use Python and JavaScript)
- Simpler deployment process
- Easier to maintain consistency and version alignment
- Smaller team (solo developer initially) benefits from centralized codebase
- CI/CD pipeline runs all tests in one workflow

**Tools**: pnpm workspaces (frontend) + Python poetry (backend)

---

### 6.2 Directory Structure

```
cuny-schedule-optimizer/                    # Root monorepo
│
├── 📄 README.md                           # Project overview
├── 📄 CONTRIBUTING.md                     # Development guidelines
├── 📄 pnpm-workspace.yaml                 # pnpm workspace config
├── 📄 package.json                        # Root package.json (shared scripts)
├── 📄 pyproject.toml                      # Python project config
├── 📄 .env.example                        # Example environment variables
├── 📄 turbo.json                          # Turborepo build config (optional)
│
├── 📁 apps/                               # Next.js applications
│   ├── web/                               # Main student-facing app
│   │   ├── 📄 package.json
│   │   ├── 📄 tsconfig.json
│   │   ├── 📄 next.config.ts
│   │   ├── 📄 tailwind.config.ts
│   │   ├── 📁 app/                        # App Router (Next.js 15)
│   │   │   ├── layout.tsx                 # Root layout with auth check
│   │   │   ├── page.tsx                   # Home page
│   │   │   ├── (auth)/                    # Auth route group
│   │   │   │   ├── login/page.tsx
│   │   │   │   ├── signup/page.tsx
│   │   │   │   └── callback/page.tsx      # OAuth callback
│   │   │   ├── (dashboard)/               # Protected routes
│   │   │   │   ├── dashboard/page.tsx     # Main dashboard
│   │   │   │   ├── schedule-builder/page.tsx
│   │   │   │   ├── professor-comparison/page.tsx
│   │   │   │   └── my-schedules/page.tsx
│   │   │   ├── api/                       # API routes
│   │   │   │   ├── optimize-schedule/route.ts
│   │   │   │   ├── get-courses/route.ts
│   │   │   │   ├── get-professor-grade/route.ts
│   │   │   │   ├── save-schedule/route.ts
│   │   │   │   └── health/route.ts
│   │   │   └── error.tsx                  # Error boundary
│   │   ├── 📁 components/
│   │   │   ├── Schedule/
│   │   │   │   ├── ScheduleGrid.tsx       # Visual schedule
│   │   │   │   ├── ScheduleConflictAlert.tsx
│   │   │   │   └── CourseCard.tsx
│   │   │   ├── Professor/
│   │   │   │   ├── ProfessorCard.tsx
│   │   │   │   ├── ProfessorComparison.tsx
│   │   │   │   └── GradeDisplay.tsx
│   │   │   ├── Search/
│   │   │   │   ├── CourseSearch.tsx
│   │   │   │   ├── FilterPanel.tsx
│   │   │   │   └── SearchResults.tsx
│   │   │   ├── Common/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Navigation.tsx
│   │   │   │   ├── LoadingSpinner.tsx
│   │   │   │   └── ErrorBoundary.tsx
│   │   │   └── Layout/
│   │   │       ├── Sidebar.tsx
│   │   │       └── MainLayout.tsx
│   │   ├── 📁 hooks/
│   │   │   ├── useAuth.ts                 # Auth context hook
│   │   │   ├── useScheduleOptimization.ts # Schedule API hook
│   │   │   ├── useCourseSearch.ts         # Course search hook
│   │   │   └── useProfessorData.ts        # Professor ratings hook
│   │   ├── 📁 lib/
│   │   │   ├── api.ts                     # API client functions
│   │   │   ├── supabase.ts                # Supabase client config
│   │   │   ├── auth.ts                    # Auth utilities
│   │   │   ├── types.ts                   # Shared TypeScript types
│   │   │   └── utils/
│   │   │       ├── formatTime.ts
│   │   │       ├── detectConflicts.ts
│   │   │       └── calculateScore.ts
│   │   ├── 📁 styles/
│   │   │   ├── globals.css
│   │   │   └── variables.css
│   │   └── 📁 public/
│   │       └── images/
│   │
│   └── admin/                             # (Future) Admin dashboard
│       └── ... (Similar structure to web)
│
├── 📁 packages/                           # Shared packages
│   ├── shared-types/                      # TypeScript type definitions
│   │   ├── 📄 package.json
│   │   ├── 📄 tsconfig.json
│   │   ├── index.ts
│   │   ├── course.types.ts                # Course/Section types
│   │   ├── professor.types.ts             # Professor rating types
│   │   ├── schedule.types.ts              # Schedule types
│   │   └── user.types.ts                  # User types
│   │
│   ├── ui-components/                    # Reusable UI components
│   │   ├── 📄 package.json
│   │   ├── 📄 tsconfig.json
│   │   ├── index.ts
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   └── Button.test.tsx
│   │   ├── Card/
│   │   └── Modal/
│   │
│   └── database/                         # Shared DB schemas & migrations
│       ├── 📄 package.json
│       ├── migrations/
│       │   ├── 001_init_schema.sql
│       │   ├── 002_add_professors.sql
│       │   ├── 003_add_user_schedules.sql
│       │   ├── 004_add_reviews.sql
│       │   └── 005_add_embeddings.sql
│       └── seeds/
│           └── seed_cuny_schools.sql
│
├── 📁 services/                          # Python backend services
│   ├── 📄 pyproject.toml
│   ├── 📄 poetry.lock
│   ├── 📄 README.md
│   ├── 📁 mcp_server/                    # FastMCP server
│   │   ├── 📄 __init__.py
│   │   ├── main.py                       # MCP server entry point
│   │   ├── config.py                     # Environment config
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── professor_evaluator.py    # Professor rating tools
│   │   │   │   ├─ fetch_professor_reviews()
│   │   │   │   ├─ analyze_review_sentiment()
│   │   │   │   └─ generate_professor_grade()
│   │   │   ├── schedule_optimizer.py      # Schedule optimization tools
│   │   │   │   ├─ fetch_course_sections()
│   │   │   │   ├─ check_scheduling_constraints()
│   │   │   │   ├─ detect_conflicts()
│   │   │   │   └─ generate_optimized_schedule()
│   │   │   └── helper.py                  # Shared utilities
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── course.py
│   │   │   ├── professor.py
│   │   │   └── schedule.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── supabase_service.py        # Database operations
│   │   │   ├── ratemyprof_scraper.py      # RateMyProf scraping
│   │   │   ├── sentiment_analyzer.py      # NLP sentiment analysis
│   │   │   ├── constraint_solver.py       # Schedule optimization
│   │   │   └── gemini_client.py           # Gemini API calls
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── logger.py                  # Structured logging
│   │   │   ├── cache.py                   # Caching utilities
│   │   │   └── validators.py              # Input validation
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_professor_evaluator.py
│   │       ├── test_schedule_optimizer.py
│   │       └── fixtures/
│   │
│   ├── 📁 background_jobs/               # Scheduled tasks
│   │   ├── 📄 __init__.py
│   │   ├── scheduler.py                  # APScheduler setup
│   │   ├── jobs/
│   │   │   ├── __init__.py
│   │   │   ├── sync_courses.py            # Weekly course sync
│   │   │   ├── scrape_reviews.py          # Weekly review scraping
│   │   │   ├── analyze_reviews.py         # Weekly sentiment analysis
│   │   │   └── update_professor_grades.py # Weekly grade update
│   │   └── logs/
│   │
│   └── requirements/
│       ├── base.txt                      # Base dependencies
│       ├── dev.txt                       # Development dependencies
│       └── prod.txt                      # Production dependencies
│
├── 📁 docs/                              # Documentation
│   ├── API.md                            # API documentation
│   ├── ARCHITECTURE.md                   # System architecture
│   ├── DATABASE.md                       # Database schema
│   ├── DEPLOYMENT.md                     # Deployment guide
│   ├── DEVELOPMENT.md                    # Development setup
│   └── MCP_TOOLS.md                      # MCP tools reference
│
├── 📁 .github/                           # GitHub configuration
│   ├── workflows/
│   │   ├── ci.yml                        # CI pipeline
│   │   ├── test.yml                      # Test pipeline
│   │   ├── deploy-frontend.yml           # Vercel deployment
│   │   └── deploy-backend.yml            # Python backend deployment
│   └── ISSUE_TEMPLATE/
│
├── 📁 scripts/                           # Utility scripts
│   ├── setup-dev.sh                      # Development setup
│   ├── seed-db.sh                        # Database seeding
│   ├── run-tests.sh                      # Run all tests
│   └── deploy.sh                         # Deployment script
│
├── 📄 .env.example                       # Environment template
├── 📄 .gitignore
├── 📄 .dockerignore
├── 📄 docker-compose.yml                 # Local dev environment
└── 📄 Makefile                           # Common commands

```

---

## 7. Google Gemini API Integration

### 7.1 Why Google Gemini over OpenAI

| Criteria | Gemini 2.0 | GPT-4o |
|----------|-----------|--------|
| **Cost** | $0.075/1M input tokens, $0.30/1M output tokens | $5/1M input, $15/1M output | ✅ |
| **Function Calling** | Excellent, async support | Excellent | ⚖️ |
| **Multimodality** | Images, audio, video | Images, audio | ✅ |
| **Response Time** | ~500-800ms | ~600-900ms | ✅ |
| **Context Window** | 1M tokens | 128K tokens | ✅ |
| **MCP Support** | Native in Gemini CLI | Via LangChain | ✅ |
| **Reliability** | High | High | ⚖️ |

### 7.2 Gemini Integration Architecture

```python
# services/mcp_server/services/gemini_client.py
import os
from google import genai
from fastmcp import Client as MCPClient
from fastmcp.client.transports import FastMCPTransport

class GeminiScheduleOptimizer:
    def __init__(self, mcp_server):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "gemini-2.0-flash"
        self.transport = FastMCPTransport(mcp_server)
        self.mcp_client = MCPClient({"transport": self.transport})
    
    async def optimize_schedule(self, user_input: dict) -> dict:
        """
        Use Gemini with MCP tools to optimize schedule
        """
        # Build prompt with user constraints
        system_prompt = """You are a CUNY academic advisor specializing in schedule optimization.
        
        Available tools:
        - fetch_course_sections(): Get available course sections
        - check_scheduling_constraints(): Validate course compatibility
        - detect_conflicts(): Find schedule conflicts
        - get_professor_grades(): Get professor quality ratings
        - generate_optimized_schedule(): Create optimal schedules
        
        For each request:
        1. Understand user's required courses and preferences
        2. Fetch available sections
        3. Check all constraints
        4. Generate 3-5 optimized schedules
        5. Rank by student preference
        6. Explain your reasoning
        """
        
        user_message = f"""Please optimize my CUNY schedule:
        - Required courses: {user_input['courses']}
        - Preferred times: {user_input['time_preferences']}
        - Campus: {user_input['campus']}
        - Avoid gaps > 2 hours: {user_input['avoid_gaps']}
        
        Generate the best 3 schedules with detailed explanations.
        """
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[
                {"role": "user", "parts": [{"text": user_message}]}
            ],
            system_instruction=system_prompt,
            tools=[self._get_tools()]  # MCP tools converted to Gemini format
        )
        
        return self._parse_response(response)
    
    def _get_tools(self):
        """Convert MCP tools to Gemini function calling format"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "fetch_course_sections",
                    "description": "Get available course sections with times and professors",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "course_codes": {"type": "array", "items": {"type": "string"}},
                            "semester": {"type": "string"}
                        },
                        "required": ["course_codes"]
                    }
                }
            },
            # ... other tools
        ]
```

### 7.3 Gemini API Key Setup
- Create key at: https://aistudio.google.com/apikey
- Set `GEMINI_API_KEY` in environment variables
- Rate limit: 15 requests per minute (free tier), upgrade as needed

---

## 8. Development & Deployment Plan

### 8.1 Development Environment Setup

**Prerequisites**:
- Node.js 20+
- Python 3.11+
- PostgreSQL (or use Supabase)
- pnpm (package manager)
- Git

**Setup Steps**:
```bash
# Clone and install dependencies
git clone <repo>
cd cuny-schedule-optimizer
pnpm install

# Install Python dependencies
cd services
poetry install
cd ..

# Copy environment template
cp .env.example .env.local
# Fill in:
# - GEMINI_API_KEY
# - SUPABASE_URL
# - SUPABASE_SERVICE_ROLE_KEY
# - DATABASE_URL

# Run development servers
pnpm dev        # Starts Next.js on 3000
pnpm dev:backend # Starts FastMCP server on 8000
```

### 8.2 Deployment Architecture

**Frontend (Vercel)**:
- Automatic deployment from `main` branch
- Environment variables synced from Supabase project
- CDN for static assets
- Serverless functions for API routes

**Backend (Railway or Fly.io)**:
- Python FastAPI/FastMCP service
- Background jobs (APScheduler)
- PostgreSQL connection pooling
- Automated restarts on failure

**Database (Supabase)**:
- Managed PostgreSQL
- Automatic backups
- Real-time subscriptions
- pgvector for semantic search

### 8.3 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 20
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pnpm install && cd services && poetry install
      - name: Run tests
        run: pnpm test && pnpm test:backend
      - name: Linting
        run: pnpm lint
      - name: Type checking
        run: pnpm type-check

  deploy-frontend:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: vercel/action@main
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}

  deploy-backend:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Railway/Fly
        # Configure based on chosen platform
```

---

## 9. Database Schema Overview

### 9.1 Core Tables

```sql
-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  major TEXT,
  graduation_year INT,
  preferences JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Courses table
CREATE TABLE courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_code TEXT NOT NULL,  -- e.g., "CSC381"
  subject_code TEXT,          -- e.g., "CSC"
  course_number TEXT,         -- e.g., "381"
  name TEXT NOT NULL,
  description TEXT,
  credits INT,
  department TEXT,
  university TEXT,            -- CUNY school
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(course_code, university)
);

-- Course sections table
CREATE TABLE course_sections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
  section_number TEXT,
  professor_id UUID,
  days TEXT,                  -- "MWF", "TTh", etc.
  start_time TIME,
  end_time TIME,
  room TEXT,
  campus TEXT,
  modality TEXT,             -- In-person, online, hybrid
  capacity INT,
  enrolled INT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Professors table
CREATE TABLE professors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  ratemyprof_id TEXT,
  university TEXT,
  department TEXT,
  average_rating NUMERIC(3,2),
  average_difficulty NUMERIC(3,2),
  review_count INT,
  grade_letter CHAR(1),      -- A-F
  composite_score NUMERIC(3,0),
  last_updated TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Professor reviews table
CREATE TABLE professor_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  professor_id UUID REFERENCES professors(id) ON DELETE CASCADE,
  review_text TEXT,
  rating NUMERIC(3,2),
  difficulty NUMERIC(3,2),
  sentiment_positive INT,
  sentiment_aspects JSONB,   -- {clarity: 0.85, fairness: 0.72, ...}
  created_at TIMESTAMP DEFAULT NOW(),
  scraped_at TIMESTAMP
);

-- User schedules table
CREATE TABLE user_schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  semester TEXT,             -- "Fall 2025", "Spring 2025"
  name TEXT DEFAULT 'My Schedule',
  sections UUID[],           -- Array of section IDs
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_courses_code ON courses(course_code);
CREATE INDEX idx_sections_professor ON course_sections(professor_id);
CREATE INDEX idx_professors_name ON professors(name);
CREATE INDEX idx_reviews_professor ON professor_reviews(professor_id);
CREATE INDEX idx_schedules_user ON user_schedules(user_id);
```

### 9.2 pgvector Setup (Semantic Search)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column for course descriptions
ALTER TABLE courses ADD COLUMN description_embedding vector(1536);

-- Create index for semantic search
CREATE INDEX ON courses USING ivfflat (description_embedding vector_cosine_ops);

-- Query example: Find similar courses
SELECT * FROM courses 
WHERE description_embedding <-> 
  $1::vector < 0.5
ORDER BY description_embedding <-> $1::vector
LIMIT 10;
```

---

## 10. Milestones & Timeline

### Phase 1: MVP (Weeks 1-4)
- **Week 1**: Setup monorepo, Supabase, Vercel deployment
- **Week 2**: Frontend: Dashboard, course search, basic schedule builder
- **Week 3**: Backend: Course sync, professor scraping, sentiment analysis
- **Week 4**: Integration: Gemini API + MCP tools, testing, deployment

### Phase 2: Enhancement (Weeks 5-8)
- Real-time monitoring & alerts
- Learning style matching
- Schedule sharing

### Phase 3: Scale (Weeks 9+)
- DegreeWorks integration
- Advanced analytics
- Mobile app

---

## 11. Success Criteria

- ✅ First 50 CUNY students sign up within 2 weeks of launch
- ✅ 70% of users report improved schedule satisfaction
- ✅ Professor grade accuracy >85% vs. RateMyProf aggregate
- ✅ System response time <3 seconds for schedule optimization
- ✅ Zero critical bugs in first month
- ✅ NPS score >40

---

## 12. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| RateMyProf scraping blocked | High | Implement API fallback, cache aggressively, implement respectful scraping |
| Gemini API rate limit | Medium | Implement queuing, cache LLM responses, upgrade tier if needed |
| Database performance | High | Implement indexing, connection pooling, query optimization, monitoring |
| Student adoption | High | Beta test with 10+ students, iterate based on feedback |
| Course data sync failure | High | Implement retry logic, fallback to cached data, alerts |

---

## 13. Success Metrics & Analytics

### Key Metrics to Track
- Daily/weekly active users (DAU/WAU)
- Schedule optimization requests per day
- Professor rating lookups
- User retention (1 week, 1 month)
- System uptime and error rate
- API latency (p50, p95, p99)
- Cost per user (infrastructure)

### Analytics Integration
- Implement event tracking (Mixpanel, Segment, or Google Analytics 4)
- Monitor via Vercel Analytics Dashboard
- Set up error tracking (Sentry)
- Database query performance monitoring

