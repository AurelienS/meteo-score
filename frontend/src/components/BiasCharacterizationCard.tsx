import type { Component } from 'solid-js';
import { createMemo, Show } from 'solid-js';
import type { ConfidenceLevel } from '../lib/types';
import { useI18n } from '../contexts/I18nContext';

/** Threshold below which bias is considered negligible (in parameter units) */
const BIAS_EXCELLENT_THRESHOLD = 1.0;

/**
 * Props for BiasCharacterizationCard component.
 * DO NOT destructure - access via props.x for Solid.js reactivity.
 */
export interface BiasCharacterizationCardProps {
  modelName: string;
  bias: number;
  parameterName: string;
  parameterUnit: string;
  confidenceLevel: ConfidenceLevel;
}

/** Interpretation data for bias display */
interface BiasInterpretation {
  titleKey: string;
  descKey: string;
  icon: string;
  borderColor: string;
}

/**
 * Get bias interpretation keys based on bias value.
 * Positive bias = forecast < observed (underestimation).
 * Negative bias = forecast > observed (overestimation).
 */
function getBiasInterpretationKeys(bias: number): BiasInterpretation {
  const absBias = Math.abs(bias);

  if (absBias < BIAS_EXCELLENT_THRESHOLD) {
    return {
      titleKey: 'components.bias.excellentTitle',
      descKey: 'components.bias.excellentDesc',
      icon: '🎯',
      borderColor: 'border-l-green-500',
    };
  } else if (bias > 0) {
    return {
      titleKey: 'components.bias.underestimationTitle',
      descKey: 'components.bias.underestimationDesc',
      icon: '⬆️',
      borderColor: 'border-l-blue-500',
    };
  } else {
    return {
      titleKey: 'components.bias.overestimationTitle',
      descKey: 'components.bias.overestimationDesc',
      icon: '⬇️',
      borderColor: 'border-l-orange-500',
    };
  }
}

/**
 * Card component displaying bias characterization for a forecast model.
 * Shows user-friendly explanation of systematic bias with practical example.
 */
const BiasCharacterizationCard: Component<BiasCharacterizationCardProps> = (props) => {
  const { t } = useI18n();

  // Memoized interpretation keys for reactivity
  const interpretation = createMemo(() => getBiasInterpretationKeys(props.bias));

  // Calculate adjusted forecast value for practical example
  // bias = observed - forecast, so expected_actual = forecast + bias
  // If bias = +3 (underestimation): forecast 25 → expect 25 + 3 = 28 actual (stronger)
  // If bias = -3 (overestimation): forecast 25 → expect 25 + (-3) = 22 actual (weaker)
  const exampleForecast = createMemo(() => {
    // Use parameter-appropriate example values
    const paramLower = props.parameterName.toLowerCase();
    if (paramLower.includes('direction')) return 180; // degrees
    if (paramLower.includes('temperature') || paramLower.includes('temp')) return 20;
    return 25; // default for wind speed, etc.
  });
  const adjustedValue = createMemo(() => exampleForecast() + props.bias);

  const title = createMemo(() => t(interpretation().titleKey));
  const description = createMemo(() => {
    const absBias = Math.abs(props.bias);
    return t(interpretation().descKey, {
      model: props.modelName,
      parameter: props.parameterName.toLowerCase(),
      value: absBias.toFixed(1),
      unit: props.parameterUnit,
    });
  });

  return (
    <div
      class={`border-l-4 ${interpretation().borderColor} bg-theme-bg-primary p-6 rounded-lg shadow-sm border border-theme-border-primary`}
    >
      <div class="flex items-start">
        {/* Icon - decorative, hidden from screen readers */}
        <div class="text-3xl mr-4" aria-hidden="true">
          {interpretation().icon}
        </div>

        <div class="flex-1">
          {/* Title */}
          <h3 class="text-lg font-semibold text-theme-text-primary mb-2">
            {title()}
          </h3>

          {/* Description */}
          <p class="text-theme-text-secondary mb-3">
            {description()}
          </p>

          {/* Practical example - only show if we have enough data */}
          <Show when={props.confidenceLevel !== 'insufficient'}>
            <div class="mt-4 p-4 bg-theme-bg-tertiary rounded">
              <p class="text-sm font-medium text-theme-text-secondary mb-2">
                {t('components.bias.practicalExample')}
              </p>
              <p class="text-sm text-theme-text-secondary">
                {t('components.bias.exampleText', {
                  model: props.modelName,
                  parameter: props.parameterName.toLowerCase(),
                  forecast: exampleForecast(),
                  actual: adjustedValue().toFixed(0),
                  unit: props.parameterUnit,
                })}
              </p>
            </div>
          </Show>

          {/* Confidence warnings */}
          <Show when={props.confidenceLevel === 'preliminary'}>
            <p class="text-sm text-status-warning-text mt-3">
              ⚠️ {t('components.bias.preliminaryWarning')}
            </p>
          </Show>
          <Show when={props.confidenceLevel === 'insufficient'}>
            <p class="text-sm text-status-error-text mt-3">
              ⚠️ {t('components.bias.insufficientWarning')}
            </p>
          </Show>
        </div>
      </div>
    </div>
  );
};

export default BiasCharacterizationCard;
