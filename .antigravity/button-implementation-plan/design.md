# Frontend-Backend Integration Design Philosophy

## Overview

This document outlines the design philosophy and architectural principles for integrating the React frontend (located in `src/`) with the FastAPI backend services (located in `services/`). The integration follows a modular, type-safe, and resilient approach that ensures seamless communication between UI components and backend APIs.

## Core Design Principles

### 1. **Separation of Concerns**
- **Frontend**: Handles UI rendering, user interactions, and client-side state management
- **Backend**: Handles business logic, AI processing, database operations, and data scraping
- **API Layer**: Serves as a clean contract between frontend and backend with typed interfaces

### 2. **Type Safety End-to-End**
- TypeScript interfaces in frontend match Pydantic models in backend
- Shared type definitions ensure compile-time safety
- API client automatically handles serialization/deserialization

### 3. **Progressive Enhancement**
- Core features work with direct Supabase queries (existing)
- Enhanced features utilize backend AI services (new)
- Graceful degradation if backend is unavailable

### 4. **Resilient Communication**
- Automatic retry logic with exponential backoff
- Error boundaries prevent UI crashes
- Loading states provide immediate user feedback
- Optimistic updates where appropriate

---

## Button-to-API Integration Architecture

Each button component in the UI follows a consistent integration pattern:

```
User clicks button → Validation → API call → Loading state → Response handling → UI update
```

### Integration Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  Button Components (src/components/ui/*-button.tsx)         │
│  - OptimizeButton, ChatButton, SearchButton, etc.           │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    INTEGRATION LAYER                         │
│  API Endpoints (src/lib/api-endpoints.ts)                   │
│  - Typed functions for each endpoint                        │
│  - Request/response interfaces                              │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    TRANSPORT LAYER                           │
│  API Client (src/lib/api-client.ts)                         │
│  - HTTP client with interceptors                            │
│  - Auth token injection                                     │
│  - Error handling                                           │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼ HTTP/JSON
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND API LAYER                         │
│  FastAPI Server (services/api_server.py)                    │
│  - Route handlers                                           │
│  - Request validation (Pydantic)                            │
│  - Response serialization                                   │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                             │
│  MCP Server (services/mcp_server/)                          │
│  - Business logic                                           │
│  - AI integration (Gemini)                                  │
│  - Database operations                                      │
│  - Data processing                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Button Integration Patterns

### Pattern 1: Search/Query Buttons
**Examples**: SearchButton, ProfessorButton

**Philosophy**: Immediate feedback with cached results
```
1. User enters search query
2. Client-side validation (required fields, format)
3. Debounced API call (prevents excessive requests)
4. Cache check (5-minute TTL)
5. Display results with loading skeleton
6. Handle empty states gracefully
```

**Design Decision**: Use direct Supabase queries for simple searches, backend API for complex queries requiring AI processing.

### Pattern 2: Action Buttons
**Examples**: ScheduleActionButton (add/remove)

**Philosophy**: Optimistic updates with rollback
```
1. User clicks action button
2. Optimistic UI update (immediate feedback)
3. Conflict detection (if adding)
4. API call to persist change
5. If error: rollback UI to previous state
6. If success: confirm with toast notification
```

**Design Decision**: Optimistic updates improve perceived performance, critical for schedule manipulation.

### Pattern 3: AI Processing Buttons
**Examples**: OptimizeButton, ChatButton

**Philosophy**: Progressive disclosure with status updates
```
1. User initiates AI action
2. Comprehensive validation (course codes, constraints)
3. Show progress indicator (simulated + real)
4. Stream updates if available
5. Parse AI response
6. Update UI with structured data
7. Provide explanation/reasoning
```

**Design Decision**: AI operations are expensive; show clear progress to manage user expectations.

### Pattern 4: Navigation Buttons
**Examples**: NavigationButton

**Philosophy**: Authentication-aware routing
```
1. User clicks navigation
2. Check if route requires auth
3. If unauthenticated: store return URL, redirect to login
4. If authenticated: navigate directly
5. Execute pre-navigation callbacks
```

**Design Decision**: Centralize auth checks to prevent scattered logic.

### Pattern 5: Authentication Buttons
**Examples**: AuthButton (login/signup/logout)

**Philosophy**: Secure, user-friendly authentication flow
```
1. User submits credentials
2. Client-side validation
3. Supabase Auth API call
4. Session management
5. Redirect to intended destination
6. Clear sensitive data
```

**Design Decision**: Use Supabase Auth for security, handle tokens automatically.

---

## Specific Button Integration Designs

### 1. OptimizeButton → `/api/schedule/optimize`

**Purpose**: Generate AI-optimized schedules based on course selections and constraints

**Flow**:
```typescript
[User Input] → [Validation] → [Progress Simulation] → [API Call] → [Parse Schedules] → [Display Options]
```

**Validation Rules**:
- At least 1 course code required
- Course codes must be non-empty strings
- Time range must be valid (earliest < latest)
- Professor rating must be 0-5
- Constraints are optional but validated if present

**API Contract**:
```typescript
Request: {
  courseCodes: string[];        // ["CSC 101", "MATH 201"]
  semester: string;              // "Fall 2025"
  constraints?: {
    preferredDays?: string[];    // ["Monday", "Wednesday"]
    earliestStartTime?: string;  // "09:00"
    latestEndTime?: string;      // "17:00"
    minProfessorRating?: number; // 4.0
    avoidGaps?: boolean;         // true
  };
}

Response: {
  schedules: OptimizedSchedule[];
  count: number;
  courses: Record<string, { id: string; name: string }>;
  total_sections: number;
}
```

**Error Handling**:
- Network errors → Retry 3x with exponential backoff
- 404 (no courses found) → Show "no sections available" message
- 400 (invalid constraints) → Display specific validation errors
- 500 → Generic error with retry option

**UI States**:
- Idle: Show button with sparkle icon
- Loading: Show spinner + progress bar (0-90% simulated, 100% on complete)
- Success: Update with schedules, show count in toast
- Error: Show error toast, keep button enabled for retry

---

### 2. ChatButton → `/api/chat/message`

**Purpose**: Send messages to AI assistant for conversational schedule help

**Flow**:
```typescript
[User Message] → [Validation] → [Send] → [Thinking State] → [Parse Response] → [Display + Actions]
```

**Validation Rules**:
- Message must not be empty
- Message trimmed before sending
- Context is optional but recommended

**API Contract**:
```typescript
Request: {
  message: string;
  context?: {
    currentSchedule?: UserSchedule;
    preferences?: UserPreferences;
    semester?: string;
  };
}

Response: {
  message: string;               // AI response text
  suggestedSchedule?: Schedule;  // Structured schedule if suggested
  actions?: AIAction[];          // Actionable items (add course, etc.)
}
```

**Special Handling**:
- Detect schedule suggestions in response
- Parse action items (e.g., "Add CSC 101 Section 02")
- Provide quick-action buttons for suggestions
- Maintain conversation context

---

### 3. SearchButton → Supabase (existing) + `/api/courses/search` (enhanced)

**Purpose**: Search for courses with filtering

**Dual Mode**:
1. **Direct Mode** (existing): Use `searchCourses()` from `supabase-queries.ts`
2. **Enhanced Mode** (new): Use `/api/courses/search` for AI-powered semantic search

**API Contract** (Enhanced):
```typescript
Request: {
  query?: string;
  department?: string;
  semester?: string;
  modality?: string;
  timeSlot?: string;
  limit?: number;
}

Response: {
  courses: CourseWithSections[];
  count: number;
  searchType: "exact" | "semantic";  // Indicates search method used
}
```

**Design Decision**: Keep direct Supabase queries as default for performance, add backend API for advanced features (e.g., "classes similar to CSC 101").

---

### 4. ScheduleActionButton → Supabase (existing)

**Purpose**: Add/remove course sections from user schedule

**Current State**: Already integrated with Supabase
**Enhancement**: Add backend validation endpoint for complex conflict detection

**New Endpoint**: `POST /api/schedule/validate`
```typescript
Request: {
  scheduleId: string;
  sectionId: string;
  action: "add" | "remove";
}

Response: {
  valid: boolean;
  conflicts: TimeConflict[];
  warnings: string[];          // Soft warnings (e.g., "long travel time")
  suggestions: CourseSection[];  // Alternative sections if conflicts found
}
```

---

### 5. ProfessorButton → `/api/professor/{name}`

**Purpose**: Fetch professor details and ratings

**Flow**:
```typescript
[Click Professor] → [API Call] → [Parse Reviews] → [Display Modal]
```

**API Contract**:
```typescript
Request: {
  name: string;        // Professor name
  university?: string; // Filter by CUNY school
}

Response: {
  professor: {
    id: string;
    name: string;
    department: string;
    average_rating: number;
    average_difficulty: number;
    review_count: number;
    grade_letter: string;      // A-F grade
    composite_score: number;    // 0-100
  };
  reviews: Review[];
  review_count: number;
}
```

**Caching Strategy**: Cache professor data for 1 hour (less volatile than course sections)

---

### 6. RefreshButton → Multiple endpoints

**Purpose**: Refresh dashboard data

**Design Pattern**: Parallel API calls with Promise.all
```typescript
Promise.all([
  getUserSchedules(userId),
  getUpcomingClasses(userId),
  getRecentActivity(userId)
])
```

**Loading State**: Show spinner on button, disable until all complete

---

## Error Handling Philosophy

### Error Categories

1. **Network Errors** (fetch failed, timeout)
   - Auto-retry 3 times with exponential backoff (1s, 2s, 4s)
   - Show "Connection lost" message
   - Provide manual retry button

2. **Authentication Errors** (401, 403)
   - Clear expired session
   - Redirect to login
   - Preserve intended destination in sessionStorage

3. **Validation Errors** (400)
   - Display field-specific errors inline
   - Highlight invalid fields
   - Prevent submission until fixed

4. **Not Found Errors** (404)
   - Show user-friendly "not found" message
   - Suggest alternatives (e.g., similar courses)

5. **Server Errors** (500)
   - Log to monitoring service
   - Show generic error message
   - Provide support contact

### Error User Experience

```typescript
// Consistent error notification pattern
toast({
  title: "Action Failed",           // Clear, action-oriented
  description: error.message,       // Specific reason
  variant: "destructive",           // Visual urgency
  action: {                         // Actionable fix
    label: "Retry",
    onClick: () => retryAction()
  }
});
```

---

## Loading States Philosophy

### Skeleton Screens
For content that takes \>500ms to load:
- Course list → Show 5 skeleton cards
- Schedule grid → Show grid outline with pulsing blocks
- Professor card → Show card with pulsing text lines

### Progress Indicators
For AI operations that take \>2s:
- Optimize button → Progress bar (0-100%)
- Chat → "Thinking" animation with dots
- Batch operations → "Processing 3/10 items"

### Optimistic Updates
For actions with high success rate:
- Add to schedule → Immediately show in grid, rollback if error
- Update preferences → Update UI first, sync in background

---

## State Management Philosophy

### Local State (useState)
- Button loading states
- Form inputs
- UI toggles (modals, dropdowns)

### Server State (Custom Hooks)
- `useCourseSearch()` → Caches search results
- `useScheduleGrid()` → Manages schedule sections
- `useAuth()` → Manages user session

### URL State (React Router)
- Current page
- Search query parameters
- Active filters

**Design Decision**: Avoid global state management (Redux/Zustand) to keep complexity low. Use React Query pattern with custom hooks.

---

## Performance Optimization

### 1. Request Debouncing
```typescript
// SearchButton: Wait 300ms after typing stops
const debouncedSearch = useDebouncedCallback(performSearch, 300);
```

### 2. Response Caching
```typescript
// Cache policy
- Course searches: 5 minutes
- Professor data: 1 hour
- User schedules: No cache (real-time)
```

### 3. Lazy Loading
```typescript
// Load heavy components only when needed
const ProfessorModal = lazy(() => import('./ProfessorDetailModal'));
```

### 4. Memoization
```typescript
// Expensive calculations
const conflicts = useMemo(() => detectConflicts(sections), [sections]);
```

---

## Security Considerations

### 1. Authentication
- All API calls include Supabase auth token in Authorization header
- Token refreshed automatically by `api-client.ts`
- Session validated on protected routes

### 2. Input Sanitization
- All user inputs validated on both client and server
- SQL injection prevention via Supabase parameterized queries
- XSS prevention via React's built-in escaping

### 3. Rate Limiting
- Backend: 100 requests/minute per user
- Frontend: Debouncing prevents excessive requests
- Heavy operations (AI): 10 requests/hour per user

### 4. Data Privacy
- User data encrypted at rest (Supabase)
- HTTPS for all communications
- No sensitive data in localStorage (only sessionStorage)

---

## Monitoring and Analytics

### Button Click Tracking
```typescript
// Track all button interactions
trackEvent({
  name: "button_click",
  properties: {
    button: "optimize",
    timestamp: new Date().toISOString(),
    context: { coursesCount: 5 }
  }
});
```

### Performance Monitoring
```typescript
// Measure API response times
measureRenderTime("OptimizeButton");
```

### Error Tracking
- All API errors logged to backend
- Client-side errors captured by ErrorBoundary
- User-facing errors shown in UI

---

## Testing Philosophy

### Unit Tests
- Each button component tested in isolation
- API client functions mocked
- Validation logic tested with edge cases

### Integration Tests
- Button → API → Response flow
- Use MSW (Mock Service Worker) for API mocking
- Test error scenarios

### End-to-End Tests
- Critical user flows (search → add to schedule → optimize)
- Use Playwright for browser automation
- Run in CI pipeline before deployment

---

## Deployment Strategy

### Development
- Frontend: `npm run dev` (Vite, port 5173)
- Backend: `python services/api_server.py` (port 8000)
- CORS: Allow localhost:5173

### Production
- Frontend: Deployed on Vercel (automatic from main branch)
- Backend: Deployed on Railway/Fly.io
- Environment variables managed per environment
- API base URL configured via `VITE_API_URL`

---

## Migration Strategy

### Phase 1: Backend Setup (Current)
- [x] FastAPI server running
- [x] Basic endpoints implemented
- [x] CORS configured

### Phase 2: API Client Integration
- [ ] Update `api-client.ts` with production URL
- [ ] Test all endpoints with real backend
- [ ] Handle environment switching (dev/prod)

### Phase 3: Button Migration
- [ ] OptimizeButton → `/api/schedule/optimize`
- [ ] ChatButton → `/api/chat/message`
- [ ] ProfessorButton → `/api/professor/{name}`
- [ ] SearchButton (enhanced mode)

### Phase 4: Testing
- [ ] Integration tests
- [ ] Load testing
- [ ] User acceptance testing

### Phase 5: Production Deployment
- [ ] Deploy backend to Railway
- [ ] Update frontend environment variables
- [ ] Monitor error rates
- [ ] Gradual rollout with feature flags

---

## Conclusion

This design philosophy ensures a robust, type-safe integration between the React frontend and FastAPI backend. Each button follows consistent patterns for validation, error handling, loading states, and user feedback. The architecture is designed for resilience, performance, and maintainability while providing an excellent user experience.
