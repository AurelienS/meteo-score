import type { Component } from 'solid-js';
import { For, Show } from 'solid-js';
import type { Parameter } from '../lib/types';

/**
 * Display name mapping for weather parameters with emojis.
 * Maps API parameter names to user-friendly display names.
 */
export const PARAMETER_DISPLAY_NAMES: Record<string, { label: string; emoji: string }> = {
  'wind_speed': { label: 'Wind', emoji: '💨' },
  'wind_direction': { label: 'Direction', emoji: '🧭' },
  'temperature': { label: 'Temp', emoji: '🌡️' },
};

/**
 * Props for ParameterSelector component.
 * Uses Parameter type from types.ts for consistency.
 * DO NOT destructure - access via props.x for Solid.js reactivity.
 */
export interface ParameterSelectorProps {
  parameters: Pick<Parameter, 'id' | 'name' | 'unit'>[];
  selectedParameterId: number;
  onParameterChange: (parameterId: number) => void;
}

/**
 * Get display info for a parameter (label and emoji).
 * Falls back to capitalizing the name if not in mapping.
 */
function getDisplayInfo(name: string): { label: string; emoji: string } {
  if (PARAMETER_DISPLAY_NAMES[name]) {
    return PARAMETER_DISPLAY_NAMES[name];
  }
  return {
    label: name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    emoji: '📊'
  };
}

/**
 * Radio button group component for selecting a weather parameter.
 * Uses Solid.js patterns: props object access, <For> component.
 */
const ParameterSelector: Component<ParameterSelectorProps> = (props) => {
  const groupId = 'parameter-selector';

  return (
    <div class="w-full">
      <label
        id={`${groupId}-label`}
        class="block text-sm font-medium text-theme-text-secondary mb-2"
      >
        Weather Parameter
      </label>
      <div
        role="radiogroup"
        aria-labelledby={`${groupId}-label`}
        class="flex flex-wrap gap-2"
      >
        <Show when={props.parameters.length === 0}>
          <span class="text-sm text-theme-text-muted">No parameters available</span>
        </Show>
        <For each={props.parameters}>
          {(param) => {
            const info = getDisplayInfo(param.name);
            return (
              <label
                class="flex items-center cursor-pointer min-h-[36px] px-3 py-1 rounded-full border border-theme-border-primary hover:bg-theme-bg-tertiary transition-colors"
                classList={{ 'bg-theme-bg-tertiary border-theme-border-secondary': props.selectedParameterId === param.id }}
              >
                <input
                  type="radio"
                  name="parameter"
                  id={`${groupId}-${param.id}`}
                  value={param.id}
                  checked={props.selectedParameterId === param.id}
                  onChange={() => props.onParameterChange(param.id)}
                  class="sr-only"
                />
                <span class="text-sm text-theme-text-secondary">
                  {info.emoji} {info.label}
                </span>
              </label>
            );
          }}
        </For>
      </div>
    </div>
  );
};

export default ParameterSelector;
