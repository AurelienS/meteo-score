import type { Component } from 'solid-js';
import { For, Show } from 'solid-js';
import type { Site } from '../lib/types';

/**
 * Props for SiteSelector component.
 * Uses Site type from types.ts for consistency.
 * DO NOT destructure - access via props.x for Solid.js reactivity.
 */
export interface SiteSelectorProps {
  sites: Pick<Site, 'id' | 'name'>[];
  selectedSiteId: number;
  onSiteChange: (siteId: number) => void;
}

/**
 * Dropdown component for selecting a flying site.
 * Uses Solid.js patterns: props object access, <For> component.
 */
const SiteSelector: Component<SiteSelectorProps> = (props) => {
  const selectId = 'site-selector';

  return (
    <div class="w-full">
      <label
        for={selectId}
        class="block text-sm font-medium text-gray-700 mb-2"
      >
        Flying Site
      </label>
      <select
        id={selectId}
        class="block w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors"
        value={props.selectedSiteId}
        onChange={(e) => props.onSiteChange(Number(e.currentTarget.value))}
        disabled={props.sites.length === 0}
      >
        <Show when={props.sites.length === 0}>
          <option value={0} disabled>
            No sites available
          </option>
        </Show>
        <For each={props.sites}>
          {(site) => (
            <option value={site.id}>
              {site.name}
            </option>
          )}
        </For>
      </select>
    </div>
  );
};

export default SiteSelector;
