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
} from '../lib/types';
import {
  fetchAdminSchedulerStatus,
  fetchAdminSchedulerJobs,
  toggleScheduler,
  triggerForecastCollection,
  triggerObservationCollection,
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
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'partial':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
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
                      <tr class="bg-red-50 dark:bg-red-900/20">
                        <td colspan="4" class="py-2 px-2 text-xs text-red-600 dark:text-red-400">
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
          <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded mb-4">
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
      const [statusData, jobsData] = await Promise.all([
        fetchAdminSchedulerStatus(),
        fetchAdminSchedulerJobs(),
      ]);
      setStatus(statusData);
      setJobs(jobsData);
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
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-lg mb-6">
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
        <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-lg mb-6">
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
