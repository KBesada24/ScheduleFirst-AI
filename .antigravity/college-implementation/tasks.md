# College Selection Feature - Implementation Tasks

## Overview

This document outlines all tasks required to implement the hybrid college selection feature. Tasks are organized by phase and include estimates, dependencies, and acceptance criteria.

---

## Phase 1: Database Setup

### Task 1.1: Create User Profiles Table

**Priority:** CRITICAL  
**Estimate:** 30 minutes  
**Dependencies:** None

**Steps:**

- [ ] Create migration file for `user_profiles` table
- [ ] Define schema: `id`, `university`, `created_at`, `updated_at`
- [ ] Set `id` as primary key with foreign key to `auth.users`
- [ ] Set `university` as text field (nullable initially)
- [ ] Add default timestamps
- [ ] Run migration in development

**Acceptance Criteria:**

- Table created successfully
- Foreign key constraint works
- Timestamps auto-populate

**Files to Create/Modify:**

- `supabase/migrations/YYYYMMDDHHMMSS_create_user_profiles.sql`

---

### Task 1.2: Configure Row-Level Security (RLS)

**Priority:** CRITICAL  
**Estimate:** 20 minutes  
**Dependencies:** Task 1.1

**Steps:**

- [ ] Enable RLS on `user_profiles` table
- [ ] Create policy: Users can SELECT their own profile
- [ ] Create policy: Users can INSERT their own profile
- [ ] Create policy: Users can UPDATE their own profile
- [ ] Test RLS policies with test users

**Acceptance Criteria:**

- RLS enabled on table
- Users can only access their own data
- Unauthorized access blocked

**SQL Example:**

```sql
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
  ON user_profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON user_profiles FOR UPDATE
  USING (auth.uid() = id);
```

---

### Task 1.3: Create Database Trigger for Auto-Profile Creation

**Priority:** HIGH  
**Estimate:** 30 minutes  
**Dependencies:** Task 1.1

**Steps:**

- [ ] Create trigger function to auto-create profile on user signup
- [ ] Trigger runs after insert on `auth.users`
- [ ] Sets `university` to NULL initially
- [ ] Test with new user registration

**Acceptance Criteria:**

- New users automatically get profile row
- University starts as NULL
- No errors on registration

**Files to Create/Modify:**

- `supabase/migrations/YYYYMMDDHHMMSS_create_profile_trigger.sql`

---

### Task 1.4: Create Supabase Client Functions

**Priority:** CRITICAL  
**Estimate:** 45 minutes  
**Dependencies:** Task 1.1, 1.2

**Steps:**

- [ ] Create `getUserProfile(userId)` function
- [ ] Create `updateUserProfile(userId, data)` function
- [ ] Add TypeScript types for UserProfile
- [ ] Add error handling
- [ ] Test functions in development

**Acceptance Criteria:**

- Functions work with real Supabase instance
- TypeScript types properly defined
- Error handling covers edge cases

**Files to Create/Modify:**

- `supabase/services/profile-service.ts` (NEW)
- `supabase/types.ts` (MODIFY)

---

## Phase 2: Shared Constants & Types

### Task 2.1: Create University Constants

**Priority:** HIGH  
**Estimate:** 15 minutes  
**Dependencies:** None

**Steps:**

- [ ] Create constants file for CUNY schools
- [ ] Define array of all 11 CUNY schools
- [ ] Export as typed constant
- [ ] Add JSDoc documentation

**Acceptance Criteria:**

- All 11 schools listed correctly
- Consistent naming (title case)
- TypeScript type exported

**Files to Create/Modify:**

- `src/lib/constants/universities.ts` (NEW)

**Code Template:**

```typescript
export const CUNY_SCHOOLS = [
  "Baruch College",
  "Brooklyn College",
  // ... all schools
] as const;

export type CUNYSchool = (typeof CUNY_SCHOOLS)[number];
```

---

### Task 2.2: Create TypeScript Types

**Priority:** HIGH  
**Estimate:** 15 minutes  
**Dependencies:** Task 2.1

**Steps:**

- [ ] Define `UserProfile` interface
- [ ] Define `UniversityDropdownProps` interface
- [ ] Export types from central location
- [ ] Ensure compatibility with Supabase types

**Acceptance Criteria:**

- All types properly defined
- No TypeScript errors
- Types used consistently

**Files to Create/Modify:**

- `src/types/user.ts` (NEW or MODIFY)

---

## Phase 3: Reusable Components

### Task 3.1: Create UniversityDropdown Component

**Priority:** HIGH  
**Estimate:** 1 hour  
**Dependencies:** Task 2.1, 2.2

**Steps:**

- [ ] Create reusable dropdown component
- [ ] Use shadcn Select component
- [ ] Import CUNY_SCHOOLS constant
- [ ] Add props for value, onChange, disabled
- [ ] Add search/filter capability
- [ ] Style consistently with app design
- [ ] Make mobile-friendly

**Acceptance Criteria:**

- Component renders all schools
- Dropdown works on desktop and mobile
- Search/filter works
- Proper TypeScript props

**Files to Create/Modify:**

- `src/components/ui/university-dropdown.tsx` (NEW)

---

### Task 3.2: Create OnboardingModal Component

**Priority:** CRITICAL  
**Estimate:** 1.5 hours  
**Dependencies:** Task 3.1

**Steps:**

- [ ] Create modal component using shadcn Dialog
- [ ] Add welcoming header and description
- [ ] Include UniversityDropdown
- [ ] Add "Get Started" button (disabled until selection)
- [ ] Add loading state during save
- [ ] Add error state with retry
- [ ] Make non-dismissible
- [ ] Style with gradient header (match app theme)

**Acceptance Criteria:**

- Modal displays correctly
- Cannot be dismissed without selection
- Loading state shows during save
- Error handling works
- Responsive design

**Files to Create/Modify:**

- `src/components/onboarding/UniversityOnboardingModal.tsx` (NEW)

---

### Task 3.3: Create Settings/Profile Page

**Priority:** HIGH  
**Estimate:** 2 hours  
**Dependencies:** Task 3.1

**Steps:**

- [x] Create Settings page component
- [x] Add navigation link to settings
- [x] Display current university (read-only)
- [x] Add "Change" button
- [x] Show UniversityDropdown when editing
- [x] Add confirmation dialog
- [x] Implement save/cancel actions
- [x] Add success/error toast notifications
- [x] Style consistently

**Acceptance Criteria:**

- Settings page accessible from nav
- Current university displayed
- Can change university
- Confirmation dialog works
- Toast notifications show

**Files to Create/Modify:**

- `src/components/pages/settings.tsx` (NEW)
- `src/App.tsx` (MODIFY - add route)
- Navigation component (MODIFY - add link)

---

## Phase 4: Auth Context Integration

### Task 4.1: Extend Auth Context

**Priority:** CRITICAL  
**Estimate:** 1.5 hours  
**Dependencies:** Task 1.4, 2.2

**Steps:**

- [x] Add `profile` to AuthContext state
- [x] Add `updateUniversity()` function to context
- [x] Load profile on login/session restore
- [x] Handle loading and error states
- [x] Update TypeScript types
- [x] Add proper error handling

**Acceptance Criteria:**

- Profile loads automatically on login
- University accessible via context
- updateUniversity() works correctly
- Error states handled gracefully

**Files to Create/Modify:**

- `supabase/auth.tsx` (MODIFY)

**Code Changes:**

```typescript
interface AuthContextType {
  // ... existing fields
  profile: UserProfile | null;
  updateUniversity: (university: string) => Promise<void>;
}
```

---

### Task 4.2: Implement Profile Loading Logic

**Priority:** CRITICAL  
**Estimate:** 1 hour  
**Dependencies:** Task 4.1

**Steps:**

- [x] Fetch profile after successful authentication
- [x] Store profile in context state
- [x] Handle case where profile doesn't exist
- [x] Cache profile to avoid re-fetching
- [x] Add loading state
- [x] Test with multiple users

**Acceptance Criteria:**

- Profile loads on login
- Profile persists in context
- No unnecessary API calls
- Loading states work

---

### Task 4.3: Implement Update University Logic

**Priority:** CRITICAL  
**Estimate:** 45 minutes  
**Dependencies:** Task 4.1

**Steps:**

- [x] Create `updateUniversity()` function in context
- [x] Call Supabase update function
- [x] Refresh profile after update
- [x] Handle errors properly
- [x] Show loading state
- [x] Test update flow

**Acceptance Criteria:**

- University updates in database
- Context refreshes automatically
- Errors handled and reported
- UI reflects changes immediately

---

## Phase 5: Application Integration

### Task 5.1: Integrate Onboarding Modal

**Priority:** CRITICAL  
**Estimate:** 1 hour  
**Dependencies:** Task 3.2, 4.2

**Steps:**

- [x] Add modal to main App component or auth-protected layout
- [x] Show modal when `profile.university` is null
- [x] Call `updateUniversity()` on submission
- [x] Close modal on successful save
- [x] Test with new user flow
- [x] Test with existing user (shouldn't show)

**Acceptance Criteria:**

- Modal shows for new users only
- Saves university successfully
- Modal closes after save
- User proceeds to app

**Files to Create/Modify:**

- `src/App.tsx` or `src/components/auth/ProtectedRoute.tsx` (MODIFY)

---

### Task 5.2: Update Schedule Builder

**Priority:** CRITICAL  
**Estimate:** 30 minutes  
**Dependencies:** Task 4.1

**Steps:**

- [x] Remove local `selectedUniversity` state
- [x] Use `profile.university` from auth context
- [x] Update all API calls to use context university
- [x] Remove or hide university dropdown (optional)
- [x] Test all features still work

**Acceptance Criteria:**

- No local state for university
- Uses auth context university
- All features work correctly
- API calls include correct university

**Files to Create/Modify:**

- `src/components/pages/schedule-builder.tsx` (MODIFY)

---

### Task 5.3: Update Course Search

**Priority:** HIGH  
**Estimate:** 20 minutes  
**Dependencies:** Task 4.1

**Steps:**

- [x] Update course search to use `profile.university`
- [x] Remove any hardcoded university values
- [x] Test search results

**Acceptance Criteria:**

- Course search uses correct university
- Results filtered properly

**Files to Create/Modify:**

- Wherever course search is implemented (MODIFY)

---

### Task 5.4: Update AI Chat Context

**Priority:** HIGH  
**Estimate:** 15 minutes  
**Dependencies:** Task 5.2

**Steps:**

- [x] Verify chat already uses context university
- [x] Remove TODO comment
- [x] Test chat responses use correct university

**Acceptance Criteria:**

- Chat context includes correct university
- AI responses reference correct school

**Files to Create/Modify:**

- Already done in previous changes, just verify

---

### Task 5.5: Update Schedule Optimization

**Priority:** HIGH  
**Estimate:** 15 minutes  
**Dependencies:** Task 5.2

**Steps:**

- [x] Verify optimization uses context university
- [x] Test optimization calls

**Acceptance Criteria:**

- Optimization uses correct university
- Results are university-specific

---

### Task 5.6: Update Professor Lookup

**Priority:** MEDIUM  
**Estimate:** 15 minutes  
**Dependencies:** Task 4.1

**Steps:**

- [x] Update professor search to use `profile.university`
- [x] Test professor results

**Acceptance Criteria:**

- Professor lookup filters by university
- Results correct

---

## Phase 6: Settings & Profile Management

### Task 6.1: Add Settings Navigation

**Priority:** MEDIUM  
**Estimate:** 30 minutes  
**Dependencies:** Task 3.3

**Steps:**

- [x] Add "Settings" link to navigation menu
- [x] Add route in App.tsx
- [x] Ensure settings is protected route
- [x] Add icon to nav link

**Acceptance Criteria:**

- Settings accessible from navigation
- Only visible when logged in
- Route works correctly

**Files to Create/Modify:**

- Navigation component (MODIFY)
- `src/App.tsx` (MODIFY)

---

### Task 6.2: Implement University Change Flow

**Priority:** HIGH  
**Estimate:** 1 hour  
**Dependencies:** Task 3.3, 4.3

**Steps:**

- [ ] Wire up change button in settings
- [ ] Show confirmation dialog
- [ ] Call `updateUniversity()` on confirm
- [ ] Show loading state during save
- [ ] Show success toast on completion
- [ ] Show error toast on failure
- [ ] Test complete flow

**Acceptance Criteria:**

- Can change university
- Confirmation required
- Success/error feedback shown
- Changes persist

---

## Phase 7: Testing

### Task 7.1: Write Unit Tests

**Priority:** MEDIUM  
**Estimate:** 2 hours  
**Dependencies:** All previous tasks

**Steps:**

- [ ] Test UniversityDropdown component
- [ ] Test OnboardingModal component
- [ ] Test Settings page component
- [ ] Test auth context functions
- [ ] Test validation logic
- [ ] Achieve >80% code coverage

**Acceptance Criteria:**

- All unit tests passing
- Good code coverage
- Edge cases covered

**Files to Create:**

- `src/components/ui/university-dropdown.test.tsx` (NEW)
- `src/components/onboarding/UniversityOnboardingModal.test.tsx` (NEW)
- `supabase/auth.test.tsx` (MODIFY)

---

### Task 7.2: Write Integration Tests

**Priority:** MEDIUM  
**Estimate:** 1.5 hours  
**Dependencies:** Task 7.1

**Steps:**

- [ ] Test full onboarding flow
- [ ] Test university change flow
- [ ] Test API integration
- [ ] Test error scenarios

**Acceptance Criteria:**

- Integration tests passing
- Key user flows covered
- API mocked properly

---

### Task 7.3: Perform Manual Testing

**Priority:** HIGH  
**Estimate:** 2 hours  
**Dependencies:** All Phase 5 tasks

**Testing Checklist:**

- [ ] New user signup → onboarding modal appears
- [ ] Select university → saves successfully
- [ ] Dashboard loads with correct university
- [ ] AI chat uses correct university in context
- [ ] Course search filters by university
- [ ] Schedule optimization uses university
- [ ] Professor lookup filters by university
- [ ] Navigate to settings
- [ ] Change university → confirmation appears
- [ ] Confirm change → saves successfully
- [ ] Logout and login → university persists
- [ ] Try on mobile device
- [ ] Test error scenarios (network failure, etc.)
- [ ] Test with different CUNY schools

**Acceptance Criteria:**

- All manual tests pass
- No bugs found
- Smooth user experience

---

### Task 7.4: Performance Testing

**Priority:** LOW  
**Estimate:** 30 minutes  
**Dependencies:** Task 7.3

**Steps:**

- [ ] Measure onboarding modal load time
- [ ] Measure save operation time
- [ ] Check for unnecessary re-renders
- [ ] Verify profile caching works

**Acceptance Criteria:**

- Modal loads < 500ms
- Save completes < 2 seconds
- No performance regressions

---

## Phase 8: Documentation & Deployment

### Task 8.1: Update Documentation

**Priority:** MEDIUM  
**Estimate:** 1 hour  
**Dependencies:** All previous tasks

**Steps:**

- [ ] Update README with new feature
- [ ] Document database schema
- [ ] Document API changes (if any)
- [ ] Create user guide for settings
- [ ] Add inline code comments

**Acceptance Criteria:**

- README updated
- All docs current
- Easy for new devs to understand

**Files to Create/Modify:**

- `README.md` (MODIFY)
- `docs/database-schema.md` (MODIFY)
- `docs/user-guide.md` (NEW or MODIFY)

---

### Task 8.2: Database Migration (Production)

**Priority:** CRITICAL  
**Estimate:** 1 hour  
**Dependencies:** All Phase 1 tasks

**Steps:**

- [ ] Backup production database
- [ ] Run migration in staging first
- [ ] Verify RLS policies
- [ ] Run migration in production
- [ ] Verify no errors
- [ ] Spot check existing users

**Acceptance Criteria:**

- Migration successful
- No data loss
- RLS working correctly
- Existing users unaffected

---

### Task 8.3: Deploy Frontend

**Priority:** CRITICAL  
**Estimate:** 30 minutes  
**Dependencies:** Task 7.3, 8.1

**Steps:**

- [ ] Merge feature branch to main
- [ ] Build production bundle
- [ ] Deploy to hosting
- [ ] Verify deployment successful
- [ ] Test in production

**Acceptance Criteria:**

- Deployment successful
- No console errors
- Feature works in production

---

### Task 8.4: Monitor & Support

**Priority:** HIGH  
**Estimate:** Ongoing (first week)  
**Dependencies:** Task 8.3

**Steps:**

- [ ] Monitor error logs for first 48 hours
- [ ] Check user adoption rate
- [ ] Respond to user feedback
- [ ] Fix critical bugs immediately

**Acceptance Criteria:**

- No critical bugs
- Good user adoption
- Positive user feedback

---

## Summary

### Total Estimated Time: ~20-25 hours

### Critical Path Tasks (Must Complete First):

1. Task 1.1 - Create User Profiles Table
2. Task 1.2 - Configure RLS
3. Task 1.4 - Supabase Client Functions
4. Task 4.1 - Extend Auth Context
5. Task 3.2 - Create Onboarding Modal
6. Task 5.1 - Integrate Onboarding Modal
7. Task 5.2 - Update Schedule Builder

### Task Breakdown by Role:

**Backend/Database (5-6 hours):**

- Tasks 1.1, 1.2, 1.3, 1.4

**Frontend Components (7-8 hours):**

- Tasks 2.1, 2.2, 3.1, 3.2, 3.3

**Integration (4-5 hours):**

- Tasks 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2

**Testing (4-5 hours):**

- Tasks 7.1, 7.2, 7.3, 7.4

**Deployment (2-3 hours):**

- Tasks 8.1, 8.2, 8.3, 8.4

---

## Risk Mitigation

### High-Risk Tasks:

- **Task 1.2 (RLS):** Test thoroughly in staging
- **Task 5.1 (Onboarding Integration):** Ensure doesn't break existing auth flow
- **Task 8.2 (Production Migration):** Have rollback plan ready

### Rollback Plan:

- Keep feature flag for onboarding modal
- Database migration has rollback script
- Can revert to local university dropdown if needed
