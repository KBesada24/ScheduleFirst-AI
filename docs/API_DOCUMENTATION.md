# API Documentation

This document provides comprehensive documentation for all API endpoints, hooks, and utilities in the button routing and integration system.

## Table of Contents

1. [Button Components](#button-components)
2. [Custom Hooks](#custom-hooks)
3. [Utility Functions](#utility-functions)
4. [API Endpoints](#api-endpoints)
5. [Type Definitions](#type-definitions)

## Button Components

### NavigationButton

A reusable button component that handles navigation with authentication checks.

**Location**: `src/components/ui/navigation-button.tsx`

**Props**:
```typescript
interface NavigationButtonProps {
  to: string;                    // Target route or URL
  children: React.ReactNode;     // Button content
  requiresAuth?: boolean;        // Whether route requires authentication
  onClick?: () => void | Promise<void>; // Optional pre-navigation callback
  external?: boolean;            // Whether link is external
  disabled?: boolean;            // Whether button is disabled
  variant?: ButtonVariant;       // Visual variant
  size?: ButtonSize;             // Button size
}
```

**Usage**:
```typescript
<NavigationButton to="/dashboard" requiresAuth>
  Go to Dashboard
</NavigationButton>

<NavigationButton to="https://example.com" external>
  External Link
</NavigationButton>
```

**Features**:
- Automatic authentication checking
- Loading states during navigation
- Return URL preservation for protected routes
- Support for external links
- Integration with React Router

### AuthButton

A button component for authentication actions (login, signup, logout).

**Location**: `src/components/ui/auth-button.tsx`

**Props**:
```typescript
interface AuthButtonProps {
  action: "login" | "signup" | "logout";
  onSuccess?: () => void;
  onError?: (error: Error) => void;
  disabled?: boolean;
  children?: React.ReactNode;
  className?: string;
  variant?: ButtonVariant;
}
```

**Usage**:
```typescript
<AuthButton 
  action="login" 
  onSuccess={() => navigate('/dashboard')}
>
  Sign In
</AuthButton>

<AuthButton action="logout">
  Log Out
</AuthButton>
```

**Features**:
- Handles login, signup, and logout
- Loading states during authentication
- Success/error notifications
- Integration with useAuth hook

### SearchButton

A button component for triggering course searches with validation.

**Location**: `src/components/ui/search-button.tsx`

**Props**:
```typescript
interface SearchButtonProps {
  query: string;
  filters: CourseFilters;
  onResults: (courses: CourseWithSections[]) => void;
  onError: (error: Error) => void;
  disabled?: boolean;
  className?: string;
  onClick?: () => void;
}

interface CourseFilters {
  department?: string;
  semester?: string;
  modality?: string;
  timeSlot?: string;
}
```

**Usage**:
```typescript
<SearchButton
  query="Computer Science"
  filters={{ department: "csc", modality: "Online" }}
  onResults={(courses) => setCourses(courses)}
  onError={(error) => console.error(error)}
/>
```

**Features**:
- Input validation before search
- Loading states
- Error handling
- Integration with Supabase queries

### ScheduleActionButton

A button component for adding/removing courses from schedule.

**Location**: `src/components/ui/schedule-action-button.tsx`

**Props**:
```typescript
interface ScheduleActionButtonProps {
  action: "add" | "remove";
  sectionId: string;
  scheduleId: string;
  onSuccess?: () => void;
  onConflict?: (conflicts: TimeConflict[]) => void;
  disabled?: boolean;
}
```

**Usage**:
```typescript
<ScheduleActionButton
  action="add"
  sectionId="section-123"
  scheduleId="schedule-456"
  onSuccess={() => toast({ title: "Course added!" })}
  onConflict={(conflicts) => showConflictDialog(conflicts)}
/>
```

**Features**:
- Conflict detection before adding
- Optimistic UI updates
- Rollback on error
- Success/error notifications

### OptimizeButton

A button component for triggering AI schedule optimization.

**Location**: `src/components/ui/optimize-button.tsx`

**Props**:
```typescript
interface OptimizeButtonProps {
  courseCodes: string[];
  semester?: string;
  constraints?: ScheduleConstraints;
  onOptimized: (response: ScheduleOptimizationResponse) => void;
  onError?: (error: Error) => void;
  disabled?: boolean;
  className?: string;
}

interface ScheduleConstraints {
  preferredDays?: string[];
  earliestStartTime?: string;
  latestEndTime?: string;
  minProfessorRating?: number;
  avoidGaps?: boolean;
}
```

**Usage**:
```typescript
<OptimizeButton
  courseCodes={["CSC 101", "MATH 201"]}
  constraints={{
    earliestStartTime: "09:00",
    latestEndTime: "17:00",
    minProfessorRating: 4.0
  }}
  onOptimized={(response) => setSchedules(response.schedules)}
/>
```

**Features**:
- Input validation (course codes, constraints)
- Progress indicator
- Constraint validation
- Error handling

### ChatButton

A button component for sending messages to AI assistant.

**Location**: `src/components/ui/chat-button.tsx`

**Props**:
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
```

**Usage**:
```typescript
<ChatButton
  message="Help me build a schedule"
  context={{ semester: "Fall 2025" }}
  onResponse={(response) => handleAIResponse(response)}
/>
```

**Features**:
- Message validation
- "Thinking" animation
- Schedule suggestion parsing
- Error handling

## Custom Hooks

### useFormSubmission

A hook for handling form submission with validation and error handling.

**Location**: `src/hooks/useFormSubmission.ts`

**Signature**:
```typescript
function useFormSubmission<T extends Record<string, any>>(
  initialValues: T,
  options: FormSubmissionOptions<T>
): FormSubmissionState<T>

interface FormSubmissionOptions<T> {
  onSubmit: (values: T) => Promise<void>;
  onSuccess?: (values: T) => void;
  onError?: (error: Error) => void;
  validationRules?: Partial<Record<keyof T, (value: any) => ValidationResult>>;
  resetOnSuccess?: boolean;
}

interface FormSubmissionState<T> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  isSubmitting: boolean;
  isValid: boolean;
  submitCount: number;
  setValue: (field: keyof T, value: any) => void;
  setFieldValues: (newValues: Partial<T>) => void;
  setFieldError: (field: keyof T, error: string) => void;
  clearErrors: () => void;
  reset: () => void;
  validate: () => boolean;
  handleSubmit: (e?: React.FormEvent) => Promise<void>;
}
```

**Usage**:
```typescript
const {
  values,
  errors,
  isSubmitting,
  setValue,
  handleSubmit,
} = useFormSubmission(
  { email: "", password: "" },
  {
    validationRules: {
      email: combine(required, email),
      password: combine(required, minLength(8)),
    },
    onSubmit: async (formValues) => {
      await signIn(formValues.email, formValues.password);
    },
    onSuccess: () => navigate('/dashboard'),
  }
);
```

**Features**:
- Automatic validation before submission
- Field-level error management
- Loading state management
- Success/error callbacks
- Form reset functionality

### useCourseSearch

A hook for managing course search with debouncing and caching.

**Location**: `src/hooks/useCourseSearch.ts`

**Signature**:
```typescript
function useCourseSearch(): {
  courses: CourseWithSections[];
  loading: boolean;
  error: Error | null;
  search: (query: string, filters: CourseFilters) => void;
  clear: () => void;
  clearCache: () => void;
}
```

**Usage**:
```typescript
const { courses, loading, error, search } = useCourseSearch();

// Trigger search (automatically debounced)
search("Computer Science", { department: "csc" });
```

**Features**:
- Automatic debouncing (300ms)
- Result caching (5 minutes)
- Loading and error states
- Cache management

### useSchedulePreview

A hook for managing schedule preview state.

**Location**: `src/hooks/useSchedulePreview.ts`

**Signature**:
```typescript
function useSchedulePreview(): {
  currentSchedule: OptimizedSchedule | null;
  schedules: OptimizedSchedule[];
  setSchedules: (schedules: OptimizedSchedule[]) => void;
  selectSchedule: (index: number) => void;
  clearPreview: () => void;
}
```

**Usage**:
```typescript
const { currentSchedule, schedules, selectSchedule } = useSchedulePreview();

// Set schedules from optimization
setSchedules(optimizationResponse.schedules);

// Switch between schedules
selectSchedule(1);
```

**Features**:
- Multiple schedule management
- Quick preview switching
- State persistence

## Utility Functions

### Form Validation

**Location**: `src/lib/form-validation.ts`

#### Basic Validators

```typescript
// Check if value is not empty
function required(value: any): ValidationResult

// Validate email format
function email(value: string): ValidationResult

// Check minimum length
function minLength(min: number): (value: string) => ValidationResult

// Check maximum length
function maxLength(max: number): (value: string) => ValidationResult

// Validate number range
function range(min: number, max: number): (value: number) => ValidationResult

// Match regex pattern
function pattern(regex: RegExp, message?: string): (value: string) => ValidationResult

// Match another field value
function matches(otherValue: any, fieldName?: string): (value: any) => ValidationResult
```

#### Specific Validators

```typescript
// Validate password strength (min 8 chars, uppercase, lowercase, number)
function password(value: string): ValidationResult

// Validate phone number
function phone(value: string): ValidationResult

// Validate URL
function url(value: string): ValidationResult

// Validate date
function date(value: string): ValidationResult

// Validate number
function number(value: any): ValidationResult

// Validate integer
function integer(value: any): ValidationResult
```

#### Async Validators

```typescript
// Check if email is available
async function emailAvailable(
  value: string,
  checkFunction: (email: string) => Promise<boolean>
): Promise<ValidationResult>

// Check if username is available
async function usernameAvailable(
  value: string,
  checkFunction: (username: string) => Promise<boolean>
): Promise<ValidationResult>
```

#### Helper Functions

```typescript
// Combine multiple validators
function combine(...validators: Validator[]): Validator

// Validate entire form
function validateForm<T>(
  values: T,
  rules: Partial<Record<keyof T, Validator>>
): { isValid: boolean; errors: Partial<Record<keyof T, string>> }

// Validate single field
function validateField(value: any, validators: Validator[]): ValidationResult

// Create custom validator
function custom(validate: (value: any) => boolean, message: string): Validator
```

### Performance Utilities

**Location**: `src/lib/performance-utils.ts`

#### Debouncing

```typescript
// Debounce a function
function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void

// Hook for debounced value
function useDebounce<T>(value: T, delay: number): T

// Hook for debounced callback
function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void
```

#### Throttling

```typescript
// Throttle a function
function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void

// Hook for throttled callback
function useThrottledCallback<T extends (...args: any[]) => any>(
  callback: T,
  limit: number
): (...args: Parameters<T>) => void
```

#### Memoization

```typescript
// Deep comparison memoization
function useDeepMemo<T>(factory: () => T, deps: any[]): T

// Deep equality check
function deepEqual(a: any, b: any): boolean
```

#### Lazy Loading

```typescript
// Intersection observer for lazy loading
function useIntersectionObserver(
  ref: React.RefObject<Element>,
  options?: IntersectionObserverInit
): boolean
```

#### Performance Monitoring

```typescript
// Measure component render time
function measureRenderTime(componentName: string): () => void

// Hook for measuring render time
function useRenderTime(componentName: string): void
```

## API Endpoints

### Course Search

**Endpoint**: `searchCourses(params: SearchParams): Promise<CourseWithSections[]>`

**Location**: `src/lib/supabase-queries.ts`

**Parameters**:
```typescript
interface SearchParams {
  query?: string;
  department?: string;
  semester?: string;
  modality?: string;
  timeSlot?: string;
  limit?: number;
}
```

**Returns**: Array of courses with sections

### Schedule Management

**Add Section**: `addSectionToSchedule(scheduleId: string, sectionId: string): Promise<void>`

**Remove Section**: `removeSectionFromSchedule(scheduleId: string, sectionId: string): Promise<void>`

**Check Conflicts**: `checkScheduleConflicts(scheduleId: string, sectionId: string): Promise<TimeConflict[]>`

**Update Schedule**: `updateSchedule(scheduleId: string, data: Partial<Schedule>): Promise<void>`

### Professor Data

**Get Professor**: `getProfessorById(id: string): Promise<ProfessorWithReviews>`

**Get Professor by Name**: `getProfessorByName(name: string): Promise<ProfessorWithReviews>`

### Backend API

**Chat**: `POST /api/chat/message`
```typescript
Request: {
  message: string;
  context?: ChatContext;
}

Response: {
  message: string;
  suggestedSchedule?: OptimizedSchedule;
  actions?: AIAction[];
}
```

**Optimize Schedule**: `POST /api/schedule/optimize`
```typescript
Request: {
  courseCodes: string[];
  semester: string;
  constraints?: ScheduleConstraints;
}

Response: {
  schedules: OptimizedSchedule[];
  count: number;
  courses: Record<string, CourseInfo>;
  total_sections: number;
}
```

## Type Definitions

### Core Types

```typescript
interface CourseSection {
  id: string;
  course_id: string;
  section_number: string;
  professor_name: string | null;
  days: string;
  start_time: string;
  end_time: string;
  location: string | null;
  modality: string | null;
  enrolled: number | null;
  capacity: number | null;
}

interface OptimizedSchedule {
  id: string;
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

interface TimeConflict {
  section1: CourseSection;
  section2: CourseSection;
  type: "time" | "location";
  message: string;
}

interface ValidationResult {
  isValid: boolean;
  error?: string;
}
```

## Error Handling

All API calls and button actions implement comprehensive error handling:

1. **Network Errors**: Retry up to 3 times with exponential backoff
2. **Authentication Errors**: Redirect to login with preserved destination
3. **Validation Errors**: Display inline with field highlighting
4. **API Errors**: Show user-friendly toast notifications

## Best Practices

### Using Button Components

1. Always provide descriptive children or aria-labels
2. Handle loading states appropriately
3. Implement error callbacks for user feedback
4. Use appropriate variants for visual hierarchy

### Using Hooks

1. Memoize expensive calculations
2. Debounce user input handlers
3. Cache API responses when appropriate
4. Clean up subscriptions and timers

### Form Validation

1. Combine validators for complex rules
2. Provide clear error messages
3. Validate on blur for better UX
4. Clear errors when user starts typing

## Conclusion

This API documentation provides a comprehensive reference for all components, hooks, and utilities in the button routing and integration system. For implementation examples, refer to the component files and integration tests.
