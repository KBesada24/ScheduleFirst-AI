/**
 * API Client Utility
 * 
 * Centralized API client with fetch wrapper, interceptors, and error handling
 * Supports structured error responses and automatic warning toasts
 */

import { supabase } from "../../supabase/supabase";
import { 
  isErrorResponse, 
  isSuccessResponse, 
  getWarnings, 
  isDataDegraded,
  isDataStale,
  type ErrorResponse,
  type ApiResponse,
  ErrorCode,
} from "@/types/api-responses";
import { createWarningsToasts, createDataQualityToast } from "./notifications";

// API base URL - defaults to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Timeout configuration
const REQUEST_TIMEOUT = 30000; // 30 seconds
const AI_REQUEST_TIMEOUT = 60000; // 60 seconds for AI operations

// Warning toast callback - set by consuming code to integrate with toast system
let showWarningToast: ((toast: ReturnType<typeof createWarningsToasts>[0]) => void) | null = null;

/**
 * Register a callback to show warning toasts
 * Call this once during app initialization with your toast function
 */
export function registerWarningToastHandler(
  handler: (toast: ReturnType<typeof createWarningsToasts>[0]) => void
) {
  showWarningToast = handler;
}

// Fetch wrapper with timeout
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

export interface APIError {
  message: string;
  code?: string;
  status?: number;
  details?: Record<string, unknown>;
  suggestions?: string[];
  retryAfter?: number;
}

export class APIClientError extends Error {
  code?: string;
  status?: number;
  details?: Record<string, unknown>;
  suggestions?: string[];
  retryAfter?: number;

  constructor(
    message: string, 
    code?: string, 
    status?: number, 
    details?: Record<string, unknown>,
    suggestions?: string[],
    retryAfter?: number
  ) {
    super(message);
    this.name = "APIClientError";
    this.code = code;
    this.status = status;
    this.details = details;
    this.suggestions = suggestions;
    this.retryAfter = retryAfter;
  }
  
  /**
   * Create APIClientError from backend ErrorResponse
   */
  static fromErrorResponse(response: ErrorResponse, status: number, retryAfter?: number): APIClientError {
    return new APIClientError(
      response.user_message || response.message,
      response.code,
      status,
      response.details,
      response.suggestions,
      retryAfter
    );
  }
}

/**
 * Request interceptor - adds auth token and common headers
 */
async function requestInterceptor(
  url: string,
  options: RequestInit = {}
): Promise<[string, RequestInit]> {
  // Get auth token from Supabase
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = new Headers(options.headers);

  // Add auth token if available
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }

  // Add common headers
  headers.set("Content-Type", "application/json");
  headers.set("Accept", "application/json");

  return [
    url,
    {
      ...options,
      headers,
      credentials: "include", // Include cookies for CORS
    },
  ];
}

/**
 * Response interceptor - handles errors, parses responses, and shows warnings
 */
async function responseInterceptor<T = unknown>(response: Response): Promise<T> {
  // Extract Retry-After header if present
  const retryAfterHeader = response.headers.get("Retry-After");
  const retryAfter = retryAfterHeader ? parseInt(retryAfterHeader, 10) : undefined;
  
  // Parse JSON response
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    // If response is not JSON
    if (!response.ok) {
      throw new APIClientError(
        `HTTP ${response.status}: ${response.statusText}`,
        `HTTP_${response.status}`,
        response.status
      );
    }
    return null;
  }
  
  // Check if response is a structured error from our backend
  if (isErrorResponse(data)) {
    throw APIClientError.fromErrorResponse(data, response.status, retryAfter);
  }
  
  // Check if response is not ok (legacy error format)
  if (!response.ok) {
    const errorMessage = typeof data === 'object' && data !== null && 'message' in data
      ? (data as { message: string }).message
      : `HTTP ${response.status}: ${response.statusText}`;
      
    throw new APIClientError(
      errorMessage,
      `HTTP_${response.status}`,
      response.status,
      typeof data === 'object' ? data as Record<string, unknown> : undefined
    );
  }
  
  // Handle successful responses - show warnings automatically
  if (showWarningToast) {
    // Show warnings from response
    const warnings = getWarnings(data);
    if (warnings.length > 0) {
      const toasts = createWarningsToasts(warnings);
      toasts.forEach(toast => showWarningToast?.(toast));
    }
    
    // Show data quality warnings
    if (isSuccessResponse(data)) {
      if (isDataDegraded(data) || isDataStale(data)) {
        const qualityToast = createDataQualityToast(
          data.metadata?.data_quality || "full",
          isDataStale(data)
        );
        if (qualityToast) {
          showWarningToast(qualityToast);
        }
      }
    }
  }

  return data as T;
}

/**
 * Main API client class
 */
class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  /**
   * Make a GET request
   */
  async get<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const [interceptedUrl, interceptedOptions] = await requestInterceptor(url, {
      ...options,
      method: "GET",
    });

    const response = await fetchWithTimeout(interceptedUrl, interceptedOptions);
    return responseInterceptor(response);
  }

  /**
   * Make a POST request
   */
  async post<T = any>(
    endpoint: string,
    data?: any,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const [interceptedUrl, interceptedOptions] = await requestInterceptor(url, {
      ...options,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });

    const response = await fetchWithTimeout(interceptedUrl, interceptedOptions, AI_REQUEST_TIMEOUT);
    return responseInterceptor(response);
  }

  /**
   * Make a PUT request
   */
  async put<T = any>(
    endpoint: string,
    data?: any,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const [interceptedUrl, interceptedOptions] = await requestInterceptor(url, {
      ...options,
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });

    const response = await fetchWithTimeout(interceptedUrl, interceptedOptions);
    return responseInterceptor(response);
  }

  /**
   * Make a DELETE request
   */
  async delete<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const [interceptedUrl, interceptedOptions] = await requestInterceptor(url, {
      ...options,
      method: "DELETE",
    });

    const response = await fetchWithTimeout(interceptedUrl, interceptedOptions);
    return responseInterceptor(response);
  }

  /**
   * Make a PATCH request
   */
  async patch<T = any>(
    endpoint: string,
    data?: any,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const [interceptedUrl, interceptedOptions] = await requestInterceptor(url, {
      ...options,
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    });

    const response = await fetchWithTimeout(interceptedUrl, interceptedOptions);
    return responseInterceptor(response);
  }
}

// Export singleton instance
export const apiClient = new APIClient();

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

// Export class for testing or custom instances
export { APIClient };
