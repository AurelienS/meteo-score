import type { Component } from 'solid-js';
import { For } from 'solid-js';
import { useI18n } from '../contexts/I18nContext';

/**
 * Props for HorizonSelector component.
 * DO NOT destructure - access via props.x for Solid.js reactivity.
 */
export interface HorizonSelectorProps {
  horizons: number[];
  selectedHorizon: number;
  onHorizonChange: (horizon: number) => void;
}

/**
 * Button group component for selecting a forecast horizon.
 * Uses Solid.js patterns: props object access, <For> component.
 */
const HorizonSelector: Component<HorizonSelectorProps> = (props) => {
  const { t } = useI18n();
  const groupId = 'horizon-selector';

  return (
    <div class="w-full">
      <label
        id={`${groupId}-label`}
        class="block text-sm font-medium text-theme-text-secondary mb-2"
      >
        {t('selectors.forecastHorizon')}
      </label>
      <div
        role="group"
        aria-labelledby={`${groupId}-label`}
        class="flex flex-wrap gap-2"
      >
        <For each={props.horizons}>
          {(horizon) => (
            <button
              type="button"
              id={`${groupId}-${horizon}`}
              aria-pressed={props.selectedHorizon === horizon}
              class={`px-4 py-2 min-h-[44px] min-w-[44px] rounded-lg font-medium transition-colors ${
                props.selectedHorizon === horizon
                  ? 'bg-primary-500 text-white'
                  : 'bg-theme-bg-tertiary text-theme-text-secondary hover:bg-theme-bg-primary'
              }`}
              onClick={() => props.onHorizonChange(horizon)}
            >
              +{horizon}h
            </button>
          )}
        </For>
      </div>
    </div>
  );
};

export default HorizonSelector;
