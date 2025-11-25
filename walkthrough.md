# College Selection Feature Walkthrough

## Overview

We have implemented a hybrid solution for college selection, allowing users to set their university during onboarding and change it later in settings. This selection is persisted in the database and used throughout the application (AI chat, course search, schedule optimization).

## Changes Made

### Database

- **Refactored**: Consolidated user data into the existing `users` table by adding a `university` column.
- **Cleanup**: Removed redundant `user_profiles` table and triggers.
- **Migration**: Created `20251125120000_add_university_to_users.sql`.

### Frontend Components

- **UniversityDropdown**: A reusable component for selecting CUNY schools.
- **UniversityOnboardingModal**: A modal that appears for new users (or users without a university set) to force selection.
- **SettingsPage**: A new page where users can view and update their university preference.

### State Management

- **AuthContext**: Extended to fetch and store `profile` (including `university`) and provide `updateUniversity` function.

### Integration

- **ScheduleBuilder**: Updated to use `profile.university` from context instead of local state.
- **Course Search**: Updated hooks to filter courses by the user's university.
- **Professor Search**: Updated hooks to filter professors by the user's university.
- **App Navigation**: Added "Settings" route and link.

## Verification

### Automated Tests

- Ran `npm run build` successfully (Exit Code 0).

### Manual Verification Steps

1.  **Onboarding**:
    - Sign up a new user.
    - Verify that the "Welcome" modal appears.
    - Select a university and save.
    - Verify modal closes and toast appears.
2.  **Persistence**:
    - Refresh the page.
    - Verify that the modal does NOT appear.
    - Go to Settings page.
    - Verify the selected university is displayed.
3.  **Application Usage**:
    - Go to Schedule Builder.
    - Verify the university is displayed in the header.
    - Search for courses. Verify results are from the selected university.
    - Use AI Chat. Ask "What courses are available?". Verify it knows your university.
4.  **Settings**:
    - Go to Settings.
    - Click "Change".
    - Select a different university.
    - Save.
    - Verify success toast.
    - Go back to Schedule Builder.
    - Verify the new university is reflected.
