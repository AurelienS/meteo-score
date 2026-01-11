/**
 * TypeScript type definitions for MétéoScore frontend.
 * All interfaces match the camelCase JSON responses from the backend API.
 */

/** Site entity representing a weather observation location */
export interface Site {
  id: number;
  name: string;
  lat: number;
  lon: number;
  alt: number;
  createdAt: string;
}

/** Weather forecast model */
export interface Model {
  id: number;
  name: string;
  source: string;
  createdAt: string;
}

/** Weather parameter being measured */
export interface Parameter {
  id: number;
  name: string;
  unit: string;
  createdAt: string;
}

/** Deviation between forecast and observation */
export interface Deviation {
  siteId: number;
  modelId: number;
  parameterId: number;
  timestamp: string;
  forecastValue: number;
  observedValue: number;
  deviation: number;
}

/** Pagination metadata */
export interface MetaResponse {
  total: number;
  page: number;
  perPage: number;
}

/** Generic paginated API response */
export interface PaginatedResponse<T> {
  data: T[];
  meta: MetaResponse;
}

/** API error response */
export interface ApiError {
  error: string;
  detail: string;
  statusCode: number;
}

/** Health check response */
export interface HealthResponse {
  status: string;
  database?: string;
}
