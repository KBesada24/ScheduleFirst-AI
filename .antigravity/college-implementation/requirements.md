# College Selection Feature - Requirements Document

## Functional Requirements

### FR-1: User Onboarding

**Priority: CRITICAL**

- **FR-1.1**: Upon first login, if user has no university set, display an onboarding modal
- **FR-1.2**: Modal must contain a dropdown with all CUNY schools
- **FR-1.3**: Modal cannot be dismissed without selecting a university
- **FR-1.4**: After selection, save university to database immediately
- **FR-1.5**: On successful save, close modal and proceed to dashboard/schedule builder
- **FR-1.6**: Show loading state during save operation
- **FR-1.7**: Display error message if save fails, allow retry

### FR-2: Database Persistence

**Priority: CRITICAL**

- **FR-2.1**: Create `user_profiles` table in Supabase
- **FR-2.2**: Table must include: `id`, `university`, `created_at`, `updated_at`
- **FR-2.3**: `id` field references `auth.users` table (foreign key)
- **FR-2.4**: `university` field is required (NOT NULL after first set)
- **FR-2.5**: Automatic timestamp updates on record modification
- **FR-2.6**: Profile created automatically when user registers
- **FR-2.7**: Migration script for existing users (set to null initially)

### FR-3: Auth Context Integration

**Priority: CRITICAL**

- **FR-3.1**: Extend auth context to include user profile data
- **FR-3.2**: Load user profile on login/session restoration
- **FR-3.3**: Provide `updateUniversity()` function in context
- **FR-3.4**: Automatically refresh profile after university update
- **FR-3.5**: University value accessible throughout the app via context
- **FR-3.6**: Context handles loading and error states

### FR-4: Settings/Profile Management

**Priority: HIGH**

- **FR-4.1**: Create a Settings page accessible from navigation
- **FR-4.2**: Display current university in read-only mode
- **FR-4.3**: Provide "Change University" button
- **FR-4.4**: Clicking button shows dropdown with all schools
- **FR-4.5**: Show confirmation dialog before saving changes
- **FR-4.6**: Update database and context on confirmation
- **FR-4.7**: Show success toast notification after change
- **FR-4.8**: Show error message if update fails

### FR-5: Application-Wide Integration

**Priority: CRITICAL**

- **FR-5.1**: Schedule Builder uses university from context (not local state)
- **FR-5.2**: AI Chat receives university in context automatically
- **FR-5.3**: Course Search uses university from context
- **FR-5.4**: Schedule Optimization uses university from context
- **FR-5.5**: Professor Lookup uses university from context
- **FR-5.6**: All API calls include correct university parameter

### FR-6: Validation & Error Handling

**Priority: HIGH**

- **FR-6.1**: Only allow selection from predefined CUNY schools list
- **FR-6.2**: Frontend validates university before saving
- **FR-6.3**: Backend validates university against allowed list
- **FR-6.4**: Return 400 error for invalid universities
- **FR-6.5**: Handle network errors gracefully
- **FR-6.6**: Provide clear error messages to users
- **FR-6.7**: Allow user to retry failed operations

## Non-Functional Requirements

### NFR-1: Performance

**Priority: HIGH**

- **NFR-1.1**: Onboarding modal appears within 500ms of login
- **NFR-1.2**: University save operation completes within 2 seconds
- **NFR-1.3**: Profile data cached in memory after initial load
- **NFR-1.4**: No unnecessary database queries

### NFR-2: Security

**Priority: CRITICAL**

- **NFR-2.1**: Row-Level Security (RLS) enabled on `user_profiles` table
- **NFR-2.2**: Users can only read their own profile
- **NFR-2.3**: Users can only update their own profile
- **NFR-2.4**: No user can access another user's university data
- **NFR-2.5**: All database operations use authenticated requests
- **NFR-2.6**: Audit trail for university changes (via timestamps)

### NFR-3: Usability

**Priority: HIGH**

- **NFR-3.1**: Onboarding modal is clear and welcoming
- **NFR-3.2**: University selection takes no more than 30 seconds
- **NFR-3.3**: Changing university in settings is intuitive
- **NFR-3.4**: All error messages are user-friendly and actionable
- **NFR-3.5**: Loading states clearly indicate progress
- **NFR-3.6**: Success feedback confirms actions completed

### NFR-4: Reliability

**Priority: HIGH**

- **NFR-4.1**: University data persists across sessions
- **NFR-4.2**: University data persists across devices
- **NFR-4.3**: System degrades gracefully if database unavailable
- **NFR-4.4**: Local storage fallback for critical scenarios
- **NFR-4.5**: 99% success rate for university save operations

### NFR-5: Maintainability

**Priority: MEDIUM**

- **NFR-5.1**: Code follows existing project patterns
- **NFR-5.2**: TypeScript types for all university-related data
- **NFR-5.3**: Reusable components (UniversityDropdown)
- **NFR-5.4**: CUNY schools list in single constant file
- **NFR-5.5**: Comprehensive inline documentation
- **NFR-5.6**: No hardcoded university names in components

### NFR-6: Scalability

**Priority: MEDIUM**

- **NFR-6.1**: Design supports adding more schools in future
- **NFR-6.2**: Database schema supports additional profile fields
- **NFR-6.3**: No performance degradation with increased users
- **NFR-6.4**: Efficient database queries with proper indexing

## Data Requirements

### DR-1: CUNY Schools List

**Complete list of supported universities:**

1. Baruch College
2. Brooklyn College
3. City College (City College of New York)
4. Hunter College
5. Queens College
6. College of Staten Island
7. John Jay College of Criminal Justice
8. Lehman College
9. Medgar Evers College
10. New York City College of Technology
11. York College

**Format:** Consistent naming, title case, no abbreviations

### DR-2: Database Schema

**Table: `user_profiles`**

| Column     | Type      | Constraints        | Description           |
| ---------- | --------- | ------------------ | --------------------- |
| id         | uuid      | PK, FK(auth.users) | User identifier       |
| university | text      | NOT NULL           | Selected CUNY school  |
| created_at | timestamp | DEFAULT now()      | Profile creation time |
| updated_at | timestamp | DEFAULT now()      | Last update time      |

**Indexes:**

- Primary key on `id`
- Index on `university` for analytics queries (optional)

### DR-3: API Contract

**User Profile Endpoints:**

```typescript
// GET /api/user/profile
Response: {
  id: string;
  university: string;
  created_at: string;
  updated_at: string;
}

// PUT /api/user/profile
Request: {
  university: string;
}
Response: {
  success: boolean;
  profile: UserProfile;
}
```

## UI/UX Requirements

### UX-1: Onboarding Modal

**Visual Requirements:**

- Centered modal, non-dismissible
- Clear heading: "Welcome to ScheduleFirst AI!"
- Subheading: "Which CUNY school do you attend?"
- Dropdown prominently displayed
- "Get Started" button (primary color)
- Button disabled until selection made
- Loading spinner during save

**Content:**

- Friendly, welcoming tone
- Brief explanation (1 sentence max)
- No jargon

### UX-2: Settings Page

**Visual Requirements:**

- Section titled "University Preference"
- Current university displayed prominently
- "Change" button next to current value
- Dropdown appears inline when editing
- "Save" and "Cancel" buttons when editing
- Confirmation dialog with warning message

**Content:**

- Clear labels
- Confirmation message: "Changing your university will update all course and schedule data. Continue?"

### UX-3: Universal Dropdown Component

**Visual Requirements:**

- Consistent styling across all uses
- Alphabetically sorted schools
- Search/filter capability for long list
- Keyboard navigation support
- Clear visual focus states
- Mobile-friendly tap targets

## Testing Requirements

### TR-1: Unit Tests

- Auth context university functions
- University validation logic
- Settings page component behaviors
- Onboarding modal component behaviors

### TR-2: Integration Tests

- Complete onboarding flow (login → modal → save → dashboard)
- University change flow (settings → change → confirm → save)
- API integration with correct university parameter

### TR-3: E2E Tests

- New user registration → onboarding → first chat
- Existing user login → no onboarding
- Change university → verify in chat/search/optimization

### TR-4: Manual Testing Checklist

- [ ] First login shows onboarding modal
- [ ] Cannot dismiss modal without selection
- [ ] University saves successfully
- [ ] Dashboard loads with correct university
- [ ] AI chat uses correct university
- [ ] Course search uses correct university
- [ ] Schedule optimization uses correct university
- [ ] Can change university in settings
- [ ] Changes persist after logout/login
- [ ] Works on mobile devices
- [ ] Error states display correctly
- [ ] Loading states display correctly

## Deployment Requirements

### DEP-1: Database Migration

- Create migration script for `user_profiles` table
- Run migration in staging environment first
- Verify RLS policies before production
- Create database backup before migration

### DEP-2: Frontend Deployment

- No breaking changes to existing functionality
- Graceful degradation if backend not ready
- Feature flag for onboarding modal (optional)

### DEP-3: Rollback Plan

- Keep old university dropdown as fallback
- Ability to disable onboarding modal
- Database migration rollback script

## Acceptance Criteria

### AC-1: Feature Complete

- [ ] All functional requirements implemented
- [ ] All non-functional requirements met
- [ ] All test cases passing
- [ ] No critical bugs

### AC-2: User Experience

- [ ] Onboarding completes in < 30 seconds
- [ ] No user confusion reported
- [ ] Clear error messages
- [ ] Smooth, bug-free experience

### AC-3: Technical Quality

- [ ] Code review approved
- [ ] TypeScript strict mode passing
- [ ] No console errors
- [ ] Performance benchmarks met
- [ ] Security audit passed

### AC-4: Documentation

- [ ] README updated with new feature
- [ ] API documentation updated
- [ ] Database schema documented
- [ ] User guide/help content created

## Out of Scope (Future Considerations)

The following are **NOT** included in this implementation:

- ❌ Support for non-CUNY schools
- ❌ Multiple university selection per user
- ❌ University verification (student ID, email)
- ❌ University-specific UI themes
- ❌ Historical tracking of university changes
- ❌ Admin panel for managing universities
- ❌ University-based user segmentation/analytics
- ❌ Automatic university detection from email domain
