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
} from '../lib/api';

/** Auto-refresh interval in milliseconds (30 seconds) */
const AUTO_REFRESH_INTERVAL = 30000;

/**
 * Format ISO date string to readable format using browser locale.
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
        return 'bg-green-100 text-green-800';
      case 'partial':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
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
}): JSX.Element {
  return (
    <div class="bg-white rounded-lg shadow p-4">
      <h3 class="text-lg font-semibold text-gray-800 mb-3">{props.title}</h3>
      <Show
        when={props.history.length > 0}
        fallback={
          <p class="text-gray-500 text-sm italic">No execution history yet</p>
        }
      >
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-gray-200">
                <th class="text-left py-2 px-2 font-medium text-gray-600">Time</th>
                <th class="text-left py-2 px-2 font-medium text-gray-600">Status</th>
                <th class="text-right py-2 px-2 font-medium text-gray-600">Records</th>
                <th class="text-right py-2 px-2 font-medium text-gray-600">Duration</th>
              </tr>
            </thead>
            <tbody>
              <For each={props.history}>
                {(record) => (
                  <>
                    <tr class="border-b border-gray-100 hover:bg-gray-50">
                      <td class="py-2 px-2 text-gray-700">
                        {formatDateTime(record.startTime)}
                      </td>
                      <td class="py-2 px-2">
                        <StatusBadge status={record.status} />
                      </td>
                      <td class="py-2 px-2 text-right text-gray-700">
                        {record.recordsCollected}
                      </td>
                      <td class="py-2 px-2 text-right text-gray-700">
                        {formatDuration(record.durationSeconds)}
                      </td>
                    </tr>
                    <Show when={record.errors && record.errors.length > 0}>
                      <tr class="bg-red-50">
                        <td colspan="4" class="py-2 px-2 text-xs text-red-600">
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
function ScheduledJobsTable(props: { jobs: ScheduledJobInfo[] }): JSX.Element {
  return (
    <div class="bg-white rounded-lg shadow p-4">
      <h3 class="text-lg font-semibold text-gray-800 mb-3">Scheduled Jobs</h3>
      <Show
        when={props.jobs.length > 0}
        fallback={
          <p class="text-gray-500 text-sm italic">No jobs scheduled</p>
        }
      >
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-gray-200">
                <th class="text-left py-2 px-2 font-medium text-gray-600">Job</th>
                <th class="text-left py-2 px-2 font-medium text-gray-600">Next Run</th>
                <th class="text-left py-2 px-2 font-medium text-gray-600">Trigger</th>
              </tr>
            </thead>
            <tbody>
              <For each={props.jobs}>
                {(job) => (
                  <tr class="border-b border-gray-100 hover:bg-gray-50">
                    <td class="py-2 px-2 text-gray-700 font-medium">{job.name}</td>
                    <td class="py-2 px-2 text-gray-700">
                      {job.nextRunTime ? formatDateTime(job.nextRunTime) : 'Not scheduled'}
                    </td>
                    <td class="py-2 px-2 text-gray-500 text-xs font-mono">
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
 * Admin Dashboard page.
 */
export default function Admin(): JSX.Element {
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
          setError('Authentication failed. Please refresh the page to try again.');
        } else if (err.statusCode === 429) {
          setError('Too many requests. Please wait a moment and try again.');
        } else {
          setError(err.message);
        }
      } else if (err instanceof NetworkError) {
        setError('Network error - please check your connection.');
      } else if (err instanceof TimeoutError) {
        setError('Request timed out - the server may be busy. Please try again.');
      } else {
        setError('An unexpected error occurred. Please try again.');
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
        setError('Network error - please check your connection.');
      } else if (err instanceof TimeoutError) {
        setError('Request timed out - please try again.');
      } else {
        setError('Failed to toggle scheduler');
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
        `Forecast collection: ${result.status} - ${result.recordsCollected} records in ${formatDuration(result.durationSeconds)}`
      );
      await fetchData();
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError('Failed to trigger forecast collection');
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
        `Observation collection: ${result.status} - ${result.recordsCollected} records in ${formatDuration(result.durationSeconds)}`
      );
      await fetchData();
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError('Failed to trigger observation collection');
      }
    } finally {
      setIsCollectingObservations(false);
    }
  }

  // Initial data fetch and auto-refresh setup
  let refreshInterval: number | undefined;

  onMount(() => {
    // Fetch initial data
    fetchData();

    // Setup auto-refresh interval
    refreshInterval = window.setInterval(() => {
      if (!isTogglingScheduler() && !isCollectingForecasts() && !isCollectingObservations()) {
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

  return (
    <div class="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
          <Show when={lastRefresh()}>
            <p class="text-sm text-gray-500 mt-1">
              Last updated: {lastRefresh()?.toLocaleTimeString('fr-FR')}
              <span class="ml-2 text-gray-400">(auto-refresh every 30s)</span>
            </p>
          </Show>
        </div>
        <button
          onClick={() => fetchData()}
          disabled={isLoadingStatus()}
          class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {/* Error Alert */}
      <Show when={error()}>
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
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
        <div class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-6">
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
          <span class="ml-3 text-gray-600">Loading admin data...</span>
        </div>
      </Show>

      {/* Main Content */}
      <Show when={status()}>
        {/* Scheduler Status & Controls */}
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            {/* Status Indicator */}
            <div class="flex items-center gap-4">
              <h2 class="text-xl font-semibold text-gray-800">Scheduler Status</h2>
              <div class="flex items-center gap-2" role="status" aria-live="polite">
                <span
                  class={`h-3 w-3 rounded-full ${
                    status()?.running ? 'bg-green-500' : 'bg-red-500'
                  }`}
                  aria-hidden="true"
                />
                <span
                  class={`font-medium ${
                    status()?.running ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {status()?.running ? 'Running' : 'Stopped'}
                </span>
              </div>
            </div>

            {/* Control Buttons */}
            <div class="flex flex-wrap gap-3">
              <Show
                when={!confirmStopScheduler()}
                fallback={
                  <div class="flex items-center gap-2">
                    <span class="text-red-600 font-medium">Stop scheduler?</span>
                    <button
                      onClick={handleToggleScheduler}
                      disabled={isTogglingScheduler()}
                      class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                      <Show when={isTogglingScheduler()}>
                        <LoadingSpinner />
                      </Show>
                      Confirm
                    </button>
                    <button
                      onClick={cancelStopScheduler}
                      class="px-3 py-1 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded font-medium transition-colors"
                    >
                      Cancel
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
                  {status()?.running ? 'Stop Scheduler' : 'Start Scheduler'}
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
                Collect Forecasts
              </button>

              <button
                onClick={handleCollectObservations}
                disabled={isCollectingObservations()}
                class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <Show when={isCollectingObservations()}>
                  <LoadingSpinner />
                </Show>
                Collect Observations
              </button>
            </div>
          </div>
        </div>

        {/* Scheduled Jobs */}
        <Show when={jobs()}>
          <div class="mb-6">
            <ScheduledJobsTable jobs={jobs()?.jobs || []} />
          </div>
        </Show>

        {/* Execution History */}
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ExecutionHistoryTable
            title="Forecast Collection History"
            history={status()?.forecastHistory || []}
          />
          <ExecutionHistoryTable
            title="Observation Collection History"
            history={status()?.observationHistory || []}
          />
        </div>
      </Show>
    </div>
  );
}
