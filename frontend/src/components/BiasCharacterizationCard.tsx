import type { Component } from 'solid-js';
import { createMemo, Show } from 'solid-js';
import type { ConfidenceLevel } from '../lib/types';

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
  title: string;
  description: string;
  icon: string;
  borderColor: string;
}

/**
 * Get bias interpretation based on bias value.
 * Positive bias = forecast < observed (underestimation).
 * Negative bias = forecast > observed (overestimation).
 */
function getBiasInterpretation(
  bias: number,
  modelName: string,
  parameterName: string,
  parameterUnit: string
): BiasInterpretation {
  const absBias = Math.abs(bias);

  if (absBias < BIAS_EXCELLENT_THRESHOLD) {
    return {
      title: 'Excellent Calibration',
      description: `${modelName} has minimal systematic bias for ${parameterName}.`,
      icon: '🎯',
      borderColor: 'border-l-green-500',
    };
  } else if (bias > 0) {
    return {
      title: 'Systematic Underestimation',
      description: `${modelName} typically underestimates ${parameterName} by ${absBias.toFixed(1)} ${parameterUnit} on average. Expect conditions to be slightly stronger than predicted.`,
      icon: '⬆️',
      borderColor: 'border-l-blue-500',
    };
  } else {
    return {
      title: 'Systematic Overestimation',
      description: `${modelName} typically overestimates ${parameterName} by ${absBias.toFixed(1)} ${parameterUnit} on average. Expect conditions to be slightly weaker than predicted.`,
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
  // Memoized interpretation for reactivity
  const interpretation = createMemo(() =>
    getBiasInterpretation(
      props.bias,
      props.modelName,
      props.parameterName,
      props.parameterUnit
    )
  );

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
            {interpretation().title}
          </h3>

          {/* Description */}
          <p class="text-theme-text-secondary mb-3">
            {interpretation().description}
          </p>

          {/* Practical example - only show if we have enough data */}
          <Show when={props.confidenceLevel !== 'insufficient'}>
            <div class="mt-4 p-4 bg-theme-bg-tertiary rounded">
              <p class="text-sm font-medium text-theme-text-secondary mb-2">
                Practical Example:
              </p>
              <p class="text-sm text-theme-text-secondary">
                If {props.modelName} forecasts {props.parameterName.toLowerCase()} at {exampleForecast()} {props.parameterUnit}, expect actual conditions around{' '}
                <span class="font-semibold">
                  {adjustedValue().toFixed(0)} {props.parameterUnit}
                </span>
                {' '}based on historical bias.
              </p>
            </div>
          </Show>

          {/* Confidence warnings */}
          <Show when={props.confidenceLevel === 'preliminary'}>
            <p class="text-sm text-status-warning-text mt-3">
              ⚠️ This bias characterization is preliminary. Results will stabilize with more data.
            </p>
          </Show>
          <Show when={props.confidenceLevel === 'insufficient'}>
            <p class="text-sm text-status-error-text mt-3">
              ⚠️ Insufficient data to reliably characterize bias.
            </p>
          </Show>
        </div>
      </div>
    </div>
  );
};

export default BiasCharacterizationCard;
