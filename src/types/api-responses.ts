/**
 * API Response Types
 * 
 * TypeScript types matching the backend API response models
 */

/**
 * Data quality indicators from backend
 */
export enum DataQuality {
  FULL = "full",           // All requested data available and fresh
  PARTIAL = "partial",     // Some data missing or from fallback sources
  DEGRADED = "degraded",   // Significant data missing, using cached/stale data
  MINIMAL = "minimal",     // Only basic data available
}

/**
 * Backend error codes
 */
export enum ErrorCode {
  // Data errors
  DATA_NOT_FOUND = "DATA_NOT_FOUND",
  DATA_STALE = "DATA_STALE",
  
  // Service errors
  CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN",
  SCRAPING_ERROR = "SCRAPING_ERROR",
  EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR",
  DATABASE_ERROR = "DATABASE_ERROR",
  
  // Rate limiting
  RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR",
  
  // Validation
  VALIDATION_ERROR = "VALIDATION_ERROR",
  
  // Population
  POPULATION_ERROR = "POPULATION_ERROR",
  PARTIAL_POPULATION = "PARTIAL_POPULATION",
  
  // Generic
  INTERNAL_ERROR = "INTERNAL_ERROR",
}

/**
 * Response metadata from backend
 */
export interface ResponseMetadata {
  source: string;
  last_updated?: string;
  is_fresh: boolean;
  auto_populated: boolean;
  count?: number;
  data_quality: DataQuality;
}

/**
 * Successful API response wrapper
 */
export interface ApiResponse<T = unknown> {
  success: true;
  data: T;
  metadata: ResponseMetadata;
  warnings: string[];
}

/**
 * Error response from backend
 */
export interface ErrorResponse {
  success: false;
  error: true;
  code: ErrorCode | string;
  message: string;
  user_message: string;
  details?: Record<string, unknown>;
  suggestions: string[];
}

/**
 * Union type for API responses
 */
export type ApiResult<T = unknown> = ApiResponse<T> | ErrorResponse;

/**
 * Type guard for checking if response is an error
 */
export function isErrorResponse(response: unknown): response is ErrorResponse {
  return (
    typeof response === "object" &&
    response !== null &&
    "success" in response &&
    (response as { success: boolean }).success === false &&
    "error" in response &&
    (response as { error: boolean }).error === true
  );
}

/**
 * Type guard for checking if response is successful
 */
export function isSuccessResponse<T>(response: unknown): response is ApiResponse<T> {
  return (
    typeof response === "object" &&
    response !== null &&
    "success" in response &&
    (response as { success: boolean }).success === true &&
    "data" in response
  );
}

/**
 * Extract warnings from a response (works for both success and error responses)
 */
export function getWarnings(response: unknown): string[] {
  if (typeof response !== "object" || response === null) {
    return [];
  }
  
  if ("warnings" in response && Array.isArray((response as { warnings: unknown }).warnings)) {
    return (response as { warnings: string[] }).warnings;
  }
  
  return [];
}

/**
 * Extract suggestions from an error response
 */
export function getSuggestions(response: unknown): string[] {
  if (!isErrorResponse(response)) {
    return [];
  }
  
  return response.suggestions || [];
}

/**
 * Check if data quality indicates degraded data
 */
export function isDataDegraded(response: unknown): boolean {
  if (!isSuccessResponse(response)) {
    return false;
  }
  
  const quality = response.metadata?.data_quality;
  return quality === DataQuality.DEGRADED || quality === DataQuality.MINIMAL;
}

/**
 * Check if data is stale based on response
 */
export function isDataStale(response: unknown): boolean {
  if (!isSuccessResponse(response)) {
    return false;
  }
  
  return response.metadata?.is_fresh === false;
}
