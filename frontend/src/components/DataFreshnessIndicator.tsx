import type { Component } from 'solid-js';
import { createSignal, createMemo, onMount, onCleanup } from 'solid-js';
import type { ConfidenceLevel } from '../lib/types';
import { useI18n } from '../contexts/I18nContext';

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

/** Confidence level icon/color configuration */
const CONFIDENCE_ICONS: Record<ConfidenceLevel, { icon: string; colorClass: string }> = {
  validated: { icon: '✅', colorClass: 'text-status-success-text' },
  preliminary: { icon: '🔶', colorClass: 'text-status-warning-text' },
  insufficient: { icon: '⚠️', colorClass: 'text-status-error-text' },
};

/** Milliseconds per time unit */
const MS_PER_MINUTE = 60000;
const MS_PER_HOUR = 3600000;
const MS_PER_DAY = 86400000;

/**
 * DataFreshnessIndicator component.
 * Displays data freshness information including last update, sample size,
 * date range, and confidence level.
 */
const DataFreshnessIndicator: Component<DataFreshnessIndicatorProps> = (props) => {
  const { t, language } = useI18n();

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
  const confidenceInfo = createMemo(() => CONFIDENCE_ICONS[props.confidenceLevel]);

  // Locale-aware date formatting
  const formatDate = (date: Date): string => {
    const locale = language() === 'fr' ? 'fr-FR' : 'en-US';
    return new Intl.DateTimeFormat(locale, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(date);
  };

  // Locale-aware relative time formatting
  const formatRelativeTime = (date: Date, currentNow: Date): string => {
    const diffMs = currentNow.getTime() - date.getTime();

    // Handle future dates (negative difference) - treat as "just now"
    if (diffMs < 0) return t('components.dataInfo.justNow');

    const diffMins = Math.floor(diffMs / MS_PER_MINUTE);
    const diffHours = Math.floor(diffMs / MS_PER_HOUR);
    const diffDays = Math.floor(diffMs / MS_PER_DAY);

    if (diffMins < 1) return t('components.dataInfo.justNow');
    if (diffMins < 60) {
      return diffMins === 1
        ? t('components.dataInfo.minuteAgo', { count: diffMins })
        : t('components.dataInfo.minutesAgo', { count: diffMins });
    }
    if (diffHours < 24) {
      return diffHours === 1
        ? t('components.dataInfo.hourAgo', { count: diffHours })
        : t('components.dataInfo.hoursAgo', { count: diffHours });
    }
    return diffDays === 1
      ? t('components.dataInfo.dayAgo', { count: diffDays })
      : t('components.dataInfo.daysAgo', { count: diffDays });
  };

  // Get confidence level translation keys
  const confidenceTitle = createMemo(() => {
    switch (props.confidenceLevel) {
      case 'validated': return t('components.dataInfo.validated');
      case 'preliminary': return t('components.dataInfo.preliminary');
      case 'insufficient': return t('components.dataInfo.insufficient');
    }
  });

  const confidenceMessage = createMemo(() => {
    switch (props.confidenceLevel) {
      case 'validated': return t('components.dataInfo.validatedMsg');
      case 'preliminary': return t('components.dataInfo.preliminaryMsg');
      case 'insufficient': return t('components.dataInfo.insufficientMsg');
    }
  });

  return (
    <div class="bg-theme-bg-primary border border-theme-border-primary rounded-lg p-6 shadow-sm">
      <h4 class="text-base font-semibold text-theme-text-primary mb-4">
        {t('components.dataInfo.title')}
      </h4>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Last Updated */}
        <div>
          <p class="text-xs text-theme-text-tertiary mb-1">
            {t('components.dataInfo.lastUpdated')}
          </p>
          <p class="text-sm font-medium text-theme-text-primary">
            {formatRelativeTime(props.lastUpdate, now())}
          </p>
          <p class="text-xs text-theme-text-tertiary">
            {formatDate(props.lastUpdate)}
          </p>
        </div>

        {/* Sample Size */}
        <div>
          <p class="text-xs text-theme-text-tertiary mb-1">
            {t('components.dataInfo.sampleSize')}
          </p>
          <p class="text-sm font-medium text-theme-text-primary">
            {props.sampleSize.toLocaleString()} {t('components.dataInfo.measurements')}
          </p>
          <p class="text-xs text-theme-text-tertiary">
            {t('components.dataInfo.daysOfData', { days: daysOfData() })}
          </p>
        </div>

        {/* Data Range */}
        <div>
          <p class="text-xs text-theme-text-tertiary mb-1">
            {t('components.dataInfo.dataRange')}
          </p>
          <p class="text-sm font-medium text-theme-text-primary">
            {formatDate(props.dateRange.start)}
          </p>
          <p class="text-xs text-theme-text-tertiary">
            {t('components.dataInfo.to')} {formatDate(props.dateRange.end)}
          </p>
        </div>
      </div>

      {/* Confidence Level Indicator */}
      <div class="mt-4 pt-4 border-t border-theme-border-secondary">
        <div class={`flex items-center gap-2 ${confidenceInfo().colorClass}`}>
          <div class="text-lg">{confidenceInfo().icon}</div>
          <div>
            <p class="text-sm font-medium">{confidenceTitle()}</p>
            <p class="text-xs">{confidenceMessage()}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataFreshnessIndicator;
