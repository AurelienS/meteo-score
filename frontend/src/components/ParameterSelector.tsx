import type { Component } from 'solid-js';
import { For, Show } from 'solid-js';
import type { Parameter } from '../lib/types';

/**
 * Display name mapping for weather parameters.
 * Maps API parameter names to user-friendly display names.
 */
export const PARAMETER_DISPLAY_NAMES: Record<string, string> = {
  'wind_speed': 'Wind Speed',
  'wind_direction': 'Wind Direction',
  'temperature': 'Temperature',
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
 * Get display name for a parameter.
 * Falls back to capitalizing the name if not in mapping.
 */
function getDisplayName(name: string): string {
  return PARAMETER_DISPLAY_NAMES[name] || name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
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
        class="block text-sm font-medium text-gray-700 mb-2"
      >
        Weather Parameter
      </label>
      <div
        role="radiogroup"
        aria-labelledby={`${groupId}-label`}
        class="flex flex-wrap gap-4"
      >
        <Show when={props.parameters.length === 0}>
          <span class="text-sm text-gray-500">No parameters available</span>
        </Show>
        <For each={props.parameters}>
          {(param) => (
            <label class="flex items-center cursor-pointer">
              <input
                type="radio"
                name="parameter"
                id={`${groupId}-${param.id}`}
                value={param.id}
                checked={props.selectedParameterId === param.id}
                onChange={() => props.onParameterChange(param.id)}
                class="w-4 h-4 text-primary-500 focus:ring-primary-500 focus:ring-2"
              />
              <span class="ml-2 text-sm text-gray-700">
                {getDisplayName(param.name)} ({param.unit})
              </span>
            </label>
          )}
        </For>
      </div>
    </div>
  );
};

export default ParameterSelector;
