# Implementation Plan

## Overview

This implementation plan breaks down the button routing and integration system into discrete, actionable coding tasks. Each task builds incrementally on previous work, ensuring all buttons function correctly with proper routing, backend calls, and DOM updates.

## Task List

- [x] 1. Audit and document existing button implementations


  - Review all button components in the codebase
  - Document current onClick handlers and their behavior
  - Identify missing functionality or broken integrations
  - Create a mapping of buttons to their expected actions
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Implement navigation button enhancements



- [x] 2.1 Create reusable NavigationButton component


  - Build component with to, variant, requiresAuth props
  - Integrate with React Router's useNavigate hook
  - Add hover and active state styling
  - Implement loading state during navigation
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2.2 Update ProtectedRoute component


  - Enhance authentication check logic
  - Add loading spinner during auth verification
  - Implement redirect with return URL preservation
  - Test with authenticated and unauthenticated users
  - _Requirements: 1.5_

- [x] 2.3 Replace existing navigation buttons


  - Update landing page buttons (Get Started, Sign In)
  - Update header navigation links (Schedule Builder, Dashboard)
  - Update sidebar navigation links
  - Verify all routes navigate correctly
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 3. Implement authentication button functionality




- [x] 3.1 Create AuthButton component


  - Build component with action prop (login, signup, logout)
  - Integrate with useAuth hook
  - Add loading state with spinner
  - Implement success/error callbacks
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3.2 Enhance useAuth hook


  - Add retry logic for network failures (3 attempts, exponential backoff)
  - Implement token refresh mechanism
  - Add error state management
  - Provide clear error messages for different failure types
  - _Requirements: 2.1, 2.2, 2.3, 10.5_

- [x] 3.3 Update authentication forms


  - Replace form submit buttons with AuthButton
  - Add form validation before submission
  - Display field-specific error messages
  - Implement success navigation (dashboard or success page)
  - _Requirements: 2.1, 2.2, 2.4, 12.1, 12.2, 12.3_

- [x] 3.4 Implement logout functionality


  - Update dropdown menu logout button
  - Call signOut from useAuth
  - Clear user session and local storage
  - Navigate to landing page after logout
  - _Requirements: 2.3_

- [x] 4. Implement course search button functionality





- [x] 4.1 Create SearchButton component


  - Build component with query and filters props
  - Validate inputs before search
  - Call searchCourses from supabase-queries
  - Handle loading and error states
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4.2 Enhance useCourseSearch hook


  - Implement debouncing (300ms delay)
  - Add caching for search results (5 minutes)
  - Provide loading and error states
  - Auto-refetch when filters change
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 4.3 Update CourseSearch component


  - Integrate SearchButton component
  - Display loading spinner during search
  - Show "No courses found" message for empty results
  - Update course list on successful search
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4.4 Implement filter functionality


  - Add filter dropdowns (department, modality, time slot)
  - Trigger search when filters change
  - Clear filters button
  - Persist filters in URL query params
  - _Requirements: 3.3_

- [x] 5. Implement schedule management button functionality


- [x] 5.1 Create ScheduleActionButton component


  - Build component with action prop (add, remove)
  - Call addSectionToSchedule or removeSectionFromSchedule
  - Implement optimistic UI updates
  - Add rollback on error
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 5.2 Implement conflict detection


  - Call checkScheduleConflicts before adding section
  - Display conflict alert dialog with details
  - Prevent adding conflicting sections
  - Show conflict indicators on schedule grid
  - _Requirements: 4.5, 13.7_

- [x] 5.3 Update CourseCard component


  - Add "Add to Schedule" button for each section
  - Integrate ScheduleActionButton
  - Show success feedback on add
  - Disable button if section already in schedule
  - _Requirements: 4.1, 4.2_

- [x] 5.4 Implement schedule grid updates


  - Update ScheduleGrid component to accept sections prop
  - Re-render grid when sections change
  - Maintain scroll position during updates
  - Add smooth transition animations
  - _Requirements: 4.2, 4.3, 11.3, 13.8_

- [x] 6. Implement AI chat button functionality




- [ ] 6.1 Create ChatButton component
  - Build component with message and context props
  - Validate message is not empty
  - Call /api/chat/message endpoint
  - Display "thinking" animation during processing


  - _Requirements: 5.1, 5.2, 5.3, 5.6_

- [ ] 6.2 Implement chat message handling
  - Add user message to chat history immediately
  - Send message to backend API


  - Parse AI response for schedule suggestions
  - Add AI response to chat history
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 6.3 Implement AI schedule suggestion parsing


  - Extract schedule data from API response
  - Map courses to ScheduleGrid format
  - Validate schedule data structure
  - Handle missing or invalid data gracefully
  - _Requirements: 5.4, 13.1, 13.2_



- [ ] 6.4 Integrate chat with calendar grid
  - Update ScheduleGrid when AI suggests schedule
  - Map each course to correct time slots




  - Use distinct colors for each course
  - Display schedule in preview panel
  - _Requirements: 5.5, 13.3, 13.4_

- [x] 6.5 Implement schedule preview functionality

  - Allow user to preview suggested schedules
  - Switch between multiple schedule options
  - Update calendar grid on preview switch (< 100ms)
  - Add "Apply to My Schedule" button
  - _Requirements: 13.5, 13.6_



- [ ] 7. Implement schedule optimization button functionality
- [ ] 7.1 Create OptimizeButton component
  - Build component with courseCodes and constraints props
  - Validate course codes exist
  - Call /api/schedule/optimize endpoint

  - Display loading state with progress indicator
  - _Requirements: 6.1, 6.2_

- [ ] 7.2 Implement optimization request handling
  - Gather user's required courses
  - Collect schedule constraints (time preferences, professor ratings)

  - Send optimization request to backend
  - Handle API errors gracefully
  - _Requirements: 6.1, 6.2, 6.6_

- [ ] 7.3 Display optimized schedule options
  - Render 3-5 optimized schedules in preview cards
  - Show score, reasoning, and metadata for each




  - Highlight conflicts if any
  - Allow user to select preferred schedule
  - _Requirements: 6.3_

- [x] 7.4 Implement schedule application flow


  - Extract sections from selected schedule
  - Call updateSchedule to save to database
  - Update ScheduleGrid with new sections
  - Parse days and times for grid positioning
  - _Requirements: 6.4, 6.5, 13.2, 13.3_



- [ ] 7.5 Implement calendar grid rendering for optimized schedules
  - Calculate grid positions (row, column, span)
  - Render course blocks in correct cells




  - Apply color coding (blue, purple, green, etc.)
  - Add course labels (code, time, location)
  - Display conflict indicators if needed
  - Add smooth transition animation (fade-in)
  - _Requirements: 6.5, 13.3, 13.4, 13.7_


- [ ] 8. Implement professor rating button functionality
- [ ] 8.1 Create ProfessorButton component
  - Build component with professorId or professorName prop
  - Call getProfessorById or getProfessorByName
  - Display loading skeleton during fetch

  - Open modal/dialog with professor details
  - _Requirements: 7.1, 7.2, 7.5_

- [ ] 8.2 Implement professor detail modal
  - Display professor name, grade, and ratings





  - Show review count and sentiment analysis
  - Render individual reviews
  - Add "Compare Professors" button
  - _Requirements: 7.2, 7.4_



- [ ] 8.3 Implement professor comparison view
  - Allow selection of 2-4 professors
  - Display side-by-side comparison
  - Highlight best professor with AI recommendation
  - Show key metrics (rating, difficulty, reviews)
  - _Requirements: 7.3_

- [ ] 9. Implement admin panel button functionality
- [ ] 9.1 Create AdminActionButton component
  - Build component with action prop (seed, clear)
  - Add confirmation dialog for destructive actions
  - Call seedDatabase or clearDatabase
  - Display progress indicator
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 9.2 Implement database seeding
  - Call seedDatabase function
  - Display success message with details
  - Log seeded data to console
  - Handle errors gracefully
  - _Requirements: 8.1, 8.2_

- [ ] 9.3 Implement database clearing
  - Show confirmation dialog with warning
  - Call clearDatabase on confirmation
  - Display success message
  - Handle errors gracefully
  - _Requirements: 8.3, 8.4, 8.5_

- [ ] 10. Implement dashboard refresh button functionality
- [ ] 10.1 Create RefreshButton component
  - Build component with onRefresh callback
  - Display spinning icon during refresh
  - Disable button during refresh
  - Re-enable after 2 seconds
  - _Requirements: 9.1, 9.2, 9.4, 9.5_

- [ ] 10.2 Implement dashboard data refresh
  - Trigger refetch of all dashboard widgets
  - Update DashboardGrid with new data
  - Update TaskBoard with new data
  - Maintain scroll position during refresh
  - _Requirements: 9.1, 9.3_

- [x] 11. Implement backend API integration


- [x] 11.1 Create API client utility


  - Build centralized API client with fetch wrapper
  - Add request/response interceptors
  - Include auth token in headers
  - Handle CORS and credentials
  - _Requirements: 10.1, 10.2_

- [x] 11.2 Implement error handling middleware


  - Parse API error responses
  - Map error codes to user-friendly messages
  - Log errors to console
  - Provide retry mechanism for network errors
  - _Requirements: 10.3, 10.4, 10.5_

- [x] 11.3 Implement API endpoints integration


  - Connect /api/courses endpoint
  - Connect /api/schedule/optimize endpoint
  - Connect /api/professor/{name} endpoint
  - Connect /api/chat/message endpoint
  - Verify all endpoints return expected data
  - _Requirements: 10.1, 10.2, 10.3_

- [x] 12. Implement real-time DOM updates


- [x] 12.1 Add visual feedback for button interactions


  - Implement hover states for all buttons
  - Add active states (pressed effect)
  - Show focus indicators for keyboard navigation
  - Add ripple effect on click (optional)
  - _Requirements: 11.1_

- [x] 12.2 Implement loading indicators


  - Add spinners for async operations
  - Add skeleton loaders for data fetching
  - Add progress bars for long operations
  - Ensure indicators appear within 100ms
  - _Requirements: 11.2_



- [x] 12.3 Implement success/error notifications





  - Create toast notification component
  - Display success messages for 3 seconds
  - Display error messages until dismissed
  - Position notifications in top-right corner


  - _Requirements: 11.4, 11.5_

- [ ] 12.4 Optimize DOM update performance
  - Use React.memo for expensive components




  - Implement useMemo for calculations
  - Use useCallback for event handlers
  - Ensure updates complete within 100ms
  - _Requirements: 11.3_



- [x] 13. Implement form validation and submission





- [x] 13.1 Create form validation utility

  - Build validation functions for common fields (email, password, etc.)
  - Add custom validation rules
  - Return field-specific error messages


  - Support async validation (e.g., check if email exists)
  - _Requirements: 12.1, 12.2_

- [x] 13.2 Implement form submission handling





  - Validate all fields before submission
  - Display validation errors inline
  - Disable submit button during processing
  - Clear form or navigate on success
  - _Requirements: 12.3, 12.4, 12.5_


- [x] 13.3 Update all forms with validation


  - Update login form
  - Update signup form
  - Update course search form
  - Update schedule constraints form

  - _Requirements: 12.1, 12.2, 12.3_

- [ ] 14. Implement comprehensive error handling
- [ ] 14.1 Create error boundary component
  - Catch React errors in component tree
  - Display fallback UI

  - Log errors to monitoring service
  - Provide "Try again" button
  - _Requirements: 10.4_

- [ ] 14.2 Implement network error handling
  - Detect network failures
  - Display "Connection lost" message
  - Retry with exponential backoff (3 attempts)
  - Show cached data if available
  - _Requirements: 10.5_

- [ ] 14.3 Implement authentication error handling
  - Detect expired sessions
  - Display "Session expired" message
  - Redirect to login page
  - Preserve intended destination
  - _Requirements: 10.4_

- [ ] 14.4 Implement validation error handling
  - Display field-specific errors
  - Highlight invalid fields in red
  - Prevent form submission until resolved
  - Clear errors when user corrects input
  - _Requirements: 12.2_

- [x] 15. Implement calendar grid component enhancements



- [x] 15.1 Build ScheduleGrid time slot rendering


  - Create grid with time slots (8 AM - 11 PM)
  - Add day columns (Monday - Friday)
  - Style grid with borders and headers
  - Make grid responsive for mobile
  - _Requirements: 13.3_

- [x] 15.2 Implement course block rendering

  - Parse section days (MWF, TTh, etc.)
  - Calculate grid position from start/end times
  - Render course blocks in correct cells
  - Calculate row span based on duration
  - _Requirements: 13.2, 13.3_

- [x] 15.3 Implement color coding system

  - Assign distinct colors to each course
  - Use color palette (blue, purple, green, orange, pink)
  - Ensure sufficient contrast for readability
  - Apply colors consistently across views
  - _Requirements: 13.4_

- [x] 15.4 Implement conflict indicators

  - Detect overlapping courses
  - Highlight conflicts in red
  - Add warning icon
  - Display conflict details on hover
  - _Requirements: 13.7_

- [x] 15.5 Implement course labels

  - Display course code in block
  - Show time range
  - Show location if available
  - Truncate text if block is small
  - _Requirements: 13.3_

- [x] 15.6 Implement smooth transitions

  - Add fade-in animation for new courses
  - Add fade-out animation for removed courses
  - Ensure transitions complete within 300ms
  - Maintain scroll position during updates
  - _Requirements: 13.6, 13.8_

- [x] 16. Integration testing and bug fixes


- [x] 16.1 Test navigation flow

  - Test all navigation buttons
  - Verify protected routes redirect correctly
  - Test authentication flow (login, signup, logout)
  - Verify return URL preservation
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 16.2 Test course search flow

  - Test search with various queries
  - Test filters (department, modality, time slot)
  - Test empty results handling
  - Test loading and error states
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 16.3 Test schedule management flow

  - Test adding sections to schedule
  - Test removing sections from schedule
  - Test conflict detection
  - Test calendar grid updates
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 16.4 Test AI integration flow

  - Test chat message sending
  - Test AI response handling
  - Test schedule suggestion parsing
  - Test calendar grid updates from AI
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 16.5 Test schedule optimization flow

  - Test optimization request
  - Test schedule options display
  - Test schedule application
  - Test calendar grid updates from optimization
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 16.6 Test professor rating flow

  - Test professor detail loading
  - Test professor comparison
  - Test review display
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 16.7 Test admin panel flow

  - Test database seeding
  - Test database clearing
  - Test confirmation dialogs
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 16.8 Test error handling

  - Test network errors
  - Test authentication errors
  - Test validation errors
  - Test API errors
  - _Requirements: 10.4, 10.5_

- [x] 16.9 Fix identified bugs

  - Document all bugs found during testing
  - Prioritize bugs by severity
  - Fix critical bugs first
  - Verify fixes with regression tests

- [x] 17. Performance optimization


- [x] 17.1 Implement debouncing

  - Add debouncing to search input (300ms)
  - Add debouncing to filter changes (200ms)
  - Verify reduced API calls
  - _Requirements: 11.2_

- [x] 17.2 Implement memoization

  - Add useMemo to course list rendering
  - Add useMemo to schedule grid calculations
  - Add useCallback to event handlers
  - Measure performance improvements
  - _Requirements: 11.3_

- [x] 17.3 Implement caching

  - Cache course search results (5 minutes)
  - Cache professor ratings (1 hour)
  - Cache user schedules until mutation
  - Verify cache hits in network tab
  - _Requirements: 11.3_

- [x] 17.4 Implement lazy loading

  - Lazy load professor reviews
  - Paginate course search results
  - Lazy load images (avatars)
  - Measure load time improvements
  - _Requirements: 11.3_

- [x] 17.5 Verify performance targets

  - Button click response < 50ms
  - API call initiation < 100ms
  - DOM update after data load < 100ms
  - Calendar grid render < 200ms
  - Page navigation < 300ms
  - _Requirements: 11.1, 11.2, 11.3_

- [x] 18. Accessibility improvements


- [x] 18.1 Implement keyboard navigation

  - Ensure all buttons accessible via Tab
  - Implement Enter/Space key handlers
  - Add visible focus indicators
  - Test with keyboard only
  - _Requirements: 11.1_

- [x] 18.2 Implement screen reader support

  - Add descriptive ARIA labels to buttons
  - Announce loading states
  - Announce error messages
  - Test with screen reader (NVDA/JAWS)
  - _Requirements: 11.2, 11.4_

- [x] 18.3 Implement visual indicators

  - Ensure high contrast colors (WCAG AA)
  - Add loading spinners
  - Add success/error icons
  - Style disabled states clearly
  - _Requirements: 11.2, 11.4, 11.5_

- [x] 18.4 Implement responsive design

  - Test buttons on mobile devices
  - Ensure touch targets ≥ 44x44px
  - Make calendar grid responsive
  - Test on various screen sizes
  - _Requirements: 11.1_

- [x] 19. Documentation and cleanup



- [x] 19.1 Document button components

  - Add JSDoc comments to all button components
  - Document props and their types
  - Provide usage examples
  - Document event handlers


- [ ] 19.2 Document hooks
  - Add JSDoc comments to custom hooks
  - Document return values
  - Provide usage examples
  - Document side effects


- [ ] 19.3 Document API integration
  - Document all API endpoints
  - Provide request/response examples
  - Document error codes

  - Update API documentation

- [ ] 19.4 Clean up code
  - Remove unused imports
  - Remove console.logs

  - Format code consistently
  - Run linter and fix issues

- [ ] 19.5 Update README
  - Document new features
  - Update setup instructions
  - Add troubleshooting section
  - Update screenshots

## Notes

- Each task should be completed and tested before moving to the next
- Tasks marked with sub-tasks should complete all sub-tasks before marking the parent complete
- All code should follow existing project conventions and style guides
- Run `pnpm lint` and `pnpm build` after each task to ensure no regressions
- Test in both development and production builds
- Verify changes work across different browsers (Chrome, Firefox, Safari)
