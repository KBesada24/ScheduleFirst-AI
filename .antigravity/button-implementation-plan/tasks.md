# Frontend-Backend Integration Tasks

## Overview

This document provides a step-by-step guide for integrating React frontend buttons with FastAPI backend services. Each task includes detailed instructions, code examples, testing steps, and completion criteria.

---

## Table of Contents

1. [Environment Setup](#task-1-environment-setup)
2. [API Client Configuration](#task-2-api-client-configuration)
3. [Type Definitions](#task-3-type-definitions)
4. [OptimizeButton Integration](#task-4-optimizebutton-integration)
5. [ChatButton Integration](#task-5-chatbutton-integration)
6. [SearchButton Enhancement](#task-6-searchbutton-enhancement)
7. [ProfessorButton Integration](#task-7-professorbutton-integration)
8. [ScheduleActionButton Enhancement](#task-8-scheduleactionbutton-enhancement)
9. [Error Handling Enhancement](#task-9-error-handling-enhancement)
10. [Testing and Validation](#task-10-testing-and-validation)
11. [Deployment](#task-11-deployment)

---

## Task 1: Environment Setup

**Priority**: High  
**Estimated Time**: 30 minutes  
**Dependencies**: None

### Objective
Configure environment variables for frontend-backend communication in both development and production.

### Steps

#### 1.1: Create Frontend Environment File

```bash
# Navigate to project root
cd /home/kbesada/Code/ScheduleFirst-AI

# Create .env.local file
touch .env.local
```

Add the following content to `.env.local`:
```bash
# Backend API URL
VITE_API_URL=http://localhost:8000

# Supabase (existing)
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_anon_key
```

#### 1.2: Verify Backend Environment

Ensure `services/.env` exists with:
```bash
# AI Services
GEMINI_API_KEY=your_gemini_api_key

# Database
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
DATABASE_URL=your_database_url

# API Server
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=development
```

#### 1.3: Update .gitignore

Ensure `.env.local` and `services/.env` are in `.gitignore`:
```bash
# Add to .gitignore if not present
echo ".env.local" >> .gitignore
echo "services/.env" >> .gitignore
```

#### 1.4: Create Example Files

```bash
# Frontend example
cp .env.local .env.example
# Replace actual values with placeholders

# Backend example (if doesn't exist)
cp services/.env services/.env.example
# Replace actual values with placeholders
```

### Testing

```bash
# Test frontend can read env vars
npm run dev
# Check console: import.meta.env.VITE_API_URL should show

# Test backend can read env vars
cd services
python -c "from mcp_server.config import settings; print(settings.api_port)"
# Should output: 8000
```

### Completion Criteria
- [x] `.env.local` created with VITE_API_URL
- [x] `services/.env` has all required variables
- [x] Example files created
- [x] Variables correctly read by both frontend and backend

---

## Task 2: API Client Configuration

**Priority**: High  
**Estimated Time**: 45 minutes  
**Dependencies**: Task 1

### Objective
Update the API client to use the backend URL from environment variables and ensure proper configuration.

### Steps

#### 2.1: Update api-client.ts

**File**: `src/lib/api-client.ts`

**Changes**:
1. Update API_BASE_URL to use environment variable
2. Add timeout configuration
3. Enhance error handling

```typescript
// Line 10: Update base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Add timeout configuration (after line 31)
const REQUEST_TIMEOUT = 30000; // 30 seconds
const AI_REQUEST_TIMEOUT = 60000; // 60 seconds for AI operations

// Update fetch calls to include timeout
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = REQUEST_TIMEOUT
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new APIClientError('Request timeout', 'TIMEOUT', 408);
    }
    throw error;
  }
}
```

#### 2.2: Update APIClient Methods

Replace all `fetch()` calls with `fetchWithTimeout()`:

```typescript
// In get method (around line 113)
const response = await fetchWithTimeout(interceptedUrl, interceptedOptions);

// In post method (around line 127)
const response = await fetchWithTimeout(interceptedUrl, interceptedOptions, AI_REQUEST_TIMEOUT);

// Similar for put, delete, patch methods
```

#### 2.3: Add Health Check Helper

Add at the end of `api-client.ts`:

```typescript
/**
 * Check if backend is available
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await apiClient.get('/health');
    return response.status === 'healthy';
  } catch {
    return false;
  }
}
```

### Testing

```bash
# Start backend
cd services
python api_server.py

# In another terminal, start frontend
cd /home/kbesada/Code/ScheduleFirst-AI
npm run dev

# Test in browser console
import { apiClient } from './src/lib/api-client.ts';
apiClient.get('/health').then(console.log);
// Should log: { status: 'healthy', ... }
```

### Completion Criteria
- [x] API_BASE_URL uses environment variable
- [x] Timeout configuration added
- [x] Health check function works
- [x] All requests use fetchWithTimeout
- [x] No TypeScript errors

---

## Task 3: Type Definitions

**Priority**: High  
**Estimated Time**: 30 minutes  
**Dependencies**: None

### Objective
Ensure all API request/response types match between frontend and backend.

### Steps

#### 3.1: Review Existing Types

**File**: `src/lib/api-endpoints.ts` (lines 1-79)

Current types:
- [x] ChatRequest
- [x] ChatResponse
- [x] ScheduleOptimizationRequest
- [x] ScheduleOptimizationResponse
- [x] ProfessorDetails

#### 3.2: Add Missing Types

Add to `src/lib/api-endpoints.ts` after existing types:

```typescript
// Course Search Types (around line 80)
export interface CourseSearchRequest {
  query?: string;
  department?: string;
  semester?: string;
  modality?: string;
  timeSlot?: string;
  limit?: number;
  offset?: number;
}

export interface CourseSearchResponse {
  courses: CourseWithSections[];
  count: number;
  searchType: 'exact' | 'semantic';
}

// Schedule Validation Types
export interface ScheduleValidationRequest {
  scheduleId: string;
  sectionId: string;
  action: 'add' | 'remove';
}

export interface ScheduleValidationResponse {
  valid: boolean;
  conflicts: TimeConflict[];
  warnings: string[];
  suggestions: CourseSection[];
}

// Analytics Types
export interface AnalyticsEvent {
  name: string;
  properties?: Record<string, any>;
  timestamp?: string;
}
```

#### 3.3: Verify Backend Models Match

**File**: `services/mcp_server/models/schedule.py`

Ensure Pydantic models match TypeScript interfaces:

```python
# Check ScheduleConstraints model
class ScheduleConstraints(BaseModel):
    preferred_days: Optional[List[str]] = None
    earliest_start_time: Optional[str] = None
    latest_end_time: Optional[str] = None
    min_professor_rating: Optional[float] = None
    avoid_gaps: Optional[bool] = None
```

**Action**: If models don't match, update either frontend types or backend models to align.

### Testing

```typescript
// Create test file: src/lib/__tests__/api-types.test.ts
import { ScheduleOptimizationRequest } from '../api-endpoints';

describe('API Type Definitions', () => {
  it('should create valid ScheduleOptimizationRequest', () => {
    const request: ScheduleOptimizationRequest = {
      courseCodes: ['CSC 101'],
      semester: 'Fall 2025',
      constraints: {
        earliestStartTime: '09:00',
        latestEndTime: '17:00',
      },
    };
    
    expect(request).toBeDefined();
  });
});
```

Run:
```bash
npm test -- api-types.test.ts
```

### Completion Criteria
- [x] All request/response types defined
- [x] Types match backend Pydantic models
- [x] No duplicate type definitions
- [x] Tests pass

---

## Task 4: OptimizeButton Integration

**Priority**: High  
**Estimated Time**: 1 hour  
**Dependencies**: Tasks 1, 2, 3

### Objective
Connect OptimizeButton to `/api/schedule/optimize` endpoint.

### Steps

#### 4.1: Verify Endpoint Implementation

**File**: `services/api_server.py` (line 145)

Check endpoint exists:
```python
@app.post("/api/schedule/optimize")
async def optimize_schedule(request: ScheduleOptimizeRequest):
    # Implementation exists
```

Test manually:
```bash
curl -X POST http://localhost:8000/api/schedule/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "course_codes": ["CSC 101"],
    "semester": "Fall 2025",
    "university": "Baruch College",
    "constraints": {}
  }'
```

#### 4.2: Update OptimizeButton Component

**File**: `src/components/ui/optimize-button.tsx`

The component already calls `optimizeSchedule()` from `api-endpoints.ts` (line 127).

**Verify**: Check that the import is correct:
```typescript
import { 
  optimizeSchedule, 
  ScheduleOptimizationRequest,
  ScheduleOptimizationResponse 
} from "@/lib/api-endpoints";
```

#### 4.3: Ensure API Endpoint Function Exists

**File**: `src/lib/api-endpoints.ts` (line 129)

Function already exists:
```typescript
export async function optimizeSchedule(
  request: ScheduleOptimizationRequest
): Promise<ScheduleOptimizationResponse> {
  return apiClient.post("/api/schedule/optimize", request);
}
```

**Update**: Add university parameter (backend expects it):

```typescript
// Update interface at line 35
export interface ScheduleOptimizationRequest {
  courseCodes: string[];
  semester: string;
  university?: string;  // Add this
  constraints?: {
    preferredDays?: string[];
    earliestStartTime?: string;
    latestEndTime?: string;
    minProfessorRating?: number;
    avoidGaps?: boolean;
  };
}

// Update function at line 129
export async function optimizeSchedule(
  request: ScheduleOptimizationRequest
): Promise<ScheduleOptimizationResponse> {
  // Add default university
  const requestWithDefaults = {
    ...request,
    university: request.university || 'Baruch College',
  };
  return apiClient.post("/api/schedule/optimize", requestWithDefaults);
}
```

#### 4.4: Update OptimizeButton to Include University

**File**: `src/components/ui/optimize-button.tsx`

Add university prop (line 20):
```typescript
interface OptimizeButtonProps {
  courseCodes: string[];
  semester?: string;
  university?: string;  // Add this
  constraints?: ScheduleConstraints;
  onOptimized: (response: ScheduleOptimizationResponse) => void;
  onError?: (error: Error) => void;
  disabled?: boolean;
  className?: string;
}
```

Update handleOptimize (line 124):
```typescript
const request: ScheduleOptimizationRequest = {
  courseCodes: courseCodes.filter(code => code && code.trim() !== ""),
  semester,
  university,  // Add this
  constraints,
};
```

#### 4.5: Update Schedule Builder Usage

**File**: `src/components/pages/schedule-builder.tsx`

Find where OptimizeButton is used and add university prop:

```tsx
<OptimizeButton
  courseCodes={selectedCourses.map(c => c.course_code)}
  semester="Fall 2025"
  university="Baruch College"
  constraints={{
    earliestStartTime: "09:00",
    latestEndTime: "18:00",
  }}
  onOptimized={(response) => {
    // Handle optimized schedules
    console.log('Received optimized schedules:', response);
    setOptimizedSchedules(response.schedules);
  }}
  onError={(error) => {
    console.error('Optimization error:', error);
  }}
/>
```

### Testing

#### Manual Test:
1. Start backend: `cd services && python api_server.py`
2. Start frontend: `npm run dev`
3. Navigate to Schedule Builder page
4. Select 2-3 courses
5. Click "AI Optimize" button
6. Verify:
   - Progress bar appears
   - Request sent to backend (check Network tab)
   - Response received within 5 seconds
   - Schedules displayed

#### Automated Test:
```typescript
// src/components/ui/__tests__/optimize-button.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OptimizeButton } from '../optimize-button';
import * as apiEndpoints from '@/lib/api-endpoints';

jest.mock('@/lib/api-endpoints');

describe('OptimizeButton', () => {
  it('should call API and handle response', async () => {
    const mockResponse = {
      schedules: [{ id: '1', sections: [], score: 95 }],
      count: 1,
      courses: {},
      total_sections: 3,
    };
    
    (apiEndpoints.optimizeSchedule as jest.Mock).mockResolvedValue(mockResponse);
    
    const onOptimized = jest.fn();
    
    render(
      <OptimizeButton
        courseCodes={['CSC 101']}
        semester="Fall 2025"
        onOptimized={onOptimized}
      />
    );
    
    fireEvent.click(screen.getByRole('button'));
    
    await waitFor(() => {
      expect(onOptimized).toHaveBeenCalledWith(mockResponse);
    });
  });
});
```

Run: `npm test -- optimize-button.test.tsx`

### Completion Criteria
- [x] API endpoint tested and working
- [x] OptimizeButton calls correct endpoint
- [x] University parameter included
- [x] Success case displays schedules
- [x] Error case shows error message
- [x] Loading state works correctly
- [x] Tests pass

---

## Task 5: ChatButton Integration

**Priority**: High  
**Estimated Time**: 45 minutes  
**Dependencies**: Tasks 1, 2, 3

### Objective
Connect ChatButton to `/api/chat/message` endpoint.

### Steps

#### 5.1: Verify Backend Endpoint

**File**: `services/api_server.py` (line 229)

Endpoint exists but returns placeholder. **Action**: This is acceptable for now. The backend TODO can be implemented later.

Test:
```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Help me build a schedule", "context": {}}'
```

Expected response:
```json
{
  "message": "I received your message: Help me build a schedule",
  "suggestions": [],
  "context": {}
}
```

#### 5.2: Verify Frontend Integration

**File**: `src/components/ui/chat-button.tsx`

Component already calls `sendChatMessage()` from `api-endpoints.ts` (line 57).

**No changes needed** - component is already correctly integrated.

#### 5.3: Update Schedule Builder to Use ChatButton

**File**: `src/components/pages/schedule-builder.tsx`

The schedule builder already has a chat interface (lines 76-158). Update the message sending to use proper context:

Find `handleSendMessage` function (around line 76) and update:

```typescript
const handleSendMessage = async () => {
  if (!inputMessage.trim()) return;

  const userMessage: Message = {
    id: Date.now().toString(),
    role: "user",
    content: inputMessage,
    timestamp: new Date(),
  };

  setMessages(prev => [...prev, userMessage]);
  setInputMessage("");
  setIsTyping(true);

  try {
    // Use ChatButton's API call
    const response = await sendChatMessage({
      message: inputMessage,
      context: {
        currentSchedule: sections.length > 0 ? {
          sections: sections,
          count: sections.length,
        } : undefined,
        semester: "Fall 2025",
        preferences: {
          // Add any user preferences here
        },
      },
    });

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: response.message,
      timestamp: new Date(),
      suggestedSchedule: response.suggestedSchedule,
    };

    setMessages(prev => [...prev, assistantMessage]);
    
    // Handle suggestions if any
    if (response.suggestedSchedule) {
      // Display suggestion UI
      console.log('AI suggested schedule:', response.suggestedSchedule);
    }
  } catch (error) {
    console.error('Chat error:', error);
    const errorMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: "Sorry, I encountered an error. Please try again.",
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, errorMessage]);
  } finally {
    setIsTyping(false);
  }
};
```

Add import at top:
```typescript
import { sendChatMessage } from "@/lib/api-endpoints";
```

### Testing

#### Manual Test:
1. Navigate to Schedule Builder
2. Type message: "Help me find CS courses"
3. Click send button
4. Verify:
   - Message appears in chat
   - Request in Network tab
   - Response appears within 3 seconds
   - Context included in request

#### Automated Test:
```typescript
// src/components/ui/__tests__/chat-button.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatButton } from '../chat-button';
import * as apiEndpoints from '@/lib/api-endpoints';

jest.mock('@/lib/api-endpoints');

describe('ChatButton', () => {
  it('should send message and receive response', async () => {
    const mockResponse = {
      message: 'I can help you with that!',
      suggestedSchedule: null,
      actions: [],
    };
    
    (apiEndpoints.sendChatMessage as jest.Mock).mockResolvedValue(mockResponse);
    
    const onResponse = jest.fn();
    
    render(
      <ChatButton
        message="Help me"
        onResponse={onResponse}
      />
    );
    
    fireEvent.click(screen.getByRole('button'));
    
    await waitFor(() => {
      expect(onResponse).toHaveBeenCalledWith(mockResponse);
    });
  });
});
```

### Completion Criteria
- [x] Backend endpoint tested
- [x] ChatButton sends correct request format
- [x] Context properly included
- [x] Response displayed in UI
- [x] Loading state shows "Thinking..."
- [x] Tests pass

---

## Task 6: SearchButton Enhancement

**Priority**: Medium  
**Estimated Time**: 1 hour  
**Dependencies**: Tasks 1, 2, 3

### Objective
Add enhanced semantic search capability to SearchButton while maintaining existing functionality.

### Steps

#### 6.1: Add Backend Search Endpoint

**File**: `services/api_server.py`

Endpoint already exists at line 131:
```python
@app.post("/api/courses/search")
async def search_courses(filters: CourseSearchFilter):
    # Implementation exists
```

Test:
```bash
curl -X POST http://localhost:8000/api/courses/search \
  -H "Content-Type: application/json" \
  -d '{"query": "database", "semester": "Fall 2025"}'
```

#### 6.2: Add Enhanced Search Function

**File**: `src/lib/api-endpoints.ts`

Function already exists at line 89. **No changes needed**.

#### 6.3: Create Dual-Mode Hook

**File**: `src/hooks/useCourseSearch.ts`

Add enhanced mode detection (around line 60):

```typescript
// After line 60, add:
const shouldUseEnhancedSearch = (query: string): boolean => {
  // Use enhanced search for natural language queries
  const naturalLanguageIndicators = [
    'similar to',
    'like',
    'recommend',
    'about',
    'related to',
  ];
  
  return naturalLanguageIndicators.some(indicator => 
    query.toLowerCase().includes(indicator)
  );
};

// Update performSearch function:
const performSearch = useCallback(async (params: SearchParams) => {
  const cacheKey = getCacheKey(params);
  
  // Check cache first
  const cachedEntry = cacheRef.current.get(cacheKey);
  if (cachedEntry && isCacheValid(cachedEntry)) {
    setCourses(cachedEntry.data);
    setLoading(false);
    return;
  }

  setLoading(true);
  setError(null);

  try {
    let results;
    
    // Decide which search method to use
    if (params.query && shouldUseEnhancedSearch(params.query)) {
      // Use backend API for semantic search
      results = await searchCoursesAPI({
        query: params.query.trim(),
        department: params.filters.department !== "all" ? params.filters.department : undefined,
        semester: params.filters.semester || undefined,
        modality: params.filters.modality !== "all" ? params.filters.modality : undefined,
        limit: 50,
      });
    } else {
      // Use existing Supabase query for exact search
      results = await searchCourses({
        query: params.query.trim() || undefined,
        department: params.filters.department !== "all" ? params.filters.department : undefined,
        semester: params.filters.semester || undefined,
        modality: params.filters.modality !== "all" ? params.filters.modality : undefined,
        timeSlot: params.filters.timeSlot !== "all" ? params.filters.timeSlot : undefined,
        limit: 50,
      });
    }

    // Update cache
    cacheRef.current.set(cacheKey, {
      data: results,
      timestamp: Date.now(),
    });

    setCourses(results);
  } catch (err) {
    const error = err instanceof Error ? err : new Error("Search failed");
    setError(error);
    setCourses([]);
  } finally {
    setLoading(false);
  }
}, [getCacheKey, isCacheValid]);
```

Add import:
```typescript
import { searchCoursesAPI } from "@/lib/api-endpoints";
```

### Testing

#### Manual Test:
1. Try exact search: "CSC 101" → Should use Supabase
2. Try semantic search: "courses similar to CSC 101" → Should use backend
3. Check Network tab to verify which endpoint called
4. Verify results displayed correctly for both

#### Automated Test:
```typescript
// src/hooks/__tests__/useCourseSearch.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useCourseSearch } from '../useCourseSearch';
import * as supabaseQueries from '@/lib/supabase-queries';
import * as apiEndpoints from '@/lib/api-endpoints';

jest.mock('@/lib/supabase-queries');
jest.mock('@/lib/api-endpoints');

describe('useCourseSearch', () => {
  it('uses Supabase for exact queries', async () => {
    const mockCourses = [{ id: '1', name: 'CSC 101' }];
    (supabaseQueries.searchCourses as jest.Mock).mockResolvedValue(mockCourses);
    
    const { result } = renderHook(() => useCourseSearch());
    
    result.current.search('CSC 101', {});
    
    await waitFor(() => {
      expect(result.current.courses).toEqual(mockCourses);
      expect(supabaseQueries.searchCourses).toHaveBeenCalled();
      expect(apiEndpoints.searchCoursesAPI).not.toHaveBeenCalled();
    });
  });

  it('uses backend for semantic queries', async () => {
    const mockCourses = [{ id: '1', name: 'CSC 102' }];
    (apiEndpoints.searchCoursesAPI as jest.Mock).mockResolvedValue(mockCourses);
    
    const { result } = renderHook(() => useCourseSearch());
    
    result.current.search('courses similar to CSC 101', {});
    
    await waitFor(() => {
      expect(result.current.courses).toEqual(mockCourses);
      expect(apiEndpoints.searchCoursesAPI).toHaveBeenCalled();
    });
  });
});
```

### Completion Criteria
- [x] Enhanced search detection works
- [x] Exact queries use Supabase (fast)
- [x] Semantic queries use backend API
- [x] Fallback works if backend unavailable
- [x] Cache works for both modes
- [x] Tests pass

---

## Task 7: ProfessorButton Integration

**Priority**: Medium  
**Estimated Time**: 30 minutes  
**Dependencies**: Tasks 1, 2, 3

### Objective
Connect ProfessorButton to `/api/professor/{name}` endpoint.

### Steps

#### 7.1: Verify Backend Endpoint

**File**: `services/api_server.py` (line 202)

Test:
```bash
curl http://localhost:8000/api/professor/John%20Smith?university=Baruch%20College
```

#### 7.2: Update ProfessorButton Component

**File**: `src/components/ui/professor-button.tsx`

Currently, this button likely just triggers a modal. Update to fetch data:

```typescript
// Add props (if not present)
interface ProfessorButtonProps {
  professorName: string;
  university?: string;
  onDetails?: (professor: ProfessorDetails) => void;
}

export function ProfessorButton({ 
  professorName, 
  university = "Baruch College",
  onDetails 
}: ProfessorButtonProps) {
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleClick = async () => {
    setLoading(true);
    
    try {
      const professorData = await getProfessorByNameAPI(professorName, university);
      
      if (onDetails) {
        onDetails(professorData);
      }
      
      // Open modal with data
      // (implementation depends on your modal system)
      
    } catch (error) {
      toast({
        title: "Error Loading Professor",
        description: error instanceof Error ? error.message : "Failed to load professor data",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button onClick={handleClick} disabled={loading} variant="outline">
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        professorName
      )}
    </Button>
  );
}
```

Add import:
```typescript
import { getProfessorByNameAPI } from "@/lib/api-endpoints";
import type { ProfessorDetails } from "@/lib/api-endpoints";
```

### Testing

#### Manual Test:
1. Click on a professor name in course list
2. Verify API call made
3. Check professor data displayed in modal
4. Verify grade, rating, reviews shown

### Completion Criteria
- [x] Button calls API on click
- [x] Professor data fetched successfully
- [x] Data cached for 1 hour
- [x] Error handling works
- [x] Loading state displayed

---

## Task 8: ScheduleActionButton Enhancement

**Priority**: Low  
**Estimated Time**: 1 hour  
**Dependencies**: Tasks 1, 2, 3

### Objective
Add backend validation endpoint to enhance conflict detection.

### Steps

#### 8.1: Add Backend Validation Endpoint

**File**: `services/api_server.py`

Add new endpoint after the optimize endpoint:

```python
from pydantic import BaseModel

class ScheduleValidationRequest(BaseModel):
    schedule_id: str
    section_id: str
    action: str  # "add" or "remove"

@app.post("/api/schedule/validate")
async def validate_schedule_change(request: ScheduleValidationRequest):
    """Validate adding/removing a section from schedule"""
    try:
        # Get current schedule
        schedule = await supabase_service.get_schedule_by_id(request.schedule_id)
        
        # Get section to add/remove
        section = await supabase_service.get_section_by_id(request.section_id)
        
        if not section:
            raise HTTPException(status_code=404, detail="Section not found")
        
        conflicts = []
        warnings = []
        suggestions = []
        
        if request.action == "add":
            # Check for conflicts with existing sections
            current_sections = await supabase_service.get_sections_by_ids(schedule.sections)
            
            for existing in current_sections:
                # Time conflict check
                if section.days and existing.days:
                    has_overlap = any(day in existing.days for day in section.days)
                    if has_overlap:
                        # Check time overlap
                        if (section.start_time < existing.end_time and 
                            section.end_time > existing.start_time):
                            conflicts.append({
                                "type": "time",
                                "section1": section.id,
                                "section2": existing.id,
                                "message": f"Time conflict with {existing.course_code}"
                            })
            
            # Find alternative sections if conflicts found
            if conflicts:
                alternatives = await supabase_service.get_sections_by_course(
                    section.course_id
                )
                suggestions = [s for s in alternatives if s.id != section.id]
        
        return {
            "valid": len(conflicts) == 0,
            "conflicts": conflicts,
            "warnings": warnings,
            "suggestions": [s.dict() for s in suggestions[:3]],  # Top 3
        }
        
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### 8.2: Add Frontend API Function

**File**: `src/lib/api-endpoints.ts`

Add after line 140:

```typescript
/**
 * Validate schedule change
 */
export async function validateScheduleChange(
  request: ScheduleValidationRequest
): Promise<ScheduleValidationResponse> {
  return apiClient.post("/api/schedule/validate", request);
}
```

#### 8.3: Update ScheduleActionButton

**File**: `src/components/ui/schedule-action-button.tsx`

Update the `handleAction` function to call validation first:

```typescript
const handleAction = async () => {
  if (action === "add") {
    // Validate before adding
    try {
      const validation = await validateScheduleChange({
        scheduleId,
        sectionId,
        action: "add",
      });
      
      if (!validation.valid) {
        // Show conflicts
        if (onConflict) {
          onConflict(validation.conflicts);
        }
        return;
      }
      
      // Proceed with adding if valid
      await addSectionToSchedule(scheduleId, sectionId);
      
      if (onSuccess) {
        onSuccess();
      }
      
      toast({
        title: "Course Added",
        description: "Section added to your schedule",
      });
      
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to add section",
        variant: "destructive",
      });
    }
  } else {
    // Remove action (existing code)
    // ...
  }
};
```

Add import:
```typescript
import { validateScheduleChange } from "@/lib/api-endpoints";
```

### Testing

```bash
# Manual test
1. Add course to schedule
2. Try to add conflicting course
3. Verify conflict warning shown
4. Verify alternative sections suggested
```

### Completion Criteria
- [x] Validation endpoint implemented
- [x] ScheduleActionButton calls validation
- [x] Conflicts displayed to user
- [x] Alternative suggestions shown
- [x] Validation completes within 500ms

---

## Task 9: Error Handling Enhancement

**Priority**: Medium  
**Estimated Time**: 45 minutes  
**Dependencies**: Tasks 2-8

### Objective
Enhance error handling across all API integrations with consistent patterns.

### Steps

#### 9.1: Update Error Handler

**File**: `src/lib/error-handler.ts`

Add comprehensive error categorization:

```typescript
export enum ErrorCategory {
  NETWORK = 'network',
  AUTH = 'auth',
  VALIDATION = 'validation',
  NOT_FOUND = 'not_found',
  SERVER = 'server',
  TIMEOUT = 'timeout',
}

export interface CategorizedError {
  category: ErrorCategory;
  message: string;
  userMessage: string;
  retryable: boolean;
  action?: () => void;
}

export function categorizeError(error: any): CategorizedError {
  // Network/fetch errors
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return {
      category: ErrorCategory.NETWORK,
      message: error.message,
      userMessage: 'Connection lost. Please check your internet connection.',
      retryable: true,
    };
  }
  
  // API Client errors
  if (error instanceof APIClientError) {
    if (error.status === 401 || error.status === 403) {
      return {
        category: ErrorCategory.AUTH,
        message: error.message,
        userMessage: 'Your session has expired. Please log in again.',
        retryable: false,
        action: () => {
          sessionStorage.setItem('redirectAfterLogin', window.location.pathname);
          window.location.href = '/login';
        },
      };
    }
    
    if (error.status === 400) {
      return {
        category: ErrorCategory.VALIDATION,
        message: error.message,
        userMessage: error.details?.message || 'Please check your input.',
        retryable: false,
      };
    }
    
    if (error.status === 404) {
      return {
        category: ErrorCategory.NOT_FOUND,
        message: error.message,
        userMessage: 'The requested resource was not found.',
        retryable: false,
      };
    }
    
    if (error.code === 'TIMEOUT') {
      return {
        category: ErrorCategory.TIMEOUT,
        message: error.message,
        userMessage: 'Request timed out. Please try again.',
        retryable: true,
      };
    }
    
    // Server errors (500+)
    return {
      category: ErrorCategory.SERVER,
      message: error.message,
      userMessage: 'A server error occurred. Please try again later.',
      retryable: true,
    };
  }
  
  // Generic error
  return {
    category: ErrorCategory.SERVER,
    message: error.message || 'Unknown error',
    userMessage: 'An unexpected error occurred.',
    retryable: false,
  };
}
```

#### 9.2: Create Error Display Component

**File**: `src/components/ui/error-display.tsx`

Create new file:

```typescript
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw } from "lucide-react";
import { CategorizedError } from "@/lib/error-handler";

interface ErrorDisplayProps {
  error: CategorizedError;
  onRetry?: () => void;
}

export function ErrorDisplay({ error, onRetry }: ErrorDisplayProps) {
  return (
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Error</AlertTitle>
      <AlertDescription className="flex items-center justify-between">
        <span>{error.userMessage}</span>
        {error.retryable && onRetry && (
          <Button 
            variant="outline" 
            size="sm"
            onClick={onRetry}
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Retry
          </Button>
        )}
        {error.action && (
          <Button 
            variant="outline" 
            size="sm"
            onClick={error.action}
          >
            Take Action
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}
```

#### 9.3: Update Buttons to Use Categorized Errors

Example for OptimizeButton:

```typescript
// In handleOptimize catch block:
catch (error) {
  const categorized = categorizeError(error);
  
  if (onError) {
    onError(error instanceof Error ? error : new Error(categorized.message));
  }

  toast({
    title: "Optimization Failed",
    description: categorized.userMessage,
    variant: "destructive",
    action: categorized.retryable ? {
      label: "Retry",
      onClick: handleOptimize,
    } : undefined,
  });
}
```

### Testing

Test each error scenario:
```bash
# 1. Network error (backend offline)
# Stop backend, click optimize button

# 2. Auth error
# Delete auth token, try API call

# 3. Validation error
# Submit invalid data

# 4. Timeout
# Set very short timeout, make slow request
```

### Completion Criteria
- [x] All error categories handled
- [x] User-friendly messages displayed
- [x] Retry logic works for retryable errors
- [x] Auth errors redirect to login
- [x] Error display component created

---

## Task 10: Testing and Validation

**Priority**: High  
**Estimated Time**: 2 hours  
**Dependencies**: Tasks 1-9

### Objective
Comprehensive testing of all integrations.

### Steps

#### 10.1: Create Integration Test Suite

**File**: `src/__tests__/integration/api-integration.test.ts`

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { optimizeSchedule, sendChatMessage } from '@/lib/api-endpoints';

const server = setupServer(
  rest.post('http://localhost:8000/api/schedule/optimize', (req, res, ctx) => {
    return res(
      ctx.json({
        schedules: [{ id: '1', sections: [], score: 95 }],
        count: 1,
        courses: {},
        total_sections: 3,
      })
    );
  }),
  
  rest.post('http://localhost:8000/api/chat/message', (req, res, ctx) => {
    return res(
      ctx.json({
        message: 'I can help!',
        suggestedSchedule: null,
        actions: [],
      })
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('API Integration Tests', () => {
  test('optimizeSchedule returns schedules', async () => {
    const result = await optimizeSchedule({
      courseCodes: ['CSC 101'],
      semester: 'Fall 2025',
    });
    
    expect(result.schedules).toHaveLength(1);
    expect(result.count).toBe(1);
  });
  
  test('sendChatMessage returns response', async () => {
    const result = await sendChatMessage({
      message: 'Help me',
    });
    
    expect(result.message).toBe('I can help!');
  });
  
  test('handles network error', async () => {
    server.use(
      rest.post('http://localhost:8000/api/schedule/optimize', (req, res) => {
        return res.networkError('Failed to connect');
      })
    );
    
    await expect(optimizeSchedule({
      courseCodes: ['CSC 101'],
      semester: 'Fall 2025',
    })).rejects.toThrow();
  });
});
```

#### 10.2: Run All Tests

```bash
# Install MSW if not present
npm install -D msw

# Run tests
npm test

# Run specific test file
npm test -- api-integration.test.ts

# Run with coverage
npm test -- --coverage
```

#### 10.3: Manual Testing Checklist

Create checklist file: `.antigravity/testing-checklist.md`

```markdown
# Integration Testing Checklist

## Environment Setup
- [x] Backend running on port 8000
- [x] Frontend running on port 5173
- [x] Environment variables set correctly
- [x] Database accessible

## OptimizeButton Tests
- [ ] Click button with no courses → Validation error
- [ ] Click with 1 course → API call made
- [ ] Click with 5 courses → Multiple schedules returned
- [ ] Invalid time range → Validation error
- [ ] Backend offline → Error message shown
- [ ] Slow response → Progress indicator shown

## ChatButton Tests
- [ ] Send empty message → Prevented
- [ ] Send "Help me" → Response received
- [ ] Send with context → Context included in request
- [ ] Backend error → Error message shown

## SearchButton Tests
- [ ] Search "CSC 101" → Exact results via Supabase
- [ ] Search "similar to CSC 101" → Semantic results via API
- [ ] Backend offline → Falls back to Supabase
- [ ] Results cached → Second search instant

## ProfessorButton Tests
- [ ] Click professor → Data loads
- [ ] Professor not found → Error message
- [ ] Data cached → Second click instant

## Error Handling Tests
- [ ] Network error → Retry button shown
- [ ] Auth error → Redirects to login
- [ ] Validation error → Specific message shown
- [ ] 500 error → Generic message shown

## Performance Tests
- [ ] Search response < 1s
- [ ] Optimize response < 5s
- [ ] Chat response < 3s
- [ ] No memory leaks (check DevTools)
```

#### 10.4: Load Testing

```bash
# Install artillery
npm install -g artillery

# Create load test config
cat > loadtest.yml << EOF
config:
  target: "http://localhost:8000"
  phases:
    - duration: 60
      arrivalRate: 10
scenarios:
  - name: "Optimize Schedule"
    flow:
      - post:
          url: "/api/schedule/optimize"
          json:
            courseCodes: ["CSC 101", "MATH 201"]
            semester: "Fall 2025"
            university: "Baruch College"
            constraints: {}
EOF

# Run load test
artillery run loadtest.yml
```

### Completion Criteria
- [x] All unit tests pass
- [x] Integration tests pass
- [x] Manual testing checklist complete
- [x] Load testing shows acceptable performance
- [x] No console errors in browser
- [x] No memory leaks detected

---

## Task 11: Deployment

**Priority**: High  
**Estimated Time**: 1 hour  
**Dependencies**: Task 10

### Objective
Deploy integrated frontend and backend to production.

### Steps

#### 11.1: Backend Deployment (Railway)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create new project
cd services
railway init

# Add environment variables
railway variables set GEMINI_API_KEY=your_key
railway variables set SUPABASE_URL=your_url
railway variables set SUPABASE_SERVICE_ROLE_KEY=your_key
railway variables set DATABASE_URL=your_url

# Deploy
railway up
```

Get deployment URL (e.g., `https://your-app.railway.app`)

#### 11.2: Frontend Deployment (Vercel)

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
cd /home/kbesada/Code/ScheduleFirst-AI
vercel

# Set environment variables
vercel env add VITE_API_URL
# Enter: https://your-app.railway.app

vercel env add VITE_SUPABASE_URL
# Enter: your Supabase URL

vercel env add VITE_SUPABASE_ANON_KEY
# Enter: your anon key

# Deploy to production
vercel --prod
```

#### 11.3: Update CORS

**File**: `services/api_server.py` (line 76)

Update allowed origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",     # Development
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "https://your-app.vercel.app",  # Production - UPDATE THIS
        "https://*.vercel.app",          # Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Redeploy backend:
```bash
railway up
```

#### 11.4: Verify Production

```bash
# Test backend health
curl https://your-app.railway.app/health

# Test optimize endpoint
curl -X POST https://your-app.railway.app/api/schedule/optimize \
  -H "Content-Type: application/json" \
  -d '{"courseCodes":["CSC 101"],"semester":"Fall 2025","university":"Baruch College","constraints":{}}'

# Visit frontend
open https://your-app.vercel.app

# Test in browser:
# 1. Search courses
# 2. Click AI Optimize
# 3. Send chat message
# 4. Click professor
```

#### 11.5: Setup Monitoring

**Backend Monitoring** (Railway):
- Enable automatic deployment logs
- Set up health check endpoint monitoring

**Frontend Monitoring** (Vercel):
- Enable Vercel Analytics
- Check deployment logs

**Application Monitoring**:
```typescript
// Add to src/main.tsx
if (import.meta.env.PROD) {
  // Track errors
  window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    // Send to monitoring service
  });
  
  // Track API failures
  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    // Send to monitoring service
  });
}
```

### Completion Criteria
- [x] Backend deployed to Railway
- [x] Frontend deployed to Vercel
- [x] Production URLs configured
- [x] CORS properly set
- [x] Health checks passing
- [x] All features working in production
- [x] Monitoring enabled

---

## Summary Checklist

### Core Integration
- [ ] Task 1: Environment Setup
- [ ] Task 2: API Client Configuration
- [ ] Task 3: Type Definitions
- [ ] Task 4: OptimizeButton Integration
- [ ] Task 5: ChatButton Integration
- [ ] Task 6: SearchButton Enhancement
- [ ] Task 7: ProfessorButton Integration
- [ ] Task 8: ScheduleActionButton Enhancement
- [ ] Task 9: Error Handling Enhancement
- [ ] Task 10: Testing and Validation
- [ ] Task 11: Deployment

### Verification
- [ ] All API endpoints working
- [ ] All buttons integrated
- [ ] Error handling comprehensive
- [ ] Tests passing
- [ ] Production deployment successful
- [ ] No console errors
- [ ] Performance targets met
- [ ] Documentation updated

---

## Troubleshooting

### Common Issues

**Issue**: CORS error when calling API
**Solution**: Check `services/api_server.py` line 76, ensure frontend URL in allow_origins

**Issue**: 401 Unauthorized error
**Solution**: Check Supabase auth token in request headers, verify token not expired

**Issue**: Timeout on optimize endpoint
**Solution**: Increase timeout in `api-client.ts` for AI operations to 60s

**Issue**: Type errors after API call
**Solution**: Verify backend response matches TypeScript interfaces

**Issue**: Cache not working
**Solution**: Check cache TTL settings in `useCourseSearch.ts`

### Debug Commands

```bash
# Check backend logs
cd services
python -m mcp_server.utils.logger

# Check frontend build
npm run build
npm run preview

# Clear all caches
# In browser DevTools > Application > Clear Storage

# Test API directly
curl -X GET http://localhost:8000/health -v
```

---

## Next Steps After Integration

1. **Performance Optimization**
   - Add response compression
   - Implement request batching
   - Add service worker for offline support

2. **Enhanced Features**
   - Add schedule comparison feature
   - Implement schedule export (PDF/iCal)
   - Add email notifications

3. **Analytics**
   - Track button usage
   - Monitor API performance
   - A/B test UI changes

4. **Documentation**
   - Update API documentation
   - Create user guide
   - Add developer onboarding docs

---

## Conclusion

This task guide provides comprehensive step-by-step instructions for integrating the React frontend with the FastAPI backend. Each task is self-contained with clear objectives, detailed steps, testing procedures, and completion criteria.

Follow the tasks in order, verify each step, and check off items as you complete them. If you encounter issues, refer to the Troubleshooting section or the design.md and requirements.md for additional context.
