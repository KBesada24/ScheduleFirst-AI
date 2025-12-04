/**
 * API Endpoints Integration
 * 
 * Typed API endpoint functions for backend integration
 */

import { apiClient } from "./api-client";
import { retryWithBackoff } from "./error-handler";

// ============================================
// TYPES
// ============================================

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  message: string;
  context?: {
    currentSchedule?: any;
    preferences?: any;
    semester?: string;
    university?: string;
  };
  history?: ChatMessage[];
}

export interface ChatResponse {
  message: string;
  suggestedSchedule?: any;
  actions?: any[];
}

export interface ScheduleOptimizationRequest {
  courseCodes: string[];
  semester: string;
  university?: string;
  constraints?: {
    preferredDays?: string[];
    earliestStartTime?: string;
    latestEndTime?: string;
    minProfessorRating?: number;
    avoidGaps?: boolean;
  };
}

export interface OptimizedSchedule {
  id: string;
  sections: any[];
  score: number;
  conflicts: any[];
  reasoning: string;
  metadata?: {
    avgProfessorRating?: number;
    totalCredits?: number;
    daysPerWeek?: number;
    gapHours?: number;
  };
}

export interface ScheduleOptimizationResponse {
  schedules: OptimizedSchedule[];
  count: number;
  courses: Record<string, { id: string; name: string }>;
  total_sections: number;
}

export interface ProfessorDetails {
  id: string;
  name: string;
  department?: string;
  university?: string;
  average_rating?: number;
  average_difficulty?: number;
  review_count?: number;
  grade_letter?: string;
  composite_score?: number;
  reviews?: any[];
}

export interface CourseSearchRequest {
  query?: string;
  department?: string;
  semester?: string;
  modality?: string;
  timeSlot?: string;
  limit?: number;
  offset?: number;
}

export interface CourseWithSections {
  id: string;
  course_code: string;
  title: string;
  description?: string;
  department?: string;
  credits?: number;
  sections?: any[];
}

export interface CourseSearchResponse {
  courses: CourseWithSections[];
  count: number;
  searchType: 'exact' | 'semantic';
}

export interface TimeConflict {
  type: string;
  section1: string;
  section2: string;
  message: string;
}

export interface ScheduleValidationRequest {
  scheduleId: string;
  sectionId: string;
  action: 'add' | 'remove';
}

export interface ScheduleValidationResponse {
  valid: boolean;
  conflicts: TimeConflict[];
  warnings: string[];
  suggestions: any[];
}

export interface AnalyticsEvent {
  name: string;
  properties?: Record<string, any>;
  timestamp?: string;
}

// ============================================
// COURSE ENDPOINTS
// ============================================

/**
 * Search courses via backend API
 * (Alternative to direct Supabase queries)
 */
export async function searchCoursesAPI(params: {
  query?: string;
  department?: string;
  semester?: string;
  modality?: string;
  limit?: number;
}) {
  return retryWithBackoff(
    async () => {
      const response = await apiClient.get("/api/courses", { ...params } as any);
      return response.data || response; // Fallback for backward compatibility if needed
    },
    3
  );
}

// ============================================
// CHAT ENDPOINTS
// ============================================

/**
 * Send message to AI chat assistant
 */
export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  return apiClient.post("/api/chat/message", request);
}

/**
 * Get chat history
 */
export async function getChatHistory(userId: string) {
  return apiClient.get(`/api/chat/history/${userId}`);
}

// ============================================
// SCHEDULE OPTIMIZATION ENDPOINTS
// ============================================

/**
 * Request schedule optimization from AI
 */
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

/**
 * Get optimization history
 */
export async function getOptimizationHistory(userId: string) {
  return apiClient.get(`/api/schedule/optimize/history/${userId}`);
}

/**
 * Validate schedule action (add/remove section)
 */
export async function validateScheduleAction(
  request: ScheduleValidationRequest
): Promise<ScheduleValidationResponse> {
  return apiClient.post("/api/schedule/validate", request);
}

// ============================================
// PROFESSOR ENDPOINTS
// ============================================

/**
 * Get professor details by name
 */
export async function getProfessorByNameAPI(
  name: string,
  university?: string
): Promise<ProfessorDetails> {
  const params = new URLSearchParams({ name });
  if (university) params.append("university", university);

  return retryWithBackoff(
    async () => {
      const response = await apiClient.get(`/api/professor/${name}?${params.toString()}`);
      return response.data || response;
    },
    2
  );
}

/**
 * Get professor details by ID
 */
export async function getProfessorByIdAPI(
  id: string
): Promise<ProfessorDetails> {
  return retryWithBackoff(
    () => apiClient.get(`/api/professor/id/${id}`),
    2
  );
}

/**
 * Compare multiple professors
 */
export async function compareProfessors(professorIds: string[]) {
  // Note: The backend expects professor names, but the frontend might be passing IDs or names.
  // Assuming names for now based on backend implementation.
  // If IDs, we might need to fetch names first or update backend.
  // The backend endpoint is /api/professor/compare and expects professor_names.
  
  // If the input is actually names:
  const response = await apiClient.post("/api/professor/compare", { 
    professor_names: professorIds, // Mapping IDs to names param if they are names
    university: "Baruch College" // Default for now
  });
  return response.data || response;
}

// ============================================
// ADMIN ENDPOINTS
// ============================================

/**
 * Seed database with sample data
 */
export async function seedDatabase() {
  return apiClient.post("/api/admin/seed");
}

/**
 * Clear database
 */
export async function clearDatabase() {
  return apiClient.post("/api/admin/clear");
}

/**
 * Get database stats
 */
export async function getDatabaseStats() {
  return apiClient.get("/api/admin/stats");
}

// ============================================
// ANALYTICS ENDPOINTS
// ============================================

/**
 * Track user event
 */
export async function trackEvent(event: {
  name: string;
  properties?: Record<string, any>;
}) {
  return apiClient.post("/api/analytics/track", event);
}

/**
 * Get user analytics
 */
export async function getUserAnalytics(userId: string) {
  return apiClient.get(`/api/analytics/user/${userId}`);
}

// ============================================
// HEALTH CHECK
// ============================================

/**
 * Check API health
 */
export async function healthCheck() {
  return apiClient.get("/api/health");
}

/**
 * Check if backend is available
 */
export async function isBackendAvailable(): Promise<boolean> {
  try {
    await healthCheck();
    return true;
  } catch {
    return false;
  }
}
