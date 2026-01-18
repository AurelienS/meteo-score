/**
 * Admin Dashboard page component.
 *
 * Provides admin interface for:
 * - Viewing scheduler status and execution history
 * - Toggling scheduler on/off
 * - Triggering manual data collection
 *
 * Requires Basic Auth (browser will prompt automatically).
 */

import { createSignal, createEffect, onMount, onCleanup, For, Show } from 'solid-js';
import type { JSX } from 'solid-js';
import type {
  AdminSchedulerStatusResponse,
  SchedulerJobsResponse,
  ExecutionRecord,
  ScheduledJobInfo,
  DataStatsResponse,
  DataPreviewResponse,
} from '../lib/types';
import {
  fetchAdminSchedulerStatus,
  fetchAdminSchedulerJobs,
  toggleScheduler,
  triggerForecastCollection,
  triggerObservationCollection,
  fetchAdminStats,
  fetchAdminDataPreview,
  ApiRequestError,
  NetworkError,
  TimeoutError,
  setAdminCredentials,
  hasAdminCredentials,
  clearAdminCredentials,
} from '../lib/api';
import { useI18n } from '../contexts/I18nContext';

/** Auto-refresh interval in milliseconds (30 seconds) */
const AUTO_REFRESH_INTERVAL = 30000;

/**
 * Format ISO date string to readable format (24h).
 */
function formatDateTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * Format time only (24h).
 */
function formatTime(date: Date): string {
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * Format duration in seconds to readable format.
 */
function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}m ${secs.toFixed(0)}s`;
}

/**
 * Status badge component.
 */
function StatusBadge(props: { status: string }): JSX.Element {
  const badgeClass = () => {
    switch (props.status) {
      case 'success':
        return 'bg-status-success-bg text-status-success-text border border-status-success-border';
      case 'partial':
        return 'bg-status-warning-bg text-status-warning-text border border-status-warning-border';
      case 'failed':
        return 'bg-status-error-bg text-status-error-text border border-status-error-border';
      default:
        return 'bg-theme-bg-tertiary text-theme-text-secondary';
    }
  };

  return (
    <span class={`px-2 py-1 rounded-full text-xs font-medium ${badgeClass()}`}>
      {props.status}
    </span>
  );
}

/**
 * Execution history table component.
 */
function ExecutionHistoryTable(props: {
  title: string;
  history: ExecutionRecord[];
  noHistoryText: string;
  timeLabel: string;
  statusLabel: string;
  recordsLabel: string;
  durationLabel: string;
}): JSX.Element {
  return (
    <div
      class="rounded-lg shadow p-4 transition-colors"
      style={{
        "background-color": "var(--color-surface)",
        "border": "1px solid var(--color-border)",
      }}
    >
      <h3
        class="text-lg font-semibold mb-3"
        style={{ color: "var(--color-text-primary)" }}
      >
        {props.title}
      </h3>
      <Show
        when={props.history.length > 0}
        fallback={
          <p class="text-sm italic" style={{ color: "var(--color-text-muted)" }}>
            {props.noHistoryText}
          </p>
        }
      >
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr style={{ "border-bottom": "1px solid var(--color-border)" }}>
                <th class="text-left py-2 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.timeLabel}</th>
                <th class="text-left py-2 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.statusLabel}</th>
                <th class="text-right py-2 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.recordsLabel}</th>
                <th class="text-right py-2 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.durationLabel}</th>
              </tr>
            </thead>
            <tbody>
              <For each={props.history}>
                {(record) => (
                  <>
                    <tr
                      class="hover:opacity-80 transition-opacity"
                      style={{ "border-bottom": "1px solid var(--color-border)" }}
                    >
                      <td class="py-2 px-2" style={{ color: "var(--color-text-primary)" }}>
                        {formatDateTime(record.startTime)}
                      </td>
                      <td class="py-2 px-2">
                        <StatusBadge status={record.status} />
                      </td>
                      <td class="py-2 px-2 text-right" style={{ color: "var(--color-text-primary)" }}>
                        {record.recordsCollected}
                      </td>
                      <td class="py-2 px-2 text-right" style={{ color: "var(--color-text-primary)" }}>
                        {formatDuration(record.durationSeconds)}
                      </td>
                    </tr>
                    <Show when={record.errors && record.errors.length > 0}>
                      <tr class="bg-status-error-bg">
                        <td colspan="4" class="py-2 px-2 text-xs text-status-error-text">
                          <For each={record.errors}>
                            {(error) => <div>{error}</div>}
                          </For>
                        </td>
                      </tr>
                    </Show>
                  </>
                )}
              </For>
            </tbody>
          </table>
        </div>
      </Show>
    </div>
  );
}

/**
 * Data stats card component.
 */
function DataStatsCard(props: {
  stats: DataStatsResponse;
  dateRange: number | undefined;
  onDateRangeChange: (days: number | undefined) => void;
  labels: {
    title: string;
    forecasts: string;
    observations: string;
    deviations: string;
    sites: string;
    allTime: string;
    last7Days: string;
    last30Days: string;
  };
}): JSX.Element {
  return (
    <div
      class="rounded-lg shadow p-4 transition-colors"
      style={{
        "background-color": "var(--color-surface)",
        "border": "1px solid var(--color-border)",
      }}
    >
      <div class="flex items-center justify-between mb-4">
        <h3
          class="text-lg font-semibold"
          style={{ color: "var(--color-text-primary)" }}
        >
          {props.labels.title}
        </h3>
        <select
          value={props.dateRange === undefined ? "" : String(props.dateRange)}
          onChange={(e) => {
            const val = e.currentTarget.value;
            props.onDateRangeChange(val === "" ? undefined : parseInt(val, 10));
          }}
          class="text-sm px-2 py-1 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          style={{
            "background-color": "var(--color-bg-primary)",
            "border": "1px solid var(--color-border)",
            "color": "var(--color-text-primary)",
          }}
        >
          <option value="">{props.labels.allTime}</option>
          <option value="7">{props.labels.last7Days}</option>
          <option value="30">{props.labels.last30Days}</option>
        </select>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="text-center">
          <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {props.stats.totalForecasts.toLocaleString()}
          </div>
          <div class="text-sm" style={{ color: "var(--color-text-muted)" }}>
            {props.labels.forecasts}
          </div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-green-600 dark:text-green-400">
            {props.stats.totalObservations.toLocaleString()}
          </div>
          <div class="text-sm" style={{ color: "var(--color-text-muted)" }}>
            {props.labels.observations}
          </div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {props.stats.totalDeviations.toLocaleString()}
          </div>
          <div class="text-sm" style={{ color: "var(--color-text-muted)" }}>
            {props.labels.deviations}
          </div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {props.stats.totalSites.toLocaleString()}
          </div>
          <div class="text-sm" style={{ color: "var(--color-text-muted)" }}>
            {props.labels.sites}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Data preview table component.
 */
function DataPreviewTable(props: {
  preview: DataPreviewResponse;
  labels: {
    title: string;
    forecastsTitle: string;
    observationsTitle: string;
    noData: string;
    timestamp: string;
    site: string;
    parameter: string;
    value: string;
  };
}): JSX.Element {
  const forecastSources = () => Object.keys(props.preview.forecasts);
  const observationSources = () => Object.keys(props.preview.observations);

  return (
    <div
      class="rounded-lg shadow p-4 transition-colors"
      style={{
        "background-color": "var(--color-surface)",
        "border": "1px solid var(--color-border)",
      }}
    >
      <h3
        class="text-lg font-semibold mb-4"
        style={{ color: "var(--color-text-primary)" }}
      >
        {props.labels.title}
      </h3>

      {/* Forecasts Section */}
      <div class="mb-6">
        <h4
          class="text-md font-medium mb-2"
          style={{ color: "var(--color-text-secondary)" }}
        >
          {props.labels.forecastsTitle}
        </h4>
        <Show
          when={forecastSources().length > 0}
          fallback={
            <p class="text-sm italic" style={{ color: "var(--color-text-muted)" }}>
              {props.labels.noData}
            </p>
          }
        >
          <div class="space-y-4">
            <For each={forecastSources()}>
              {(source) => (
                <div>
                  <div class="text-sm font-medium mb-1 text-blue-600 dark:text-blue-400">
                    {source}
                  </div>
                  <div class="overflow-x-auto">
                    <table class="min-w-full text-xs">
                      <thead>
                        <tr style={{ "border-bottom": "1px solid var(--color-border)" }}>
                          <th class="text-left py-1 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.labels.timestamp}</th>
                          <th class="text-left py-1 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.labels.site}</th>
                          <th class="text-left py-1 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.labels.parameter}</th>
                          <th class="text-right py-1 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.labels.value}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <For each={props.preview.forecasts[source]}>
                          {(record) => (
                            <tr style={{ "border-bottom": "1px solid var(--color-border)" }}>
                              <td class="py-1 px-2 font-mono" style={{ color: "var(--color-text-primary)" }}>
                                {formatDateTime(record.valid_time)}
                              </td>
                              <td class="py-1 px-2" style={{ color: "var(--color-text-primary)" }}>
                                {record.site}
                              </td>
                              <td class="py-1 px-2" style={{ color: "var(--color-text-primary)" }}>
                                {record.parameter}
                              </td>
                              <td class="py-1 px-2 text-right font-mono" style={{ color: "var(--color-text-primary)" }}>
                                {record.value.toFixed(1)}
                              </td>
                            </tr>
                          )}
                        </For>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </For>
          </div>
        </Show>
      </div>

      {/* Observations Section */}
      <div>
        <h4
          class="text-md font-medium mb-2"
          style={{ color: "var(--color-text-secondary)" }}
        >
          {props.labels.observationsTitle}
        </h4>
        <Show
          when={observationSources().length > 0}
          fallback={
            <p class="text-sm italic" style={{ color: "var(--color-text-muted)" }}>
              {props.labels.noData}
            </p>
          }
        >
          <div class="space-y-4">
            <For each={observationSources()}>
              {(source) => (
                <div>
                  <div class="text-sm font-medium mb-1 text-green-600 dark:text-green-400">
                    {source}
                  </div>
                  <div class="overflow-x-auto">
                    <table class="min-w-full text-xs">
                      <thead>
                        <tr style={{ "border-bottom": "1px solid var(--color-border)" }}>
                          <th class="text-left py-1 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.labels.timestamp}</th>
                          <th class="text-left py-1 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.labels.site}</th>
                          <th class="text-left py-1 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.labels.parameter}</th>
                          <th class="text-right py-1 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.labels.value}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <For each={props.preview.observations[source]}>
                          {(record) => (
                            <tr style={{ "border-bottom": "1px solid var(--color-border)" }}>
                              <td class="py-1 px-2 font-mono" style={{ color: "var(--color-text-primary)" }}>
                                {formatDateTime(record.observation_time)}
                              </td>
                              <td class="py-1 px-2" style={{ color: "var(--color-text-primary)" }}>
                                {record.site}
                              </td>
                              <td class="py-1 px-2" style={{ color: "var(--color-text-primary)" }}>
                                {record.parameter}
                              </td>
                              <td class="py-1 px-2 text-right font-mono" style={{ color: "var(--color-text-primary)" }}>
                                {record.value.toFixed(1)}
                              </td>
                            </tr>
                          )}
                        </For>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </For>
          </div>
        </Show>
      </div>
    </div>
  );
}

/**
 * Scheduled jobs table component.
 */
function ScheduledJobsTable(props: {
  jobs: ScheduledJobInfo[];
  title: string;
  noJobsText: string;
  jobLabel: string;
  nextRunLabel: string;
  triggerLabel: string;
  notScheduledText: string;
}): JSX.Element {
  return (
    <div
      class="rounded-lg shadow p-4 transition-colors"
      style={{
        "background-color": "var(--color-surface)",
        "border": "1px solid var(--color-border)",
      }}
    >
      <h3
        class="text-lg font-semibold mb-3"
        style={{ color: "var(--color-text-primary)" }}
      >
        {props.title}
      </h3>
      <Show
        when={props.jobs.length > 0}
        fallback={
          <p class="text-sm italic" style={{ color: "var(--color-text-muted)" }}>
            {props.noJobsText}
          </p>
        }
      >
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr style={{ "border-bottom": "1px solid var(--color-border)" }}>
                <th class="text-left py-2 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.jobLabel}</th>
                <th class="text-left py-2 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.nextRunLabel}</th>
                <th class="text-left py-2 px-2 font-medium" style={{ color: "var(--color-text-secondary)" }}>{props.triggerLabel}</th>
              </tr>
            </thead>
            <tbody>
              <For each={props.jobs}>
                {(job) => (
                  <tr
                    class="hover:opacity-80 transition-opacity"
                    style={{ "border-bottom": "1px solid var(--color-border)" }}
                  >
                    <td class="py-2 px-2 font-medium" style={{ color: "var(--color-text-primary)" }}>{job.name}</td>
                    <td class="py-2 px-2" style={{ color: "var(--color-text-primary)" }}>
                      {job.nextRunTime ? formatDateTime(job.nextRunTime) : props.notScheduledText}
                    </td>
                    <td class="py-2 px-2 text-xs font-mono" style={{ color: "var(--color-text-muted)" }}>
                      {job.trigger}
                    </td>
                  </tr>
                )}
              </For>
            </tbody>
          </table>
        </div>
      </Show>
    </div>
  );
}

/**
 * Loading spinner component.
 */
function LoadingSpinner(): JSX.Element {
  return (
    <svg
      class="animate-spin h-5 w-5 text-white"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-label="Loading"
      role="status"
    >
      <circle
        class="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        stroke-width="4"
      />
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

/**
 * Login form component for admin authentication.
 */
function LoginForm(props: {
  onLogin: (username: string, password: string) => void;
  error: string | null;
  isLoading: boolean;
  labels: {
    title: string;
    username: string;
    password: string;
    login: string;
    loggingIn: string;
  };
}): JSX.Element {
  const [username, setUsername] = createSignal('');
  const [password, setPassword] = createSignal('');

  function handleSubmit(e: Event): void {
    e.preventDefault();
    props.onLogin(username(), password());
  }

  return (
    <div
      class="min-h-screen flex items-center justify-center transition-colors"
      style={{ "background-color": "var(--color-bg-secondary)" }}
    >
      <div
        class="p-8 rounded-lg shadow-lg max-w-md w-full transition-colors"
        style={{
          "background-color": "var(--color-surface)",
          "border": "1px solid var(--color-border)",
        }}
      >
        <h1
          class="text-2xl font-bold mb-6 text-center"
          style={{ color: "var(--color-text-primary)" }}
        >
          {props.labels.title}
        </h1>

        <Show when={props.error}>
          <div class="bg-status-error-bg border border-status-error-border text-status-error-text px-4 py-3 rounded mb-4">
            {props.error}
          </div>
        </Show>

        <form onSubmit={handleSubmit}>
          <div class="mb-4">
            <label
              class="block text-sm font-medium mb-2"
              style={{ color: "var(--color-text-secondary)" }}
              for="username"
            >
              {props.labels.username}
            </label>
            <input
              id="username"
              type="text"
              value={username()}
              onInput={(e) => setUsername(e.currentTarget.value)}
              class="w-full px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
              style={{
                "background-color": "var(--color-bg-primary)",
                "border": "1px solid var(--color-border)",
                "color": "var(--color-text-primary)",
              }}
              required
              autocomplete="username"
            />
          </div>

          <div class="mb-6">
            <label
              class="block text-sm font-medium mb-2"
              style={{ color: "var(--color-text-secondary)" }}
              for="password"
            >
              {props.labels.password}
            </label>
            <input
              id="password"
              type="password"
              value={password()}
              onInput={(e) => setPassword(e.currentTarget.value)}
              class="w-full px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
              style={{
                "background-color": "var(--color-bg-primary)",
                "border": "1px solid var(--color-border)",
                "color": "var(--color-text-primary)",
              }}
              required
              autocomplete="current-password"
            />
          </div>

          <button
            type="submit"
            disabled={props.isLoading}
            class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Show when={props.isLoading}>
              <LoadingSpinner />
            </Show>
            {props.isLoading ? props.labels.loggingIn : props.labels.login}
          </button>
        </form>
      </div>
    </div>
  );
}

/**
 * Admin Dashboard page.
 */
export default function Admin(): JSX.Element {
  const { t } = useI18n();

  // Auth state
  const [isAuthenticated, setIsAuthenticated] = createSignal(hasAdminCredentials());
  const [loginError, setLoginError] = createSignal<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = createSignal(false);

  // State signals
  const [status, setStatus] = createSignal<AdminSchedulerStatusResponse | null>(null);
  const [jobs, setJobs] = createSignal<SchedulerJobsResponse | null>(null);
  const [stats, setStats] = createSignal<DataStatsResponse | null>(null);
  const [dataPreview, setDataPreview] = createSignal<DataPreviewResponse | null>(null);
  const [statsDateRange, setStatsDateRange] = createSignal<number | undefined>(undefined);
  const [error, setError] = createSignal<string | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = createSignal(true);
  const [isTogglingScheduler, setIsTogglingScheduler] = createSignal(false);
  const [isCollectingForecasts, setIsCollectingForecasts] = createSignal(false);
  const [isCollectingObservations, setIsCollectingObservations] = createSignal(false);
  const [lastRefresh, setLastRefresh] = createSignal<Date | null>(null);
  const [actionMessage, setActionMessage] = createSignal<string | null>(null);
  const [confirmStopScheduler, setConfirmStopScheduler] = createSignal(false);

  /**
   * Handle login attempt.
   */
  async function handleLogin(username: string, password: string): Promise<void> {
    setIsLoggingIn(true);
    setLoginError(null);

    // Store credentials and try to fetch data
    setAdminCredentials(username, password);

    try {
      await fetchAdminSchedulerStatus();
      setIsAuthenticated(true);
      fetchData();
    } catch (err) {
      clearAdminCredentials();
      if (err instanceof ApiRequestError && err.statusCode === 401) {
        setLoginError(t('admin.loginError'));
      } else {
        setLoginError(t('admin.loginFailed'));
      }
    } finally {
      setIsLoggingIn(false);
    }
  }

  /**
   * Handle logout.
   */
  function handleLogout(): void {
    clearAdminCredentials();
    setIsAuthenticated(false);
    setStatus(null);
    setJobs(null);
  }

  /**
   * Fetch all admin data.
   */
  async function fetchData(): Promise<void> {
    setError(null);
    try {
      const [statusData, jobsData, statsData, previewData] = await Promise.all([
        fetchAdminSchedulerStatus(),
        fetchAdminSchedulerJobs(),
        fetchAdminStats(statsDateRange()),
        fetchAdminDataPreview(),
      ]);
      setStatus(statusData);
      setJobs(jobsData);
      setStats(statsData);
      setDataPreview(previewData);
      setLastRefresh(new Date());
    } catch (err) {
      if (err instanceof ApiRequestError) {
        if (err.statusCode === 401) {
          // Session expired or invalid credentials - log out
          handleLogout();
          return;
        } else if (err.statusCode === 429) {
          setError(t('admin.tooManyRequests'));
        } else {
          setError(err.message);
        }
      } else if (err instanceof NetworkError) {
        setError(t('admin.networkError'));
      } else if (err instanceof TimeoutError) {
        setError(t('admin.timeoutError'));
      } else {
        setError(t('admin.unexpectedError'));
      }
    } finally {
      setIsLoadingStatus(false);
    }
  }

  /**
   * Handle scheduler toggle with confirmation for stopping.
   */
  async function handleToggleScheduler(): Promise<void> {
    // If scheduler is running, require confirmation before stopping
    if (status()?.running && !confirmStopScheduler()) {
      setConfirmStopScheduler(true);
      return;
    }

    setConfirmStopScheduler(false);
    setIsTogglingScheduler(true);
    setActionMessage(null);
    try {
      const result = await toggleScheduler();
      setActionMessage(result.message);
      await fetchData();
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else if (err instanceof NetworkError) {
        setError(t('admin.networkError'));
      } else if (err instanceof TimeoutError) {
        setError(t('admin.timeoutError'));
      } else {
        setError(t('admin.failedToggleScheduler'));
      }
    } finally {
      setIsTogglingScheduler(false);
    }
  }

  /**
   * Cancel scheduler stop confirmation.
   */
  function cancelStopScheduler(): void {
    setConfirmStopScheduler(false);
  }

  /**
   * Handle forecast collection trigger.
   */
  async function handleCollectForecasts(): Promise<void> {
    setIsCollectingForecasts(true);
    setActionMessage(null);
    try {
      const result = await triggerForecastCollection();
      setActionMessage(
        `${t('admin.forecastCollection')}: ${result.status} - ${result.recordsCollected} ${t('admin.records').toLowerCase()} (${formatDuration(result.durationSeconds)})`
      );
      await fetchData();
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError(t('admin.failedTriggerForecast'));
      }
    } finally {
      setIsCollectingForecasts(false);
    }
  }

  /**
   * Handle observation collection trigger.
   */
  async function handleCollectObservations(): Promise<void> {
    setIsCollectingObservations(true);
    setActionMessage(null);
    try {
      const result = await triggerObservationCollection();
      setActionMessage(
        `${t('admin.observationCollection')}: ${result.status} - ${result.recordsCollected} ${t('admin.records').toLowerCase()} (${formatDuration(result.durationSeconds)})`
      );
      await fetchData();
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError(t('admin.failedTriggerObservation'));
      }
    } finally {
      setIsCollectingObservations(false);
    }
  }

  // Initial data fetch and auto-refresh setup
  let refreshInterval: number | undefined;

  onMount(() => {
    // Only fetch if already authenticated
    if (isAuthenticated()) {
      fetchData();
    } else {
      setIsLoadingStatus(false);
    }

    // Setup auto-refresh interval
    refreshInterval = window.setInterval(() => {
      if (isAuthenticated() && !isTogglingScheduler() && !isCollectingForecasts() && !isCollectingObservations()) {
        fetchData();
      }
    }, AUTO_REFRESH_INTERVAL);
  });

  onCleanup(() => {
    if (refreshInterval) {
      window.clearInterval(refreshInterval);
    }
  });

  // Clear action message after 5 seconds
  createEffect(() => {
    const msg = actionMessage();
    if (msg) {
      const timer = setTimeout(() => setActionMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  });

  // Show login form if not authenticated
  if (!isAuthenticated()) {
    return (
      <LoginForm
        onLogin={handleLogin}
        error={loginError()}
        isLoading={isLoggingIn()}
        labels={{
          title: t('admin.login'),
          username: t('admin.username'),
          password: t('admin.password'),
          login: t('admin.login'),
          loggingIn: t('admin.loggingIn'),
        }}
      />
    );
  }

  return (
    <div class="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1
            class="text-3xl font-bold"
            style={{ color: "var(--color-text-primary)" }}
          >
            {t('admin.dashboard')}
          </h1>
          <Show when={lastRefresh()}>
            <p class="text-sm mt-1" style={{ color: "var(--color-text-muted)" }}>
              {t('admin.lastUpdated')}: {formatTime(lastRefresh()!)}
              <span class="ml-2" style={{ color: "var(--color-text-muted)" }}>({t('admin.autoRefresh')})</span>
            </p>
          </Show>
        </div>
        <div class="flex gap-2">
          <button
            onClick={() => fetchData()}
            disabled={isLoadingStatus()}
            class="px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
            style={{
              "background-color": "var(--color-surface)",
              "border": "1px solid var(--color-border)",
              "color": "var(--color-text-primary)",
            }}
          >
            {t('admin.refresh')}
          </button>
          <button
            onClick={handleLogout}
            class="px-4 py-2 rounded-lg transition-colors"
            style={{
              "background-color": "var(--color-surface)",
              "border": "1px solid var(--color-border)",
              "color": "var(--color-text-primary)",
            }}
          >
            {t('admin.logout')}
          </button>
        </div>
      </div>

      {/* Error Alert */}
      <Show when={error()}>
        <div class="bg-status-error-bg border border-status-error-border text-status-error-text px-4 py-3 rounded-lg mb-6">
          <div class="flex items-center">
            <svg class="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clip-rule="evenodd"
              />
            </svg>
            {error()}
          </div>
        </div>
      </Show>

      {/* Action Message */}
      <Show when={actionMessage()}>
        <div class="bg-status-success-bg border border-status-success-border text-status-success-text px-4 py-3 rounded-lg mb-6">
          <div class="flex items-center">
            <svg class="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clip-rule="evenodd"
              />
            </svg>
            {actionMessage()}
          </div>
        </div>
      </Show>

      {/* Loading State */}
      <Show when={isLoadingStatus() && !status()}>
        <div class="flex items-center justify-center py-12">
          <div class="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full" />
          <span class="ml-3" style={{ color: "var(--color-text-secondary)" }}>{t('admin.loadingAdminData')}</span>
        </div>
      </Show>

      {/* Main Content */}
      <Show when={status()}>
        {/* Scheduler Status & Controls */}
        <div
          class="rounded-lg shadow p-6 mb-6 transition-colors"
          style={{
            "background-color": "var(--color-surface)",
            "border": "1px solid var(--color-border)",
          }}
        >
          <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            {/* Status Indicator */}
            <div class="flex items-center gap-4">
              <h2
                class="text-xl font-semibold"
                style={{ color: "var(--color-text-primary)" }}
              >
                {t('admin.schedulerStatus')}
              </h2>
              <div class="flex items-center gap-2" role="status" aria-live="polite">
                <span
                  class={`h-3 w-3 rounded-full ${
                    status()?.running ? 'bg-green-500' : 'bg-red-500'
                  }`}
                  aria-hidden="true"
                />
                <span
                  class={`font-medium ${
                    status()?.running ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {status()?.running ? t('admin.running') : t('admin.stopped')}
                </span>
              </div>
            </div>

            {/* Control Buttons */}
            <div class="flex flex-wrap gap-3">
              <Show
                when={!confirmStopScheduler()}
                fallback={
                  <div class="flex items-center gap-2">
                    <span class="text-red-600 dark:text-red-400 font-medium">{t('admin.confirmStop')}</span>
                    <button
                      onClick={handleToggleScheduler}
                      disabled={isTogglingScheduler()}
                      class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                      <Show when={isTogglingScheduler()}>
                        <LoadingSpinner />
                      </Show>
                      {t('admin.confirm')}
                    </button>
                    <button
                      onClick={cancelStopScheduler}
                      class="px-3 py-1 rounded font-medium transition-colors"
                      style={{
                        "background-color": "var(--color-bg-secondary)",
                        "color": "var(--color-text-primary)",
                      }}
                    >
                      {t('admin.cancel')}
                    </button>
                  </div>
                }
              >
                <button
                  onClick={handleToggleScheduler}
                  disabled={isTogglingScheduler()}
                  class={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                    status()?.running
                      ? 'bg-red-600 hover:bg-red-700 text-white'
                      : 'bg-green-600 hover:bg-green-700 text-white'
                  } disabled:opacity-50`}
                >
                  <Show when={isTogglingScheduler()}>
                    <LoadingSpinner />
                  </Show>
                  {status()?.running ? t('admin.stopScheduler') : t('admin.startScheduler')}
                </button>
              </Show>

              <button
                onClick={handleCollectForecasts}
                disabled={isCollectingForecasts()}
                class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <Show when={isCollectingForecasts()}>
                  <LoadingSpinner />
                </Show>
                {t('admin.triggerForecasts')}
              </button>

              <button
                onClick={handleCollectObservations}
                disabled={isCollectingObservations()}
                class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <Show when={isCollectingObservations()}>
                  <LoadingSpinner />
                </Show>
                {t('admin.triggerObservations')}
              </button>
            </div>
          </div>
        </div>

        {/* Data Statistics */}
        <Show when={stats()}>
          <div class="mb-6">
            <DataStatsCard
              stats={stats()!}
              dateRange={statsDateRange()}
              onDateRangeChange={async (days) => {
                setStatsDateRange(days);
                try {
                  const newStats = await fetchAdminStats(days);
                  setStats(newStats);
                } catch (err) {
                  // Keep existing stats on error
                }
              }}
              labels={{
                title: t('admin.dataStats'),
                forecasts: t('admin.totalForecasts'),
                observations: t('admin.totalObservations'),
                deviations: t('admin.totalDeviations'),
                sites: t('admin.totalSites'),
                allTime: t('admin.allTime'),
                last7Days: t('admin.last7Days'),
                last30Days: t('admin.last30Days'),
              }}
            />
          </div>
        </Show>

        {/* Scheduled Jobs */}
        <Show when={jobs()}>
          <div class="mb-6">
            <ScheduledJobsTable
              jobs={jobs()?.jobs || []}
              title={t('admin.scheduledJobs')}
              noJobsText={t('admin.noJobsScheduled')}
              jobLabel={t('admin.job')}
              nextRunLabel={t('admin.nextRun')}
              triggerLabel={t('admin.trigger')}
              notScheduledText={t('admin.notScheduled')}
            />
          </div>
        </Show>

        {/* Data Preview */}
        <Show when={dataPreview()}>
          <div class="mb-6">
            <DataPreviewTable
              preview={dataPreview()!}
              labels={{
                title: t('admin.dataPreview'),
                forecastsTitle: t('admin.recentForecasts'),
                observationsTitle: t('admin.recentObservations'),
                noData: t('admin.noDataCollected'),
                timestamp: t('admin.timestamp'),
                site: t('admin.site'),
                parameter: t('admin.parameter'),
                value: t('admin.value'),
              }}
            />
          </div>
        </Show>

        {/* Execution History */}
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ExecutionHistoryTable
            title={t('admin.forecastHistory')}
            history={status()?.forecastHistory || []}
            noHistoryText={t('admin.noExecutionHistory')}
            timeLabel={t('admin.time')}
            statusLabel={t('admin.status')}
            recordsLabel={t('admin.records')}
            durationLabel={t('admin.duration')}
          />
          <ExecutionHistoryTable
            title={t('admin.observationHistory')}
            history={status()?.observationHistory || []}
            noHistoryText={t('admin.noExecutionHistory')}
            timeLabel={t('admin.time')}
            statusLabel={t('admin.status')}
            recordsLabel={t('admin.records')}
            durationLabel={t('admin.duration')}
          />
        </div>
      </Show>
    </div>
  );
}
