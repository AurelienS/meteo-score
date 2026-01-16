/**
 * API client for MétéoScore backend.
 * Provides typed fetch wrapper with error handling.
 */

import type { ApiError, HealthResponse, Site, Parameter, PaginatedResponse, SiteAccuracyResponse } from './types';

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

/**
 * Fetch all available sites.
 * @returns Promise resolving to array of sites
 */
export async function fetchSites(): Promise<Site[]> {
  const response = await fetchApi<PaginatedResponse<Site>>('/api/v1/sites/');
  return response.data;
}

/**
 * Fetch all available weather parameters.
 * @returns Promise resolving to array of parameters
 */
export async function fetchParameters(): Promise<Parameter[]> {
  const response = await fetchApi<PaginatedResponse<Parameter>>('/api/v1/parameters/');
  return response.data;
}

/**
 * Fetch site accuracy comparison across all models.
 * @param siteId - Site identifier (must be positive integer)
 * @param parameterId - Weather parameter identifier (must be positive integer)
 * @param horizon - Forecast horizon in hours (must be positive integer)
 * @returns Promise resolving to accuracy response with model metrics
 * @throws ApiRequestError if parameters are invalid
 */
export async function fetchSiteAccuracy(
  siteId: number,
  parameterId: number,
  horizon: number
): Promise<SiteAccuracyResponse> {
  if (!Number.isInteger(siteId) || siteId <= 0) {
    throw new ApiRequestError('Invalid siteId: must be a positive integer', 400, 'ValidationError');
  }
  if (!Number.isInteger(parameterId) || parameterId <= 0) {
    throw new ApiRequestError('Invalid parameterId: must be a positive integer', 400, 'ValidationError');
  }
  if (!Number.isInteger(horizon) || horizon <= 0) {
    throw new ApiRequestError('Invalid horizon: must be a positive integer', 400, 'ValidationError');
  }

  return fetchApi<SiteAccuracyResponse>(
    `/api/v1/analysis/sites/${siteId}/accuracy?parameterId=${parameterId}&horizon=${horizon}`
  );
}
