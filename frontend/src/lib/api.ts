/**
 * API client for MétéoScore backend.
 * Provides typed fetch wrapper with error handling.
 */

import type { ApiError, HealthResponse } from './types';

/** Base API URL from environment or default to local backend */
const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Custom error class for API errors.
 */
export class ApiRequestError extends Error {
  public readonly statusCode: number;
  public readonly errorType: string;

  constructor(message: string, statusCode: number, errorType: string = 'ApiError') {
    super(message);
    this.name = 'ApiRequestError';
    this.statusCode = statusCode;
    this.errorType = errorType;
  }
}

/**
 * Generic fetch wrapper with type safety and error handling.
 *
 * @param endpoint - API endpoint path (e.g., '/api/sites/')
 * @returns Promise resolving to typed response data
 * @throws ApiRequestError if request fails
 */
export async function fetchApi<T>(endpoint: string): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  const response = await fetch(url);

  if (!response.ok) {
    let errorMessage = 'API request failed';
    let errorType = 'ApiError';

    try {
      const errorData: ApiError = await response.json();
      errorMessage = errorData.detail || errorMessage;
      errorType = errorData.error || errorType;
    } catch {
      // Response wasn't JSON, use default message
    }

    throw new ApiRequestError(errorMessage, response.status, errorType);
  }

  return response.json() as Promise<T>;
}

/**
 * Check backend health status.
 */
export async function checkHealth(): Promise<HealthResponse> {
  return fetchApi<HealthResponse>('/api/health');
}
