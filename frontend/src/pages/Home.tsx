import type { Component } from 'solid-js';
import { createSignal, createEffect, onMount, Show } from 'solid-js';

import SiteSelector from '../components/SiteSelector';
import ParameterSelector from '../components/ParameterSelector';
import HorizonSelector from '../components/HorizonSelector';
import ModelComparisonTable from '../components/ModelComparisonTable';
import { fetchSites, fetchParameters, fetchSiteAccuracy } from '../lib/api';
import type { Site, Parameter, SiteAccuracyResponse } from '../lib/types';

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
  const [accuracyData, setAccuracyData] = createSignal<SiteAccuracyResponse | null>(null);

  // Selection state
  const [selectedSiteId, setSelectedSiteId] = createSignal<number>(0);
  const [selectedParameterId, setSelectedParameterId] = createSignal<number>(0);
  const [selectedHorizon, setSelectedHorizon] = createSignal<number>(6);

  // Loading states - specific per resource
  const [isLoadingSites, setIsLoadingSites] = createSignal(true);
  const [isLoadingParameters, setIsLoadingParameters] = createSignal(true);
  const [isLoadingAccuracy, setIsLoadingAccuracy] = createSignal(false);

  // Error state
  const [error, setError] = createSignal<string | null>(null);
  const [accuracyError, setAccuracyError] = createSignal<string | null>(null);

  // Get selected parameter unit for display
  const selectedParameterUnit = () => {
    const param = parameters().find(p => p.id === selectedParameterId());
    return param?.unit || '';
  };

  // Fetch accuracy data when selections change
  const loadAccuracyData = async (siteId: number, parameterId: number, horizon: number) => {
    if (!siteId || !parameterId) return;

    setIsLoadingAccuracy(true);
    setAccuracyError(null);

    try {
      const data = await fetchSiteAccuracy(siteId, parameterId, horizon);
      setAccuracyData(data);
    } catch (err) {
      setAccuracyError(err instanceof Error ? err.message : 'Failed to load accuracy data');
      setAccuracyData(null);
    } finally {
      setIsLoadingAccuracy(false);
    }
  };

  // Effect to refetch accuracy data when selections change
  createEffect(() => {
    const siteId = selectedSiteId();
    const parameterId = selectedParameterId();
    const horizon = selectedHorizon();

    if (siteId && parameterId) {
      loadAccuracyData(siteId, parameterId, horizon);
    }
  });

  // Load initial data on mount
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

  const isLoadingSelectors = () => isLoadingSites() || isLoadingParameters();

  return (
    <div class="container mx-auto px-4 py-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-2">
        MétéoScore
      </h1>
      <p class="text-gray-600 mb-8">
        Compare weather forecast accuracy across different models for paragliding sites.
      </p>

      {/* Error state for initial load */}
      <Show when={error()}>
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          <p class="font-medium">Error loading data</p>
          <p class="text-sm">{error()}</p>
        </div>
      </Show>

      {/* Loading state for selectors */}
      <Show when={isLoadingSelectors()}>
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="animate-pulse space-y-4">
            <div class="h-4 bg-gray-200 rounded w-1/4" />
            <div class="h-10 bg-gray-200 rounded" />
            <div class="h-4 bg-gray-200 rounded w-1/4" />
            <div class="h-6 bg-gray-200 rounded w-1/2" />
          </div>
        </div>
      </Show>

      {/* Main content when selectors are loaded */}
      <Show when={!isLoadingSelectors() && !error()}>
        {/* Selectors - responsive grid */}
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

        {/* Accuracy error state */}
        <Show when={accuracyError()}>
          <div class="bg-orange-50 border border-orange-200 text-orange-700 px-4 py-3 rounded-lg mb-6">
            <p class="font-medium">Could not load accuracy data</p>
            <p class="text-sm">{accuracyError()}</p>
          </div>
        </Show>

        {/* Loading state for accuracy data */}
        <Show when={isLoadingAccuracy()}>
          <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <div class="animate-pulse space-y-4">
              <div class="h-6 bg-gray-200 rounded w-1/3" />
              <div class="h-40 bg-gray-200 rounded" />
            </div>
          </div>
        </Show>

        {/* Model comparison table */}
        <Show when={!isLoadingAccuracy() && !accuracyError() && accuracyData()}>
          {(data) => (
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
              <ModelComparisonTable
                models={data().models}
                parameterUnit={selectedParameterUnit()}
              />
            </div>
          )}
        </Show>
      </Show>
    </div>
  );
};

export default Home;
