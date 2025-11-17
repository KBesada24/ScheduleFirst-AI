# Design Document: Button Routing and Integration System

## Overview

This design document outlines the architecture for ensuring all interactive buttons in the ScheduleFirst AI application function correctly with proper routing, backend API integration, and real-time DOM updates. The system follows a unidirectional data flow pattern with React hooks managing state and side effects.

### Key Design Principles

1. **Separation of Concerns**: UI components, business logic, and data access are clearly separated
2. **Single Source of Truth**: React state and Supabase database serve as authoritative data sources
3. **Optimistic UI Updates**: Immediate visual feedback before API responses
4. **Error Resilience**: Graceful degradation and user-friendly error messages
5. **Performance**: Minimal re-renders and efficient data fetching

## Architecture

### High-Level Component Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Button     │  │   Form       │  │   Link       │      │
│  │  Components  │  │  Components  │  │  Components  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Event Handler Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  onClick     │  │  onSubmit    │  │  onChange    │      │
│  │  Handlers    │  │  Handlers    │  │  Handlers    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    State Management Layer                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  useState    │  │  useAuth     │  │  Custom      │      │
│  │  Hooks       │  │  Context     │  │  Hooks       │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Access Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Supabase    │  │  Backend     │  │  React       │      │
│  │  Queries     │  │  API Calls   │  │  Router      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Supabase    │  │  FastAPI     │  │  Browser     │      │
│  │  PostgreSQL  │  │  Backend     │  │  History API │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Navigation System

#### Component: NavigationButton

**Purpose**: Handle all navigation-related button clicks

**Interface**:
```typescript
interface NavigationButtonProps {
  to: string;                    // Target route
  children: React.ReactNode;     // Button content
  variant?: "primary" | "ghost"; // Visual style
  requiresAuth?: boolean;        // Protected route flag
  onClick?: () => void;          // Optional pre-navigation callback
}
```

**Behavior**:
- Uses React Router's `Link` or `useNavigate` for navigation
- Checks authentication status for protected routes
- Provides visual feedback on hover/active states
- Handles loading states during navigation

#### Component: ProtectedRoute

**Purpose**: Wrap protected routes with authentication checks

**Interface**:
```typescript
interface ProtectedRouteProps {
  children: React.ReactNode;
  redirectTo?: string;  // Default: "/login"
}
```

**Behavior**:
- Checks `useAuth()` hook for user session
- Redirects unauthenticated users to login
- Shows loading spinner during auth check
- Preserves intended destination for post-login redirect

### 2. Authentication System

#### Component: AuthButton

**Purpose**: Handle authentication actions (login, signup, logout)

**Interface**:
```typescript
interface AuthButtonProps {
  action: "login" | "signup" | "logout";
  onSuccess?: (user: User) => void;
  onError?: (error: Error) => void;
  disabled?: boolean;
}
```

**Behavior**:
- Calls Supabase auth methods via `useAuth()` hook
- Manages loading state during API calls
- Displays success/error messages
- Navigates to appropriate page on success
- Implements retry logic for network failures

#### Hook: useAuth

**Purpose**: Centralized authentication state management

**Interface**:
```typescript
interface UseAuthReturn {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  error: Error | null;
}
```

**Implementation Details**:
- Uses Supabase Auth client
- Stores session in localStorage
- Provides auth state to entire app via Context
- Handles token refresh automatically

### 3. Course Search System

#### Component: SearchButton

**Purpose**: Trigger course search with filters

**Interface**:
```typescript
interface SearchButtonProps {
  query: string;
  filters: CourseFilters;
  onResults: (courses: CourseWithSections[]) => void;
  onError: (error: Error) => void;
}

interface CourseFilters {
  department?: string;
  semester?: string;
  modality?: string;
  timeSlot?: string;
}
```

**Behavior**:
- Validates search inputs before submission
- Calls `searchCourses()` from supabase-queries
- Updates course list in parent component
- Handles empty results gracefully
- Implements debouncing for real-time search

#### Hook: useCourseSearch

**Purpose**: Manage course search state and side effects

**Implementation**:
- Fetches courses from Supabase
- Caches results to minimize API calls
- Provides loading and error states
- Auto-refetches when filters change

### 4. Schedule Management System

#### Component: ScheduleActionButton

**Purpose**: Add/remove courses from schedule

**Interface**:
```typescript
interface ScheduleActionButtonProps {
  action: "add" | "remove";
  sectionId: string;
  scheduleId: string;
  onSuccess?: () => void;
  onConflict?: (conflicts: TimeConflict[]) => void;
}
```

**Behavior**:
- Calls `addSectionToSchedule()` or `removeSectionFromSchedule()`
- Checks for conflicts before adding
- Updates schedule grid immediately (optimistic update)
- Rolls back on error
- Shows conflict dialog if detected

#### Component: ScheduleGrid

**Purpose**: Visual calendar display of scheduled courses

**Interface**:
```typescript
interface ScheduleGridProps {
  sections: CourseSection[];
  conflicts?: TimeConflict[];
  onSectionClick?: (section: CourseSection) => void;
  editable?: boolean;
}
```

**Behavior**:
- Renders time slots (8 AM - 8 PM) in rows
- Renders days (Mon-Fri) in columns
- Maps sections to grid cells based on days/times
- Uses distinct colors for each course
- Highlights conflicts in red
- Supports drag-and-drop (future enhancement)

**Grid Update Logic**:
```typescript
function updateScheduleGrid(sections: CourseSection[]) {
  // 1. Clear existing grid
  // 2. Parse each section's days and times
  // 3. Calculate grid position (row, column, span)
  // 4. Render course block in correct cell
  // 5. Apply color coding
  // 6. Add conflict indicators if needed
}
```

### 5. AI Chat System

#### Component: ChatButton

**Purpose**: Send messages to AI assistant

**Interface**:
```typescript
interface ChatButtonProps {
  message: string;
  context?: ChatContext;
  onResponse: (response: AIResponse) => void;
  disabled?: boolean;
}

interface ChatContext {
  currentSchedule?: UserSchedule;
  preferences?: UserPreferences;
  semester?: string;
}

interface AIResponse {
  message: string;
  suggestedSchedule?: OptimizedSchedule;
  actions?: AIAction[];
}
```

**Behavior**:
- Validates message is not empty
- Calls `/api/chat/message` endpoint
- Displays "thinking" animation
- Parses AI response for schedule suggestions
- Updates chat history
- Triggers calendar update if schedule suggested

#### Calendar Integration Flow

```
User sends message
    ↓
ChatButton onClick
    ↓
POST /api/chat/message
    ↓
Backend calls Gemini AI with MCP tools
    ↓
AI generates schedule recommendation
    ↓
Response: { message, suggestedSchedule }
    ↓
Parse suggestedSchedule.courses[]
    ↓
Map courses to ScheduleGrid format
    ↓
Update ScheduleGrid component state
    ↓
ScheduleGrid re-renders with new courses
    ↓
Visual update complete (< 100ms)
```

### 6. Schedule Optimization System

#### Component: OptimizeButton

**Purpose**: Trigger AI schedule optimization

**Interface**:
```typescript
interface OptimizeButtonProps {
  courseCodes: string[];
  constraints: ScheduleConstraints;
  onOptimized: (schedules: OptimizedSchedule[]) => void;
}

interface ScheduleConstraints {
  preferredDays?: string[];
  earliestStartTime?: string;
  latestEndTime?: string;
  minProfessorRating?: number;
  avoidGaps?: boolean;
}

interface OptimizedSchedule {
  id: string;
  sections: CourseSection[];
  score: number;
  conflicts: TimeConflict[];
  reasoning: string;
}
```

**Behavior**:
- Validates course codes exist
- Calls `/api/schedule/optimize` endpoint
- Displays loading state with progress indicator
- Receives 3-5 optimized schedules
- Renders schedule options in preview cards
- Allows user to select and apply schedule

#### Schedule Application Flow

```
User clicks "Apply to My Schedule"
    ↓
OptimizeButton.applySchedule(scheduleId)
    ↓
Extract sections from selected schedule
    ↓
Call updateSchedule(scheduleId, { sections })
    ↓
Update Supabase database
    ↓
Trigger ScheduleGrid update
    ↓
Parse each section:
  - days: "MWF" → [Monday, Wednesday, Friday]
  - start_time: "10:00" → row 10
  - end_time: "11:15" → span 1.25 rows
    ↓
Calculate grid positions
    ↓
Render course blocks in calendar
    ↓
Apply color coding (blue, purple, green, etc.)
    ↓
Add course labels (code, time, location)
    ↓
Display conflict indicators if any
    ↓
Smooth transition animation (fade-in)
    ↓
Calendar update complete
```

### 7. Professor Rating System

#### Component: ProfessorButton

**Purpose**: View professor details and ratings

**Interface**:
```typescript
interface ProfessorButtonProps {
  professorId?: string;
  professorName?: string;
  onDataLoaded: (professor: ProfessorWithReviews) => void;
}
```

**Behavior**:
- Calls `getProfessorById()` or `getProfessorByName()`
- Opens modal/dialog with professor details
- Displays grade, ratings, reviews
- Shows sentiment analysis breakdown
- Provides comparison option

### 8. Admin Panel System

#### Component: AdminActionButton

**Purpose**: Execute admin operations (seed, clear database)

**Interface**:
```typescript
interface AdminActionButtonProps {
  action: "seed" | "clear";
  onSuccess: (message: string) => void;
  onError: (error: Error) => void;
  requireConfirmation?: boolean;
}
```

**Behavior**:
- Shows confirmation dialog for destructive actions
- Calls `seedDatabase()` or `clearDatabase()`
- Displays progress indicator
- Shows success/error toast notifications
- Logs operation details to console

## Data Models

### Course Section Model

```typescript
interface CourseSection {
  id: string;
  course_id: string;
  section_number: string;
  professor_name: string | null;
  days: string;              // "MWF", "TTh", etc.
  start_time: string;        // "10:00"
  end_time: string;          // "11:15"
  location: string | null;
  modality: string | null;   // "In-person", "Online", "Hybrid"
  enrolled: number | null;
  capacity: number | null;
}
```

### Schedule Grid Cell Model

```typescript
interface GridCell {
  day: "Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday";
  timeSlot: string;          // "10:00"
  course: CourseSection | null;
  rowSpan: number;           // Duration in 15-min increments
  color: string;             // CSS color for course
  hasConflict: boolean;
}
```

### AI Schedule Response Model

```typescript
interface AIScheduleResponse {
  schedules: OptimizedSchedule[];
  count: number;
  courses: Record<string, { id: string; name: string }>;
  total_sections: number;
}

interface OptimizedSchedule {
  sections: CourseSection[];
  score: number;
  conflicts: TimeConflict[];
  reasoning: string;
  metadata: {
    avgProfessorRating: number;
    totalCredits: number;
    daysPerWeek: number;
    gapHours: number;
  };
}
```

## Error Handling

### Error Types and Responses

1. **Network Errors**
   - Display: "Connection lost. Retrying..."
   - Action: Retry up to 3 times with exponential backoff
   - Fallback: Show cached data if available

2. **Authentication Errors**
   - Display: "Session expired. Please log in again."
   - Action: Redirect to login page
   - Preserve: Intended destination for post-login redirect

3. **Validation Errors**
   - Display: Field-specific error messages
   - Action: Highlight invalid fields in red
   - Prevent: Form submission until resolved

4. **API Errors (4xx)**
   - Display: User-friendly message from API response
   - Action: Log error details to console
   - Example: "Course not found for Fall 2025"

5. **Server Errors (5xx)**
   - Display: "Something went wrong. Please try again."
   - Action: Log error to monitoring service
   - Fallback: Suggest alternative actions

### Error Handling Pattern

```typescript
async function handleButtonClick() {
  try {
    setLoading(true);
    setError(null);
    
    const result = await apiCall();
    
    // Optimistic update
    updateUIImmediately(result);
    
    // Success feedback
    showSuccessToast("Action completed!");
    
  } catch (error) {
    // Rollback optimistic update
    revertUIChanges();
    
    // User-friendly error
    if (error.code === "NETWORK_ERROR") {
      setError("Connection lost. Please check your internet.");
    } else if (error.code === "AUTH_ERROR") {
      setError("Session expired. Redirecting to login...");
      setTimeout(() => navigate("/login"), 2000);
    } else {
      setError(error.message || "Something went wrong.");
    }
    
    // Log for debugging
    console.error("Button action failed:", error);
    
  } finally {
    setLoading(false);
  }
}
```

## Testing Strategy

### Unit Tests

1. **Button Components**
   - Test onClick handlers are called
   - Test loading states render correctly
   - Test disabled states prevent clicks
   - Test error states display messages

2. **Hooks**
   - Test data fetching logic
   - Test state updates
   - Test error handling
   - Test cleanup on unmount

3. **Utility Functions**
   - Test time parsing (days, start/end times)
   - Test conflict detection algorithm
   - Test grid position calculations
   - Test color assignment logic

### Integration Tests

1. **Navigation Flow**
   - Test unauthenticated redirect to login
   - Test successful login navigates to dashboard
   - Test protected routes require auth
   - Test logout clears session and redirects

2. **Course Search Flow**
   - Test search with query returns results
   - Test filters update results
   - Test empty results show message
   - Test loading states during search

3. **Schedule Management Flow**
   - Test adding section updates grid
   - Test removing section updates grid
   - Test conflict detection triggers alert
   - Test schedule persistence to database

4. **AI Integration Flow**
   - Test chat message sends to backend
   - Test AI response updates chat history
   - Test suggested schedule updates calendar
   - Test schedule application saves to database

### End-to-End Tests

1. **Complete User Journey**
   - Sign up → Login → Search courses → Add to schedule → Optimize → View calendar
   - Test all buttons work in sequence
   - Test data persists across page refreshes
   - Test error recovery at each step

2. **Calendar Update Scenarios**
   - AI chat suggests schedule → Calendar updates
   - Optimization returns schedules → Preview updates → Apply updates calendar
   - Manual add/remove → Calendar updates immediately
   - Conflict detected → Visual indicator appears

## Performance Considerations

### Optimization Techniques

1. **Debouncing**
   - Search input: 300ms delay
   - Filter changes: 200ms delay
   - Prevents excessive API calls

2. **Memoization**
   - Course list rendering: `useMemo`
   - Schedule grid calculations: `useMemo`
   - Prevents unnecessary re-renders

3. **Lazy Loading**
   - Professor reviews: Load on demand
   - Course sections: Paginate results
   - Images: Lazy load avatars

4. **Caching**
   - Course data: Cache for 5 minutes
   - Professor ratings: Cache for 1 hour
   - User schedules: Cache until mutation

5. **Optimistic Updates**
   - Add/remove sections: Update UI immediately
   - Rollback on error
   - Improves perceived performance

### Performance Targets

- Button click response: < 50ms
- API call initiation: < 100ms
- DOM update after data load: < 100ms
- Calendar grid render: < 200ms
- Page navigation: < 300ms
- Full page load: < 2 seconds

## Security Considerations

1. **Authentication**
   - All API calls include auth token
   - Tokens stored securely in httpOnly cookies
   - Automatic token refresh before expiry

2. **Authorization**
   - Row-Level Security (RLS) in Supabase
   - Users can only access their own schedules
   - Admin actions require admin role

3. **Input Validation**
   - Client-side validation for UX
   - Server-side validation for security
   - Sanitize all user inputs

4. **CORS**
   - Backend allows only frontend origin
   - Credentials included in requests
   - Preflight requests handled correctly

5. **Rate Limiting**
   - Backend limits requests per user
   - Frontend implements exponential backoff
   - Prevents abuse and DoS attacks

## Accessibility

1. **Keyboard Navigation**
   - All buttons accessible via Tab
   - Enter/Space triggers onClick
   - Focus indicators visible

2. **Screen Readers**
   - Buttons have descriptive labels
   - Loading states announced
   - Error messages announced
   - ARIA attributes used correctly

3. **Visual Indicators**
   - High contrast colors
   - Loading spinners
   - Success/error icons
   - Disabled state styling

4. **Responsive Design**
   - Buttons work on mobile
   - Touch targets ≥ 44x44px
   - Calendar grid adapts to screen size

## Deployment Considerations

1. **Environment Variables**
   - Frontend: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
   - Backend: `GEMINI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
   - Separate configs for dev/staging/prod

2. **Build Process**
   - TypeScript compilation
   - Vite bundling and optimization
   - Tree shaking unused code
   - Code splitting for routes

3. **Monitoring**
   - Log all button clicks (analytics)
   - Track API response times
   - Monitor error rates
   - Alert on critical failures

4. **Rollback Strategy**
   - Keep previous build artifacts
   - Feature flags for new buttons
   - Gradual rollout for major changes
   - Quick rollback if issues detected
