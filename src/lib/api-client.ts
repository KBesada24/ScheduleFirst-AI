/**
 * API Client Utility
 * 
 * Centralized API client with fetch wrapper, interceptors, and error handling
 */

import { supabase } from "../../supabase/supabase";

// API base URL - defaults to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface APIError {
  message: string;
  code?: string;
  status?: number;
  details?: any;
}

export class APIClientError extends Error {
  code?: string;
  status?: number;
  details?: any;

  constructor(message: string, code?: string, status?: number, details?: any) {
    super(message);
    this.name = "APIClientError";
    this.code = code;
    this.status = status;
    this.details = details;
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
 * Response interceptor - handles errors and parses responses
 */
async function responseInterceptor(response: Response): Promise<any> {
  // Check if response is ok
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    let errorDetails: any = null;

    try {
      const errorData = await response.json();
      errorMessage = errorData.message || errorData.detail || errorMessage;
      errorDetails = errorData;
    } catch {
      // If response is not JSON, use status text
    }

    throw new APIClientError(
      errorMessage,
      `HTTP_${response.status}`,
      response.status,
      errorDetails
    );
  }

  // Parse JSON response
  try {
    return await response.json();
  } catch {
    // If response is not JSON, return null
    return null;
  }
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

    const response = await fetch(interceptedUrl, interceptedOptions);
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

    const response = await fetch(interceptedUrl, interceptedOptions);
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

    const response = await fetch(interceptedUrl, interceptedOptions);
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

    const response = await fetch(interceptedUrl, interceptedOptions);
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

    const response = await fetch(interceptedUrl, interceptedOptions);
    return responseInterceptor(response);
  }
}

// Export singleton instance
export const apiClient = new APIClient();

// Export class for testing or custom instances
export { APIClient };
