/**
 * Error Handling Middleware
 * 
 * Centralized error handling with user-friendly messages and retry logic
 * Supports backend error codes and suggestions
 */

import { APIClientError } from "./api-client";
import { ErrorCode } from "@/types/api-responses";

export interface ErrorHandlerOptions {
  showToast?: boolean;
  logToConsole?: boolean;
  retryable?: boolean;
  maxRetries?: number;
  retryDelay?: number;
}

/**
 * Map error codes to user-friendly messages
 * Includes backend-specific error codes
 */
const ERROR_MESSAGES: Record<string, string> = {
  // Network errors
  NETWORK_ERROR: "Unable to connect to the server. Please check your internet connection.",
  TIMEOUT_ERROR: "The request took too long. Please try again.",
  TIMEOUT: "The request took too long. Please try again.",

  // HTTP errors
  HTTP_400: "Invalid request. Please check your input and try again.",
  HTTP_401: "You need to be logged in to perform this action.",
  HTTP_403: "You don't have permission to perform this action.",
  HTTP_404: "The requested resource was not found.",
  HTTP_409: "This action conflicts with existing data.",
  HTTP_422: "The data provided is invalid. Please check and try again.",
  HTTP_429: "Too many requests. Please wait a moment and try again.",
  HTTP_500: "Server error. Please try again later.",
  HTTP_502: "Server is temporarily unavailable. Please try again later.",
  HTTP_503: "Service is temporarily unavailable. Please try again later.",

  // Backend-specific error codes
  [ErrorCode.DATA_NOT_FOUND]: "The requested data could not be found.",
  [ErrorCode.DATA_STALE]: "The data is outdated. Refresh to get the latest information.",
  [ErrorCode.CIRCUIT_BREAKER_OPEN]: "The service is temporarily unavailable. Please try again later.",
  [ErrorCode.SCRAPING_ERROR]: "Unable to fetch external data. Please try again later.",
  [ErrorCode.EXTERNAL_SERVICE_ERROR]: "An external service is unavailable. Please try again later.",
  [ErrorCode.DATABASE_ERROR]: "A database error occurred. Please try again.",
  [ErrorCode.RATE_LIMIT_ERROR]: "Too many requests. Please wait a moment and try again.",
  [ErrorCode.VALIDATION_ERROR]: "The provided data is invalid. Please check your input.",
  [ErrorCode.POPULATION_ERROR]: "Unable to load data. Please try again.",
  [ErrorCode.PARTIAL_POPULATION]: "Some data could not be loaded. Results may be incomplete.",
  [ErrorCode.INTERNAL_ERROR]: "An unexpected error occurred. Please try again.",

  // Application errors
  AUTH_ERROR: "Authentication failed. Please log in again.",
  CONFLICT_ERROR: "This action conflicts with existing data.",
  NOT_FOUND_ERROR: "The requested item was not found.",

  // Default
  UNKNOWN_ERROR: "Something went wrong. Please try again.",
};

/**
 * Get user-friendly error message
 */
export function getUserFriendlyMessage(error: Error | APIClientError): string {
  if (error instanceof APIClientError) {
    // Check if we have a specific message for this error code
    if (error.code && ERROR_MESSAGES[error.code]) {
      return ERROR_MESSAGES[error.code];
    }

    // Check if we have a message for the HTTP status
    if (error.status && ERROR_MESSAGES[`HTTP_${error.status}`]) {
      return ERROR_MESSAGES[`HTTP_${error.status}`];
    }

    // Use the error message from the API if available
    if (error.message) {
      return error.message;
    }
  }

  // Check for network errors
  if (error.message.includes("fetch") || error.message.includes("network")) {
    return ERROR_MESSAGES.NETWORK_ERROR;
  }

  // Default message
  return ERROR_MESSAGES.UNKNOWN_ERROR;
}

/**
 * Get suggestions from an APIClientError
 */
export function getErrorSuggestions(error: Error | APIClientError): string[] {
  if (error instanceof APIClientError && error.suggestions) {
    return error.suggestions;
  }
  return [];
}

/**
 * Get retry-after time from an APIClientError (in seconds)
 */
export function getRetryAfterTime(error: Error | APIClientError): number | undefined {
  if (error instanceof APIClientError && error.retryAfter) {
    return error.retryAfter;
  }
  return undefined;
}

/**
 * Check if an error is retryable
 */
export function isRetryableError(error: Error | APIClientError): boolean {
  if (error instanceof APIClientError) {
    // Check for specific retryable error codes
    const retryableCodes = [
      ErrorCode.CIRCUIT_BREAKER_OPEN,
      ErrorCode.DATABASE_ERROR,
      ErrorCode.EXTERNAL_SERVICE_ERROR,
      ErrorCode.SCRAPING_ERROR,
      ErrorCode.RATE_LIMIT_ERROR,
    ];
    
    if (error.code && retryableCodes.includes(error.code as ErrorCode)) {
      return true;
    }
    
    // Retry on network errors and 5xx server errors
    if (!error.status) return true; // Network error
    if (error.status >= 500 && error.status < 600) return true;
    if (error.status === 429) return true; // Rate limit
  }

  // Retry on network errors
  if (error.message.includes("fetch") || error.message.includes("network")) {
    return true;
  }

  return false;
}

/**
 * Calculate retry delay with exponential backoff
 * Respects Retry-After header if present
 */
export function getRetryDelay(
  attempt: number, 
  baseDelay: number = 1000,
  retryAfter?: number
): number {
  // If server specified a retry-after, use that
  if (retryAfter !== undefined && retryAfter > 0) {
    return retryAfter * 1000; // Convert seconds to milliseconds
  }
  
  return Math.min(baseDelay * Math.pow(2, attempt), 10000); // Max 10 seconds
}

/**
 * Retry a function with exponential backoff
 * Respects Retry-After header from rate limiting
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: Error | APIClientError | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error("Unknown error");

      // Don't retry if error is not retryable
      if (!isRetryableError(lastError)) {
        throw lastError;
      }

      // Don't retry if this was the last attempt
      if (attempt === maxRetries) {
        throw lastError;
      }

      // Get delay, respecting Retry-After header if present
      const retryAfter = lastError instanceof APIClientError ? lastError.retryAfter : undefined;
      const delay = getRetryDelay(attempt, baseDelay, retryAfter);
      console.log(`Retry attempt ${attempt + 1}/${maxRetries} after ${delay}ms`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

/**
 * Handle error with logging and user feedback
 */
export function handleError(
  error: Error | APIClientError,
  options: ErrorHandlerOptions = {}
): string {
  const {
    logToConsole = true,
  } = options;

  // Log to console
  if (logToConsole) {
    console.error("Error occurred:", error);

    if (error instanceof APIClientError) {
      console.error("Error details:", {
        code: error.code,
        status: error.status,
        details: error.details,
      });
    }
  }

  // Get user-friendly message
  const message = getUserFriendlyMessage(error);

  return message;
}

/**
 * Parse API error response
 */
export function parseAPIError(error: any): APIClientError {
  if (error instanceof APIClientError) {
    return error;
  }

  if (error instanceof Error) {
    return new APIClientError(error.message);
  }

  if (typeof error === "string") {
    return new APIClientError(error);
  }

  if (error && typeof error === "object") {
    const message = error.message || error.detail || error.error || "Unknown error";
    const code = error.code || error.error_code;
    const status = error.status || error.statusCode;

    return new APIClientError(message, code, status, error);
  }

  return new APIClientError("Unknown error");
}

/**
 * Create error handler for async operations
 */
export function createErrorHandler(options: ErrorHandlerOptions = {}) {
  return (error: any) => {
    const apiError = parseAPIError(error);
    return handleError(apiError, options);
  };
}

export enum ErrorCategory {
  NETWORK = 'NETWORK',
  AUTH = 'AUTH',
  VALIDATION = 'VALIDATION',
  NOT_FOUND = 'NOT_FOUND',
  SERVER = 'SERVER',
  UNKNOWN = 'UNKNOWN',
}

export function categorizeError(error: Error | APIClientError): ErrorCategory {
  if (error instanceof APIClientError) {
    if (!error.status) return ErrorCategory.NETWORK;
    if (error.status === 401 || error.status === 403) return ErrorCategory.AUTH;
    if (error.status === 404) return ErrorCategory.NOT_FOUND;
    if (error.status >= 400 && error.status < 500) return ErrorCategory.VALIDATION;
    if (error.status >= 500) return ErrorCategory.SERVER;
  }

  if (error.message.toLowerCase().includes('network') || error.message.toLowerCase().includes('fetch')) {
    return ErrorCategory.NETWORK;
  }

  return ErrorCategory.UNKNOWN;
}
