# Frontend-Backend Integration Requirements

## Project Overview

**Objective**: Integrate React frontend buttons and components with the FastAPI backend services to enable AI-powered schedule optimization, course search, and professor evaluation features.

**Scope**: This document defines the functional and technical requirements for connecting UI components in `src/` to backend services in `services/`.

---

## 1. Functional Requirements

### FR-1: Schedule Optimization Integration

**Description**: Enable users to generate AI-optimized schedules via the OptimizeButton component.

**Requirements**:
- **FR-1.1**: OptimizeButton shall call `/api/schedule/optimize` endpoint when clicked
- **FR-1.2**: User can select 1-10 course codes for optimization
- **FR-1.3**: User can specify optional constraints:
  - Preferred days (Mon-Fri)
  - Earliest start time (format: "HH:MM")
  - Latest end time (format: "HH:MM")
  - Minimum professor rating (0-5)
  - Avoid gaps preference (boolean)
- **FR-1.4**: System shall validate all inputs before API call
- **FR-1.5**: System shall display 1-5 optimized schedule options
- **FR-1.6**: Each schedule shall include:
  - Course sections with times
  - Overall preference score
  - Detected conflicts (if any)
  - AI reasoning/explanation
  - Metadata (avg rating, credits, etc.)
- **FR-1.7**: System shall allow user to preview and select from multiple schedule options

**Acceptance Criteria**:
- [x] Button is disabled when no courses selected
- [x] Validation errors displayed as toasts
- [x] Progress indicator shown during optimization (0-100%)
- [x] Results displayed within 5 seconds
- [x] User can switch between generated schedules

---

### FR-2: AI Chat Assistant Integration

**Description**: Enable conversational interface for schedule planning via ChatButton.

**Requirements**:
- **FR-2.1**: ChatButton shall call `/api/chat/message` endpoint
- **FR-2.2**: User can send natural language queries
- **FR-2.3**: System shall send conversation context:
  - Current schedule (if any)
  - User preferences
  - Current semester
- **FR-2.4**: System shall parse AI responses for:
  - Text reply
  - Suggested schedules
  - Actionable items
- **FR-2.5**: System shall display quick-action buttons for AI suggestions
- **FR-2.6**: Chat history shall persist during session

**Acceptance Criteria**:
- [x] Empty messages are prevented
- [x] Loading state shows "Thinking..." animation
- [x] AI responses rendered within 3 seconds
- [x] Suggested schedules can be previewed
- [x] Action buttons execute suggested changes

---

### FR-3: Enhanced Course Search Integration

**Description**: Add AI-powered semantic search as optional enhancement to existing course search.

**Requirements**:
- **FR-3.1**: SearchButton shall support two modes:
  - Direct mode: Use existing Supabase queries (default)
  - Enhanced mode: Use `/api/courses/search` for semantic search
- **FR-3.2**: Enhanced mode activated when query contains natural language
- **FR-3.3**: System shall handle same filters as direct mode
- **FR-3.4**: Results shall indicate search method used
- **FR-3.5**: Fallback to direct mode if backend unavailable

**Acceptance Criteria**:
- [x] Searches complete within 1 second (direct) or 2 seconds (enhanced)
- [x] Results are cached for 5 minutes
- [x] Empty states handled gracefully
- [x] Filters work consistently across both modes

---

### FR-4: Professor Data Integration

**Description**: Fetch professor ratings and reviews from backend.

**Requirements**:
- **FR-4.1**: ProfessorButton shall call `/api/professor/{name}` endpoint
- **FR-4.2**: System shall display:
  - Average rating (0-5)
  - Average difficulty (0-5)
  - Review count
  - Letter grade (A-F)
  - Composite score (0-100)
  - Recent reviews
- **FR-4.3**: Data cached for 1 hour
- **FR-4.4**: Support fuzzy name matching
- **FR-4.5**: Filter by university/department

**Acceptance Criteria**:
- [x] Professor data loads within 1 second
- [x] Reviews displayed in modal/detail view
- [x] Grade prominently displayed
- [x] No data state handled

---

### FR-5: Schedule Validation Enhancement

**Description**: Add backend-powered conflict detection and validation.

**Requirements**:
- **FR-5.1**: ScheduleActionButton shall call `/api/schedule/validate` before adding courses
- **FR-5.2**: Backend shall detect:
  - Time conflicts
  - Location conflicts (travel time)
  - Prerequisite violations
  - Capacity issues
- **FR-5.3**: System shall display conflict warnings
- **FR-5.4**: System shall suggest alternative sections if conflicts found
- **FR-5.5**: User can override warnings (soft conflicts only)

**Acceptance Criteria**:
- [x] Validation completes within 500ms
- [x] Conflicts clearly highlighted
- [x] Alternative suggestions provided
- [x] Optimistic updates rollback on error

---

## 2. Technical Requirements

### TR-1: API Client Configuration

**Requirements**:
- **TR-1.1**: API base URL configurable via environment variable `VITE_API_URL`
- **TR-1.2**: Development: `http://localhost:8000`
- **TR-1.3**: Production: Set via Vercel environment variables
- **TR-1.4**: API client shall include:
  - Automatic auth token injection
  - Request/response interceptors
  - Retry logic (3 attempts with exponential backoff)
  - Error transformation

**Implementation Files**:
- `src/lib/api-client.ts` (existing, needs update)
- `.env` (create for development)
- `.env.production` (Vercel)

---

### TR-2: Type Safety

**Requirements**:
- **TR-2.1**: All API endpoints shall have TypeScript interfaces
- **TR-2.2**: Request/response types shall match backend Pydantic models
- **TR-2.3**: No `any` types in API integration code
- **TR-2.4**: Use branded types for IDs (e.g., `type CourseId = string & { __brand: 'CourseId' }`)

**Implementation Files**:
- `src/lib/api-endpoints.ts` (existing, needs expansion)
- `src/types/api-types.ts` (create for shared types)

---

### TR-3: Error Handling

**Requirements**:
- **TR-3.1**: Network errors: Auto-retry 3x with backoff (1s, 2s, 4s)
- **TR-3.2**: 401/403 errors: Redirect to login, preserve return URL
- **TR-3.3**: 400 errors: Display validation errors inline
- **TR-3.4**: 404 errors: Show not found message
- **TR-3.5**: 500 errors: Log to monitoring, show generic error
- **TR-3.6**: Timeout: 30 seconds for normal requests, 60 seconds for AI requests

**Implementation Files**:
- `src/lib/error-handler.ts` (existing, needs enhancement)
- `src/components/ErrorBoundary.tsx` (existing)

---

### TR-4: Loading States

**Requirements**:
- **TR-4.1**: All buttons shall show loading state during API calls
- **TR-4.2**: Long operations (\>2s) shall show progress indicator
- **TR-4.3**: Content loading (\>500ms) shall show skeleton screens
- **TR-4.4**: Optimistic updates for high-success operations
- **TR-4.5**: Loading states prevent double-clicks

**Implementation Files**:
- `src/components/ui/loading-indicators.tsx` (existing)
- Individual button components

---

### TR-5: Performance

**Requirements**:
- **TR-5.1**: Search requests debounced by 300ms
- **TR-5.2**: Cache responses:
  - Course searches: 5 minutes
  - Professor data: 1 hour
  - User schedules: No cache
- **TR-5.3**: Lazy load heavy components
- **TR-5.4**: Memoize expensive calculations
- **TR-5.5**: Use React.memo for pure components

**Implementation Files**:
- `src/lib/performance-utils.ts` (existing)
- `src/hooks/useCourseSearch.ts` (existing, already implements caching)

---

### TR-6: Security

**Requirements**:
- **TR-6.1**: All API calls include Supabase auth token
- **TR-6.2**: Tokens refreshed automatically before expiration
- **TR-6.3**: Sensitive data never logged
- **TR-6.4**: Input sanitization on both client and server
- **TR-6.5**: HTTPS enforced in production
- **TR-6.6**: CORS properly configured

**Implementation Files**:
- `src/lib/api-client.ts` (auth injection)
- `supabase/auth.tsx` (token management)
- `services/api_server.py` (CORS config)

---

### TR-7: Monitoring and Analytics

**Requirements**:
- **TR-7.1**: Track all button clicks with event analytics
- **TR-7.2**: Log API response times
- **TR-7.3**: Monitor error rates
- **TR-7.4**: Track feature usage (which buttons most used)
- **TR-7.5**: Performance metrics for optimization operations

**Implementation Files**:
- `src/lib/analytics.ts` (create)
- Backend logging in `services/mcp_server/utils/logger.py`

---

## 3. Data Requirements

### DR-1: API Response Formats

All API responses shall follow this structure:
```json
{
  "data": {},        // Response data
  "error": null,     // Error object if failed
  "meta": {          // Metadata
    "timestamp": "2025-11-23T20:00:00Z",
    "requestId": "uuid",
    "duration": 1250
  }
}
```

### DR-2: Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid course code",
    "details": {
      "field": "courseCodes[0]",
      "value": "",
      "constraint": "non-empty"
    }
  }
}
```

### DR-3: Pagination

For list endpoints:
```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 245,
    "hasMore": true
  }
}
```

---

## 4. Environment Requirements

### Development Environment

**Frontend**:
- Node.js 20+
- npm/pnpm
- Vite dev server on port 5173
- Environment variables in `.env`

**Backend**:
- Python 3.11+
- FastAPI server on port 8000
- Environment variables in `.env`

**Required Environment Variables**:
```bash
# Frontend (.env)
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_anon_key

# Backend (.env)
GEMINI_API_KEY=your_gemini_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_key
DATABASE_URL=your_db_url
API_HOST=0.0.0.0
API_PORT=8000
```

### Production Environment

**Frontend**:
- Deployed on Vercel
- Environment variables configured in Vercel dashboard
- VITE_API_URL points to production backend

**Backend**:
- Deployed on Railway/Fly.io
- Environment variables configured in platform dashboard
- CORS allows production frontend origin

---

## 5. Testing Requirements

### Unit Tests

**TR-TEST-1**: Each button component shall have unit tests covering:
- Rendering with various props
- Click handlers
- Validation logic
- Loading states
- Error states

**TR-TEST-2**: API client functions shall have tests covering:
- Successful responses
- Network errors
- Authentication errors
- Validation errors
- Retry logic

### Integration Tests

**TR-TEST-3**: Button-to-API integration tests:
- Use Mock Service Worker (MSW) for API mocking
- Test complete flow from button click to UI update
- Test error scenarios
- Test loading states

### End-to-End Tests

**TR-TEST-4**: Critical user flows:
- Search courses → Add to schedule → Optimize
- Chat with AI → Apply suggestion
- View professor → Compare professors

**Tools**: Playwright or Cypress

---

## 6. Documentation Requirements

**DR-DOC-1**: API endpoint documentation
- OpenAPI/Swagger spec for backend
- TypeScript interfaces for frontend
- Example requests/responses

**DR-DOC-2**: Component usage documentation
- Props interface
- Usage examples
- Integration examples

**DR-DOC-3**: Deployment documentation
- Environment setup guide
- Deployment steps
- Troubleshooting guide

---

## 7. Performance Requirements

### Response Time Targets

| Operation | Target | Maximum |
|-----------|--------|---------|
| Course search | \<500ms | 1s |
| Professor lookup | \<1s | 2s |
| AI optimization | \<3s | 5s |
| Chat message | \<2s | 4s |
| Schedule validation | \<300ms | 500ms |

### Throughput

- Support 100 concurrent users
- 1000 requests/hour per user
- AI operations: 10/hour per user (rate limited)

### Availability

- Frontend: 99.9% uptime
- Backend: 99.5% uptime
- Graceful degradation if backend unavailable

---

## 8. Compatibility Requirements

### Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Mobile Support

- Responsive design for all screen sizes
- Touch-friendly button targets (44x44px minimum)
- Works on iOS 14+ and Android 10+

---

## 9. Accessibility Requirements

**ACC-1**: All buttons shall be keyboard accessible (Enter/Space to activate)
**ACC-2**: Loading states announced to screen readers
**ACC-3**: Error messages accessible via ARIA live regions
**ACC-4**: WCAG 2.1 AA compliance
**ACC-5**: Color contrast ratio \>4.5:1 for text

---

## 10. Migration Requirements

### Backward Compatibility

**MIG-1**: Existing features must continue to work during migration
**MIG-2**: Direct Supabase queries remain available as fallback
**MIG-3**: Feature flags control backend integration rollout
**MIG-4**: No breaking changes to existing components

### Rollout Plan

**Phase 1**: Development environment integration
**Phase 2**: Staging environment testing
**Phase 3**: Production deployment with 10% traffic
**Phase 4**: Gradual rollout to 100% traffic
**Phase 5**: Remove feature flags after stability confirmation

---

## 11. Dependencies

### Frontend Dependencies (Existing)
- React 18
- TypeScript 5
- React Router 6
- Tailwind CSS
- Radix UI
- Lucide icons

### Backend Dependencies (Existing)
- FastAPI
- Pydantic
- Google Gemini API
- Supabase client
- APScheduler

### New Dependencies (If Needed)
- Frontend: None (use existing packages)
- Backend: Additional as needed for features

---

## 12. Success Criteria

**Integration is successful when**:
1. ✅ All 8 button components successfully integrate with backend
2. ✅ AI optimization generates schedules within 5 seconds
3. ✅ Chat provides helpful responses within 3 seconds
4. ✅ Professor data loads within 1 second
5. ✅ Error rate \<2% for API calls
6. ✅ No degradation in existing functionality
7. ✅ All tests pass (unit + integration + e2e)
8. ✅ Performance targets met
9. ✅ Accessibility standards maintained
10. ✅ Documentation complete and accurate

---

## 13. Out of Scope

The following are explicitly **NOT** included in this integration:

- Mobile app development
- Email notification system
- DegreeWorks integration
- Schedule sharing features
- Real-time collaboration
- Push notifications
- Offline support
- Multi-language support

These may be added in future phases.

---

## 14. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Backend unavailable | High | Fallback to direct Supabase queries |
| AI API rate limits | Medium | Client-side throttling, queue requests |
| Slow AI responses | Medium | Show progress, set timeout, cache results |
| Type mismatches | Medium | Validation layer, runtime type checking |
| CORS issues | High | Proper configuration, testing |
| Auth token expiry | Medium | Auto-refresh, graceful re-auth |

---

## Conclusion

This requirements document defines the functional, technical, and performance requirements for integrating the React frontend with the FastAPI backend. All requirements are designed to ensure a robust, performant, and user-friendly integration while maintaining backward compatibility and allowing for graceful degradation.
