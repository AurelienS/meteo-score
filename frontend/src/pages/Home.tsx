import type { Component } from 'solid-js';
import { createSignal, onMount, Show } from 'solid-js';

import SiteSelector from '../components/SiteSelector';
import ParameterSelector from '../components/ParameterSelector';
import HorizonSelector from '../components/HorizonSelector';
import { fetchSites, fetchParameters } from '../lib/api';
import type { Site, Parameter } from '../lib/types';

/** Standard forecast horizons for MVP */
const FORECAST_HORIZONS = [6, 12, 24, 48];

/**
 * Home page component.
 * Displays site, parameter, and horizon selectors for model comparison.
 */
const Home: Component = () => {
  // Data state - loaded from API
  const [sites, setSites] = createSignal<Site[]>([]);
  const [parameters, setParameters] = createSignal<Parameter[]>([]);

  // Selection state
  const [selectedSiteId, setSelectedSiteId] = createSignal<number>(0);
  const [selectedParameterId, setSelectedParameterId] = createSignal<number>(0);
  const [selectedHorizon, setSelectedHorizon] = createSignal<number>(6);

  // Loading states - specific per resource
  const [isLoadingSites, setIsLoadingSites] = createSignal(true);
  const [isLoadingParameters, setIsLoadingParameters] = createSignal(true);

  // Error state
  const [error, setError] = createSignal<string | null>(null);

  // Load data on mount
  onMount(async () => {
    try {
      // Fetch sites and parameters in parallel
      const [sitesData, parametersData] = await Promise.all([
        fetchSites(),
        fetchParameters(),
      ]);

      setSites(sitesData);
      setParameters(parametersData);

      // Set default selections to first items
      if (sitesData.length > 0) {
        setSelectedSiteId(sitesData[0].id);
      }
      if (parametersData.length > 0) {
        setSelectedParameterId(parametersData[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setIsLoadingSites(false);
      setIsLoadingParameters(false);
    }
  });

  const isLoading = () => isLoadingSites() || isLoadingParameters();

  return (
    <div class="container mx-auto px-4 py-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-2">
        MétéoScore
      </h1>
      <p class="text-gray-600 mb-8">
        Compare weather forecast accuracy across different models for paragliding sites.
      </p>

      {/* Error state */}
      <Show when={error()}>
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          <p class="font-medium">Error loading data</p>
          <p class="text-sm">{error()}</p>
        </div>
      </Show>

      {/* Loading state */}
      <Show when={isLoading()}>
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="animate-pulse space-y-4">
            <div class="h-4 bg-gray-200 rounded w-1/4" />
            <div class="h-10 bg-gray-200 rounded" />
            <div class="h-4 bg-gray-200 rounded w-1/4" />
            <div class="h-6 bg-gray-200 rounded w-1/2" />
          </div>
        </div>
      </Show>

      {/* Selectors - responsive grid */}
      <Show when={!isLoading() && !error()}>
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <SiteSelector
              sites={sites()}
              selectedSiteId={selectedSiteId()}
              onSiteChange={setSelectedSiteId}
            />
            <ParameterSelector
              parameters={parameters()}
              selectedParameterId={selectedParameterId()}
              onParameterChange={setSelectedParameterId}
            />
            <HorizonSelector
              horizons={FORECAST_HORIZONS}
              selectedHorizon={selectedHorizon()}
              onHorizonChange={setSelectedHorizon}
            />
          </div>
        </div>

        {/* Current selection summary */}
        <div class="bg-gray-50 rounded-lg p-4">
          <h2 class="text-sm font-medium text-gray-500 mb-2">Current Selection</h2>
          <p class="text-gray-700">
            <span class="font-medium">Site:</span>{' '}
            {sites().find(s => s.id === selectedSiteId())?.name || 'None'}
            {' | '}
            <span class="font-medium">Parameter:</span>{' '}
            {parameters().find(p => p.id === selectedParameterId())?.name || 'None'}
            {' | '}
            <span class="font-medium">Horizon:</span> +{selectedHorizon()}h
          </p>
        </div>
      </Show>
    </div>
  );
};

export default Home;
