# Data Flow Diagrams

## 1. Course Data Request Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │     │   API    │     │  Cache   │     │ Database │
│ (React)  │     │ Server   │     │ Manager  │     │(Supabase)│
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ GET /api/courses               │                │
     │ ?semester=Spring 2025          │                │
     │ &university=Baruch             │                │
     │───────────────>│                │                │
     │                │                │                │
     │                │ cache.get(key) │                │
     │                │───────────────>│                │
     │                │                │                │
     │                │   cache miss   │                │
     │                │<───────────────│                │
     │                │                │                │
     │                │ get_courses_by_semester()      │
     │                │────────────────────────────────>│
     │                │                │                │
     │                │                │    courses[]   │
     │                │<────────────────────────────────│
     │                │                │                │
     │                │ cache.set(key, courses)        │
     │                │───────────────>│                │
     │                │                │                │
     │   { courses, metadata }        │                │
     │<───────────────│                │                │
     │                │                │                │
```

## 2. Auto-Population Flow (Empty/Stale Data)

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Client  │  │   API    │  │Population│  │Freshness │  │ Scraper  │  │ Database │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │             │             │
     │ GET /api/courses          │             │             │             │
     │────────────>│             │             │             │             │
     │             │             │             │             │             │
     │             │ ensure_course_data()      │             │             │
     │             │────────────>│             │             │             │
     │             │             │             │             │             │
     │             │             │ is_fresh?   │             │             │
     │             │             │────────────>│             │             │
     │             │             │             │             │             │
     │             │             │   FALSE     │             │             │
     │             │             │<────────────│             │             │
     │             │             │             │             │             │
     │             │             │ acquire_lock()            │             │
     │             │             │─────────┐   │             │             │
     │             │             │         │   │             │             │
     │             │             │<────────┘   │             │             │
     │             │             │             │             │             │
     │             │             │ sync_courses_job()        │             │
     │             │             │────────────────────────────────────────>│
     │             │             │             │             │             │
     │             │             │             │ scrape()    │             │
     │             │             │             │────────────>│             │
     │             │             │             │             │             │
     │             │             │             │  courses[]  │             │
     │             │             │             │<────────────│             │
     │             │             │             │             │             │
     │             │             │             │ insert_courses()          │
     │             │             │────────────────────────────────────────>│
     │             │             │             │             │             │
     │             │             │ release_lock()            │             │
     │             │             │─────────┐   │             │             │
     │             │             │         │   │             │             │
     │             │             │<────────┘   │             │             │
     │             │             │             │             │             │
     │             │  success    │             │             │             │
     │             │<────────────│             │             │             │
     │             │             │             │             │             │
     │             │ get_courses_by_semester() │             │             │
     │             │──────────────────────────────────────────────────────>│
     │             │             │             │             │             │
     │             │             │             │             │  courses[]  │
     │             │<──────────────────────────────────────────────────────│
     │             │             │             │             │             │
     │ { courses, metadata }     │             │             │             │
     │<────────────│             │             │             │             │
```

## 3. Professor Grade Request Flow

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Client  │  │ MCP Tool │  │Population│  │  RMP     │  │ Gemini   │  │ Database │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │             │             │
     │ get_professor_grade()     │             │             │             │
     │────────────>│             │             │             │             │
     │             │             │             │             │             │
     │             │ ensure_professor_data()   │             │             │
     │             │────────────>│             │             │             │
     │             │             │             │             │             │
     │             │             │ get_professor_by_name()   │             │
     │             │             │─────────────────────────────────────────>│
     │             │             │             │             │             │
     │             │             │             │             │    NULL     │
     │             │             │<─────────────────────────────────────────│
     │             │             │             │             │             │
     │             │             │ scrape_professor_data()   │             │
     │             │             │────────────>│             │             │
     │             │             │             │             │             │
     │             │             │  { prof, reviews }        │             │
     │             │             │<────────────│             │             │
     │             │             │             │             │             │
     │             │             │ insert_professor()        │             │
     │             │             │─────────────────────────────────────────>│
     │             │             │             │             │             │
     │             │             │ insert_reviews()          │             │
     │             │             │─────────────────────────────────────────>│
     │             │             │             │             │             │
     │             │             │ analyze_reviews()         │             │
     │             │             │────────────────────────────>│            │
     │             │             │             │             │             │
     │             │             │  { sentiments }           │             │
     │             │             │<────────────────────────────│            │
     │             │             │             │             │             │
     │             │             │ update_professor_grades() │             │
     │             │             │─────────────────────────────────────────>│
     │             │             │             │             │             │
     │             │   success   │             │             │             │
     │             │<────────────│             │             │             │
     │             │             │             │             │             │
     │             │ get_professor_by_name()   │             │             │
     │             │──────────────────────────────────────────────────────>│
     │             │             │             │             │             │
     │             │             │             │             │  professor  │
     │             │<──────────────────────────────────────────────────────│
     │             │             │             │             │             │
     │ { grade, metrics }        │             │             │             │
     │<────────────│             │             │             │             │
```

## 4. Schedule Optimization Flow

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Client  │  │ MCP Tool │  │Constraint│  │ Database │  │  Gemini  │
│          │  │          │  │ Solver   │  │          │  │   (AI)   │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │             │
     │ generate_optimized_schedule()          │             │
     │ { courses: [...], constraints: {...} } │             │
     │────────────>│             │             │             │
     │             │             │             │             │
     │             │ ensure_course_data() [for each course] │
     │             │─────────────────────────>│             │
     │             │             │             │             │
     │             │ get_course_by_code()     │             │
     │             │─────────────────────────>│             │
     │             │             │  course    │             │
     │             │<─────────────────────────│             │
     │             │             │             │             │
     │             │ get_sections_by_course() │             │
     │             │─────────────────────────>│             │
     │             │             │ sections[] │             │
     │             │<─────────────────────────│             │
     │             │             │             │             │
     │             │ generate_optimized_schedules()        │
     │             │────────────>│             │             │
     │             │             │             │             │
     │             │             │ _generate_combinations() │
     │             │             │─────────┐   │             │
     │             │             │         │   │             │
     │             │             │<────────┘   │             │
     │             │             │             │             │
     │             │             │ detect_conflicts()       │
     │             │             │─────────┐   │             │
     │             │             │         │   │             │
     │             │             │<────────┘   │             │
     │             │             │             │             │
     │             │             │ _calculate_scores()      │
     │             │             │─────────┐   │             │
     │             │             │         │   │             │
     │             │             │<────────┘   │             │
     │             │             │             │             │
     │             │ schedules[] │             │             │
     │             │<────────────│             │             │
     │             │             │             │             │
     │ { schedules, metadata }   │             │             │
     │<────────────│             │             │             │
```

## 5. Circuit Breaker Flow

```
                    ┌─────────────────────────────────────┐
                    │         CIRCUIT BREAKER             │
                    │                                     │
     Request ──────>│  ┌────────┐    ┌────────┐          │
                    │  │ CLOSED │───>│  OPEN  │          │
                    │  └────────┘    └────────┘          │
                    │       ▲            │               │
                    │       │            │ timeout       │
                    │       │            ▼               │
                    │       │      ┌───────────┐         │
                    │       └──────│ HALF_OPEN │         │
                    │   success    └───────────┘         │
                    │                    │               │
                    │               failure              │
                    │                    │               │
                    │                    ▼               │
                    │              ┌────────┐            │
                    │              │  OPEN  │            │
                    │              └────────┘            │
                    └─────────────────────────────────────┘

CLOSED → OPEN: After 5 consecutive failures
OPEN → HALF_OPEN: After 60 second recovery timeout
HALF_OPEN → CLOSED: After successful test requests
HALF_OPEN → OPEN: On any failure during testing
```

## 6. Background Job Scheduling

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKGROUND SCHEDULER                                 │
│                        (APScheduler AsyncIO)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│ sync_courses_job  │     │ scrape_reviews_job│     │update_grades_job  │
│                   │     │                   │     │                   │
│ Schedule:         │     │ Schedule:         │     │ Schedule:         │
│ Sunday 2:00 AM    │     │ Monday 3:00 AM    │     │ Monday 5:00 AM    │
│                   │     │                   │     │                   │
│ Can also be       │     │ Can also be       │     │ Can also be       │
│ triggered on-     │     │ triggered on-     │     │ triggered on-     │
│ demand via        │     │ demand via        │     │ demand via        │
│ DataPopulation    │     │ DataPopulation    │     │ DataPopulation    │
│ Service           │     │ Service           │     │ Service           │
└───────────────────┘     └───────────────────┘     └───────────────────┘
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│ CUNY Global       │     │ RateMyProfessors  │     │ Gemini AI         │
│ Search Scraper    │     │ GraphQL API       │     │ Sentiment         │
│                   │     │                   │     │ Analysis          │
└───────────────────┘     └───────────────────┘     └───────────────────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      ▼
                              ┌───────────────┐
                              │   SUPABASE    │
                              │  (Postgres)   │
                              └───────────────┘
```

## 7. Cache Layer Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CACHE MANAGER                                     │
│                         (InMemoryCache LRU)                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          Cache Store                                 │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │   │
│  │  │ courses:abc123   │  │ professors:xyz   │  │ sync:courses:... │   │   │
│  │  │ TTL: 300s        │  │ TTL: 300s        │  │ TTL: 60s         │   │   │
│  │  │ Access: 12:30:45 │  │ Access: 12:31:00 │  │ Access: 12:29:00 │   │   │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Max Size: 1000 entries                                                     │
│  Eviction: LRU (Least Recently Used)                                        │
│  Default TTL: 300 seconds                                                   │
│                                                                             │
│  Operations:                                                                │
│  • get(key) → value or None                                                 │
│  • set(key, value, ttl) → void                                              │
│  • delete(key) → void                                                       │
│  • cleanup_expired() → count                                                │
│                                                                             │
│  Statistics:                                                                │
│  • hits: 1,234                                                              │
│  • misses: 456                                                              │
│  • evictions: 78                                                            │
│  • sets: 567                                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```
