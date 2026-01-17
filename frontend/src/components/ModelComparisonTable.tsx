import type { Component } from 'solid-js';
import { createMemo, For, Show } from 'solid-js';
import type { ModelAccuracyMetrics, ConfidenceLevel } from '../lib/types';
import { useI18n } from '../contexts/I18nContext';

/** Threshold below which bias is considered negligible (in parameter units) */
const BIAS_NEGLIGIBLE_THRESHOLD = 0.5;

/**
 * Props for ModelComparisonTable component.
 * DO NOT destructure - access via props.x for Solid.js reactivity.
 */
export interface ModelComparisonTableProps {
  models: ModelAccuracyMetrics[];
  parameterUnit: string;
}

/**
 * Table component displaying model accuracy comparison.
 * Models are sorted by MAE (best first) with the best model highlighted.
 */
const ModelComparisonTable: Component<ModelComparisonTableProps> = (props) => {
  const { t } = useI18n();
  const tableId = 'model-comparison-table';

  // Sort models by MAE ascending (best accuracy first)
  const sortedModels = createMemo(() => {
    return [...props.models].sort((a, b) => a.mae - b.mae);
  });

  /**
   * Get confidence badge styling and text.
   * Maps confidence levels to color-coded badges.
   */
  const getConfidenceBadge = (level: ConfidenceLevel): { text: string; color: string } => {
    switch (level) {
      case 'validated':
        return { text: t('components.comparison.validated'), color: 'bg-status-success-bg text-status-success-text border border-status-success-border' };
      case 'preliminary':
        return { text: t('components.comparison.preliminary'), color: 'bg-status-warning-bg text-status-warning-text border border-status-warning-border' };
      case 'insufficient':
        return { text: t('components.comparison.insufficientData'), color: 'bg-status-error-bg text-status-error-text border border-status-error-border' };
      default: {
        // Exhaustive check - TypeScript will error if a case is missing
        const _exhaustiveCheck: never = level;
        return _exhaustiveCheck;
      }
    }
  };

  /**
   * Get human-readable bias interpretation text.
   * Positive bias = forecast < observed (underestimation).
   */
  const getBiasText = (bias: number, unit: string): string => {
    if (Math.abs(bias) < BIAS_NEGLIGIBLE_THRESHOLD) {
      return t('components.comparison.noBias');
    } else if (bias > 0) {
      return t('components.comparison.underestimates', { value: bias.toFixed(1), unit });
    } else {
      return t('components.comparison.overestimates', { value: Math.abs(bias).toFixed(1), unit });
    }
  };

  return (
    <div class="w-full">
      <h2
        id={`${tableId}-label`}
        class="text-base md:text-lg font-semibold text-theme-text-primary mb-4"
      >
        {t('components.comparison.title')}
      </h2>

      {/* Empty state */}
      <Show when={props.models.length === 0}>
        <div class="bg-theme-bg-tertiary rounded-lg p-8 text-center">
          <p class="text-theme-text-tertiary">{t('components.comparison.noData')}</p>
        </div>
      </Show>

      {/* Table */}
      <Show when={props.models.length > 0}>
        <div class="overflow-x-auto rounded-lg border border-theme-border-primary">
          <table
            class="min-w-full bg-theme-bg-primary"
            aria-labelledby={`${tableId}-label`}
          >
            <caption class="sr-only">
              Comparison of forecast model accuracy metrics sorted by Mean Absolute Error
            </caption>
            <thead class="bg-theme-bg-tertiary">
              <tr>
                <th
                  scope="col"
                  class="px-6 py-3 text-left text-xs font-medium text-theme-text-tertiary uppercase tracking-wider"
                >
                  {t('components.comparison.model')}
                </th>
                <th
                  scope="col"
                  class="px-6 py-3 text-left text-xs font-medium text-theme-text-tertiary uppercase tracking-wider"
                >
                  {t('components.comparison.mae')} ({props.parameterUnit})
                </th>
                <th
                  scope="col"
                  class="px-6 py-3 text-left text-xs font-medium text-theme-text-tertiary uppercase tracking-wider"
                >
                  {t('components.comparison.bias')}
                </th>
                <th
                  scope="col"
                  class="hidden md:table-cell px-6 py-3 text-left text-xs font-medium text-theme-text-tertiary uppercase tracking-wider"
                >
                  {t('components.comparison.sampleSize')}
                </th>
                <th
                  scope="col"
                  class="px-6 py-3 text-left text-xs font-medium text-theme-text-tertiary uppercase tracking-wider"
                >
                  {t('components.comparison.confidence')}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-theme-border-secondary">
              <For each={sortedModels()}>
                {(model, index) => {
                  const badge = getConfidenceBadge(model.confidenceLevel);

                  return (
                    <tr class={index() === 0 ? 'bg-status-success-bg' : 'bg-theme-bg-primary'}>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center gap-2">
                          <span class="font-medium text-theme-text-primary">
                            {model.modelName}
                          </span>
                          <Show when={index() === 0}>
                            <span class="px-2 py-0.5 text-xs font-medium bg-status-success-bg text-status-success-text border border-status-success-border rounded">
                              {t('components.comparison.best')}
                            </span>
                          </Show>
                        </div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-theme-text-primary">
                        {model.mae.toFixed(1)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-theme-text-secondary">
                        {getBiasText(model.bias, props.parameterUnit)}
                      </td>
                      <td class="hidden md:table-cell px-6 py-4 whitespace-nowrap text-sm text-theme-text-secondary">
                        {model.sampleSize.toLocaleString()} {t('components.comparison.measurements')}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <span
                          class={`px-2 py-1 text-xs font-medium rounded ${badge.color}`}
                          title={model.confidenceMessage}
                        >
                          {badge.text}
                        </span>
                      </td>
                    </tr>
                  );
                }}
              </For>
            </tbody>
          </table>
        </div>
      </Show>
    </div>
  );
};

export default ModelComparisonTable;
