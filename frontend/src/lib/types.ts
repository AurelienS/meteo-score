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

/** Confidence level for accuracy metrics */
export type ConfidenceLevel = 'insufficient' | 'preliminary' | 'validated';

/** Accuracy metrics for a single forecast model */
export interface ModelAccuracyMetrics {
  modelId: number;
  modelName: string;
  mae: number;
  bias: number;
  stdDev: number;
  sampleSize: number;
  confidenceLevel: ConfidenceLevel;
  confidenceMessage: string;
}

/** Response for site accuracy comparison across models */
export interface SiteAccuracyResponse {
  siteId: number;
  siteName: string;
  parameterId: number;
  parameterName: string;
  horizon: number;
  models: ModelAccuracyMetrics[];
}

/** Single data point in time series accuracy data */
export interface TimeSeriesDataPoint {
  bucket: string;
  mae: number;
  bias: number;
  sampleSize: number;
  avgForecast?: number | null;
  avgObserved?: number | null;
}

/** Response for time series accuracy data */
export interface TimeSeriesAccuracyResponse {
  siteId: number;
  siteName: string;
  modelId: number;
  modelName: string;
  parameterId: number;
  parameterName: string;
  granularity: string;
  dataPoints: TimeSeriesDataPoint[];
}

// Admin API types

/** Execution record for a scheduled job */
export interface ExecutionRecord {
  startTime: string;
  endTime: string;
  durationSeconds: number;
  status: 'success' | 'partial' | 'failed';
  recordsCollected: number;
  errors?: string[];
}

/** Admin scheduler status response */
export interface AdminSchedulerStatusResponse {
  running: boolean;
  forecastHistory: ExecutionRecord[];
  observationHistory: ExecutionRecord[];
}

/** Scheduled job information */
export interface ScheduledJobInfo {
  id: string;
  name: string;
  nextRunTime: string | null;
  trigger: string;
}

/** Scheduler jobs response */
export interface SchedulerJobsResponse {
  jobs: ScheduledJobInfo[];
}

/** Toggle scheduler response */
export interface ToggleResponse {
  running: boolean;
  message: string;
}

/** Manual collection response */
export interface CollectionResponse {
  status: string;
  recordsCollected: number;
  recordsPersisted?: number;
  durationSeconds: number;
  errors?: string[];
}

/** Data statistics response */
export interface DataStatsResponse {
  totalForecasts: number;
  totalObservations: number;
  totalDeviations: number;
  totalPairs: number;
  totalSites: number;
}

/** Single forecast preview record */
export interface ForecastPreviewRecord {
  id: number;
  site: string;
  parameter: string;
  valid_time: string;
  value: number;
  created_at: string;
}

/** Single observation preview record */
export interface ObservationPreviewRecord {
  id: number;
  site: string;
  parameter: string;
  observation_time: string;
  value: number;
  created_at: string;
}

/** Data preview response */
export interface DataPreviewResponse {
  forecasts: Record<string, ForecastPreviewRecord[]>;
  observations: Record<string, ObservationPreviewRecord[]>;
}
