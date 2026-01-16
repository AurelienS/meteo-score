import type { Component } from 'solid-js';
import { createSignal, createMemo, onMount, onCleanup } from 'solid-js';
import type { ConfidenceLevel } from '../lib/types';

/**
 * Props for DataFreshnessIndicator component.
 * DO NOT destructure - access via props.x for Solid.js reactivity.
 */
export interface DataFreshnessIndicatorProps {
  lastUpdate: Date;
  sampleSize: number;
  dateRange: {
    start: Date;
    end: Date;
  };
  confidenceLevel: ConfidenceLevel;
}

/** Confidence level configuration */
const CONFIDENCE_CONFIG: Record<ConfidenceLevel, {
  icon: string;
  colorClass: string;
  title: string;
  message: string;
}> = {
  validated: {
    icon: '✅',
    colorClass: 'text-green-700',
    title: 'Validated Data',
    message: 'Metrics are statistically reliable (90+ days)',
  },
  preliminary: {
    icon: '🔶',
    colorClass: 'text-orange-700',
    title: 'Preliminary Data',
    message: 'Results will stabilize with more data (30-89 days)',
  },
  insufficient: {
    icon: '⚠️',
    colorClass: 'text-red-700',
    title: 'Insufficient Data',
    message: 'Collect more data for reliable metrics (<30 days)',
  },
};

/** Milliseconds per time unit */
const MS_PER_MINUTE = 60000;
const MS_PER_HOUR = 3600000;
const MS_PER_DAY = 86400000;

/**
 * Format a date as an absolute date string.
 */
function formatDate(date: Date): string {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date);
}

/**
 * Format the time difference as a relative string.
 * Handles edge cases including future dates (negative difference).
 */
function formatRelativeTime(date: Date, now: Date): string {
  const diffMs = now.getTime() - date.getTime();

  // Handle future dates (negative difference) - treat as "just now"
  if (diffMs < 0) return 'just now';

  const diffMins = Math.floor(diffMs / MS_PER_MINUTE);
  const diffHours = Math.floor(diffMs / MS_PER_HOUR);
  const diffDays = Math.floor(diffMs / MS_PER_DAY);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
}

/**
 * DataFreshnessIndicator component.
 * Displays data freshness information including last update, sample size,
 * date range, and confidence level.
 */
const DataFreshnessIndicator: Component<DataFreshnessIndicatorProps> = (props) => {
  // Signal for current time - updates every minute for relative time display
  const [now, setNow] = createSignal(new Date());

  // Auto-refresh relative time every minute
  onMount(() => {
    const interval = setInterval(() => {
      setNow(new Date());
    }, MS_PER_MINUTE);

    onCleanup(() => clearInterval(interval));
  });

  // Calculate days of data coverage (minimum 1 day)
  const daysOfData = createMemo(() => {
    const diffMs = props.dateRange.end.getTime() - props.dateRange.start.getTime();
    return Math.max(1, Math.floor(diffMs / MS_PER_DAY));
  });

  // Get confidence configuration
  const confidenceInfo = createMemo(() => CONFIDENCE_CONFIG[props.confidenceLevel]);

  return (
    <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
      <h4 class="text-sm font-semibold text-gray-700 mb-3">Data Information</h4>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Last Updated */}
        <div>
          <p class="text-xs text-gray-500 mb-1">Last Updated</p>
          <p class="text-sm font-medium text-gray-900">
            {formatRelativeTime(props.lastUpdate, now())}
          </p>
          <p class="text-xs text-gray-500">
            {formatDate(props.lastUpdate)}
          </p>
        </div>

        {/* Sample Size */}
        <div>
          <p class="text-xs text-gray-500 mb-1">Sample Size</p>
          <p class="text-sm font-medium text-gray-900">
            {props.sampleSize.toLocaleString()} measurements
          </p>
          <p class="text-xs text-gray-500">
            {daysOfData()} days of data
          </p>
        </div>

        {/* Data Range */}
        <div>
          <p class="text-xs text-gray-500 mb-1">Data Range</p>
          <p class="text-sm font-medium text-gray-900">
            {formatDate(props.dateRange.start)}
          </p>
          <p class="text-xs text-gray-500">
            to {formatDate(props.dateRange.end)}
          </p>
        </div>
      </div>

      {/* Confidence Level Indicator */}
      <div class="mt-4 pt-4 border-t border-gray-200">
        <div class={`flex items-center gap-2 ${confidenceInfo().colorClass}`}>
          <div class="text-lg">{confidenceInfo().icon}</div>
          <div>
            <p class="text-sm font-medium">{confidenceInfo().title}</p>
            <p class="text-xs">{confidenceInfo().message}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataFreshnessIndicator;
