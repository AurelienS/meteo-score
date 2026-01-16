/**
 * API client for MétéoScore backend.
 * Provides typed fetch wrapper with error handling, timeout, and network error detection.
 */

import type { ApiError, HealthResponse, Site, Parameter, PaginatedResponse, SiteAccuracyResponse, TimeSeriesAccuracyResponse } from './types';

/** Base API URL from environment or default to local backend */
const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/** Default request timeout in milliseconds (30 seconds) */
const DEFAULT_TIMEOUT_MS = 30000;

/**
 * Custom error class for API errors (HTTP error responses).
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
 * Error class for network failures (offline, DNS, CORS, etc.).
 */
export class NetworkError extends Error {
  constructor(message: string = 'Network error - please check your connection') {
    super(message);
    this.name = 'NetworkError';
  }
}

/**
 * Error class for request timeouts.
 */
export class TimeoutError extends Error {
  constructor(message: string = 'Request timed out - please try again') {
    super(message);
    this.name = 'TimeoutError';
  }
}

/**
 * Fetch with timeout support using AbortController.
 * @param url - Full URL to fetch
 * @param timeoutMs - Timeout in milliseconds (default: 30 seconds)
 * @returns Promise resolving to Response
 * @throws TimeoutError if request times out
 * @throws NetworkError if network fails
 */
async function fetchWithTimeout(url: string, timeoutMs: number = DEFAULT_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new TimeoutError();
    }
    // Network failure (offline, DNS, CORS, etc.)
    throw new NetworkError();
  }
}

/**
 * Generic fetch wrapper with type safety, error handling, and timeout.
 *
 * @param endpoint - API endpoint path (e.g., '/api/sites/')
 * @returns Promise resolving to typed response data
 * @throws ApiRequestError if HTTP error response
 * @throws NetworkError if network fails
 * @throws TimeoutError if request times out
 */
export async function fetchApi<T>(endpoint: string): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  const response = await fetchWithTimeout(url);

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

/** Valid granularity values for time series API */
const VALID_GRANULARITIES = ['daily', 'weekly', 'monthly'] as const;
type Granularity = typeof VALID_GRANULARITIES[number];

/**
 * Fetch time series accuracy data for a model at a site.
 * @param siteId - Site identifier (must be positive integer)
 * @param modelId - Model identifier (must be positive integer)
 * @param parameterId - Weather parameter identifier (must be positive integer)
 * @param granularity - Time granularity: "daily" | "weekly" | "monthly" (default: "daily")
 * @returns Promise resolving to time series accuracy data
 * @throws ApiRequestError if parameters are invalid
 */
export async function fetchAccuracyTimeSeries(
  siteId: number,
  modelId: number,
  parameterId: number,
  granularity: Granularity = 'daily'
): Promise<TimeSeriesAccuracyResponse> {
  if (!Number.isInteger(siteId) || siteId <= 0) {
    throw new ApiRequestError('Invalid siteId: must be a positive integer', 400, 'ValidationError');
  }
  if (!Number.isInteger(modelId) || modelId <= 0) {
    throw new ApiRequestError('Invalid modelId: must be a positive integer', 400, 'ValidationError');
  }
  if (!Number.isInteger(parameterId) || parameterId <= 0) {
    throw new ApiRequestError('Invalid parameterId: must be a positive integer', 400, 'ValidationError');
  }
  if (!VALID_GRANULARITIES.includes(granularity)) {
    throw new ApiRequestError(
      `Invalid granularity: must be one of ${VALID_GRANULARITIES.join(', ')}`,
      400,
      'ValidationError'
    );
  }

  return fetchApi<TimeSeriesAccuracyResponse>(
    `/api/v1/analysis/sites/${siteId}/accuracy/timeseries?modelId=${modelId}&parameterId=${parameterId}&granularity=${granularity}`
  );
}
