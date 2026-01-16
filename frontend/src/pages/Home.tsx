import type { Component } from 'solid-js';
import { createSignal, createEffect, createMemo, onMount, Show, For } from 'solid-js';

import SiteSelector from '../components/SiteSelector';
import ParameterSelector from '../components/ParameterSelector';
import HorizonSelector from '../components/HorizonSelector';
import ModelComparisonTable from '../components/ModelComparisonTable';
import DataFreshnessIndicator from '../components/DataFreshnessIndicator';
import BiasCharacterizationCard from '../components/BiasCharacterizationCard';
import AccuracyTimeSeriesChart, { getModelColor } from '../components/AccuracyTimeSeriesChart';
import type { ModelTimeSeries } from '../components/AccuracyTimeSeriesChart';
import { fetchSites, fetchParameters, fetchSiteAccuracy, fetchAccuracyTimeSeries, NetworkError, TimeoutError } from '../lib/api';
import type { Site, Parameter, SiteAccuracyResponse, ModelAccuracyMetrics, ConfidenceLevel } from '../lib/types';

/** Standard forecast horizons for MVP */
const FORECAST_HORIZONS = [6, 12, 24, 48];

/** Confidence levels ordered from lowest to highest for conservative comparison */
const CONFIDENCE_LEVELS_ORDERED: ConfidenceLevel[] = ['insufficient', 'preliminary', 'validated'];

/**
 * Get user-friendly error message based on error type.
 */
function getErrorMessage(err: unknown): string {
  if (err instanceof TimeoutError) {
    return 'Request timed out. The server may be busy - please try again later.';
  }
  if (err instanceof NetworkError) {
    return 'Unable to connect. Please check your internet connection.';
  }
  if (err instanceof Error) {
    return err.message;
  }
  return 'An unexpected error occurred.';
}

/**
 * Home page component.
 * Displays site, parameter, and horizon selectors for model comparison.
 */
const Home: Component = () => {
  // Data state - loaded from API
  const [sites, setSites] = createSignal<Site[]>([]);
  const [parameters, setParameters] = createSignal<Parameter[]>([]);
  const [accuracyData, setAccuracyData] = createSignal<SiteAccuracyResponse | null>(null);
  const [timeSeriesData, setTimeSeriesData] = createSignal<ModelTimeSeries[]>([]);

  // Selection state
  const [selectedSiteId, setSelectedSiteId] = createSignal<number>(0);
  const [selectedParameterId, setSelectedParameterId] = createSignal<number>(0);
  const [selectedHorizon, setSelectedHorizon] = createSignal<number>(6);

  // Loading states - specific per resource
  const [isLoadingSites, setIsLoadingSites] = createSignal(true);
  const [isLoadingParameters, setIsLoadingParameters] = createSignal(true);
  const [isLoadingAccuracy, setIsLoadingAccuracy] = createSignal(false);
  const [isLoadingTimeSeries, setIsLoadingTimeSeries] = createSignal(false);

  // Error state
  const [error, setError] = createSignal<string | null>(null);
  const [accuracyError, setAccuracyError] = createSignal<string | null>(null);
  const [timeSeriesError, setTimeSeriesError] = createSignal<string | null>(null);

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
      setAccuracyError(getErrorMessage(err));
      setAccuracyData(null);
    } finally {
      setIsLoadingAccuracy(false);
    }
  };

  // Fetch time series for all models
  const loadTimeSeriesData = async (
    siteId: number,
    parameterId: number,
    models: ModelAccuracyMetrics[]
  ) => {
    if (!siteId || !parameterId || models.length === 0) {
      setTimeSeriesData([]);
      return;
    }

    setIsLoadingTimeSeries(true);
    setTimeSeriesError(null);

    try {
      // Fetch in parallel for all models
      const responses = await Promise.all(
        models.map(model =>
          fetchAccuracyTimeSeries(siteId, model.modelId, parameterId)
        )
      );

      // Transform to chart format
      const chartData: ModelTimeSeries[] = responses.map((response, index) => ({
        modelId: response.modelId,
        modelName: response.modelName,
        color: getModelColor(response.modelName, index),
        data: response.dataPoints.map(dp => ({
          date: new Date(dp.bucket),
          mae: dp.mae,
        })),
      }));

      setTimeSeriesData(chartData);
    } catch (err) {
      setTimeSeriesError(getErrorMessage(err));
      setTimeSeriesData([]);
    } finally {
      setIsLoadingTimeSeries(false);
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

  // Effect to load time series after accuracy data loads
  createEffect(() => {
    const data = accuracyData();
    if (data && data.models.length > 0) {
      loadTimeSeriesData(data.siteId, data.parameterId, data.models);
    } else {
      setTimeSeriesData([]);
    }
  });

  // Shared function for loading initial data (sites and parameters)
  const loadInitialData = async () => {
    setError(null);
    setIsLoadingSites(true);
    setIsLoadingParameters(true);

    try {
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
      setError(getErrorMessage(err));
    } finally {
      setIsLoadingSites(false);
      setIsLoadingParameters(false);
    }
  };

  // Load initial data on mount
  onMount(() => {
    loadInitialData();
  });

  const isLoadingSelectors = () => isLoadingSites() || isLoadingParameters();

  // Retry handler for accuracy data
  const retryAccuracyLoad = () => {
    loadAccuracyData(selectedSiteId(), selectedParameterId(), selectedHorizon());
  };

  // Retry handler for time series data
  const retryTimeSeriesLoad = () => {
    const data = accuracyData();
    if (data && data.models.length > 0) {
      loadTimeSeriesData(data.siteId, data.parameterId, data.models);
    }
  };

  // Derive freshness data from time series and accuracy data
  const freshnessData = createMemo(() => {
    const tsData = timeSeriesData();
    const accData = accuracyData();

    if (!accData || tsData.length === 0) return null;

    // Get all bucket dates from all models
    const allBuckets = tsData.flatMap(m => m.data.map(d => d.date));
    if (allBuckets.length === 0) return null;

    // Sort to find min/max dates (spread to avoid mutating original array)
    const sortedBuckets = [...allBuckets].sort((a, b) => a.getTime() - b.getTime());

    // Aggregate sample size (sum across models)
    const totalSampleSize = accData.models.reduce((sum, m) => sum + m.sampleSize, 0);

    // Use lowest confidence level (most conservative)
    const lowestConfidence = accData.models.reduce((lowest, m) => {
      const currentIdx = CONFIDENCE_LEVELS_ORDERED.indexOf(m.confidenceLevel);
      const lowestIdx = CONFIDENCE_LEVELS_ORDERED.indexOf(lowest);
      return currentIdx < lowestIdx ? m.confidenceLevel : lowest;
    }, 'validated' as ConfidenceLevel);

    return {
      lastUpdate: sortedBuckets[sortedBuckets.length - 1],
      sampleSize: totalSampleSize,
      dateRange: {
        start: sortedBuckets[0],
        end: sortedBuckets[sortedBuckets.length - 1],
      },
      confidenceLevel: lowestConfidence,
    };
  });

  return (
    <div class="container mx-auto px-4 py-8">
      <h1 class="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
        MétéoScore
      </h1>
      <p class="text-sm md:text-base text-gray-600 mb-8">
        Compare weather forecast accuracy across different models for paragliding sites.
      </p>

      {/* Error state for initial load */}
      <Show when={error()}>
        <div role="alert" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          <p class="font-medium">Error loading data</p>
          <p class="text-sm mb-3">{error()}</p>
          <button
            type="button"
            class="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors min-h-[44px] disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={loadInitialData}
            disabled={isLoadingSelectors()}
          >
            {isLoadingSelectors() ? 'Retrying...' : 'Retry'}
          </button>
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
          <div role="alert" class="bg-orange-50 border border-orange-200 text-orange-700 px-4 py-3 rounded-lg mb-6">
            <p class="font-medium">Could not load accuracy data</p>
            <p class="text-sm mb-3">{accuracyError()}</p>
            <button
              type="button"
              class="px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 transition-colors min-h-[44px] disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={retryAccuracyLoad}
              disabled={isLoadingAccuracy()}
            >
              {isLoadingAccuracy() ? 'Retrying...' : 'Retry'}
            </button>
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

        {/* Model comparison table and bias cards */}
        <Show when={!isLoadingAccuracy() && !accuracyError() && accuracyData()}>
          {(data) => (
            <>
              {/* Model comparison table */}
              <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <ModelComparisonTable
                  models={data().models}
                  parameterUnit={selectedParameterUnit()}
                />
              </div>

              {/* Data freshness indicator - only show when time series has loaded */}
              <Show when={!isLoadingTimeSeries() && freshnessData()}>
                {(freshness) => (
                  <div class="mb-6">
                    <DataFreshnessIndicator
                      lastUpdate={freshness().lastUpdate}
                      sampleSize={freshness().sampleSize}
                      dateRange={freshness().dateRange}
                      confidenceLevel={freshness().confidenceLevel}
                    />
                  </div>
                )}
              </Show>

              {/* Bias characterization cards */}
              <Show when={data().models.length > 0}>
                <div class="mb-6">
                  <h2 class="text-base md:text-lg font-semibold text-gray-900 mb-4">
                    Bias Characterization
                  </h2>
                  <div class="space-y-4">
                    <For each={data().models}>
                      {(model) => (
                        <BiasCharacterizationCard
                          modelName={model.modelName}
                          bias={model.bias}
                          parameterName={data().parameterName}
                          parameterUnit={selectedParameterUnit()}
                          confidenceLevel={model.confidenceLevel}
                        />
                      )}
                    </For>
                  </div>
                </div>
              </Show>

              {/* Time series error state */}
              <Show when={timeSeriesError()}>
                <div role="alert" class="bg-orange-50 border border-orange-200 text-orange-700 px-4 py-3 rounded-lg mb-6">
                  <p class="font-medium">Could not load time series data</p>
                  <p class="text-sm mb-3">{timeSeriesError()}</p>
                  <button
                    type="button"
                    class="px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 transition-colors min-h-[44px] disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={retryTimeSeriesLoad}
                    disabled={isLoadingTimeSeries()}
                  >
                    {isLoadingTimeSeries() ? 'Retrying...' : 'Retry'}
                  </button>
                </div>
              </Show>

              {/* Time series chart loading state */}
              <Show when={isLoadingTimeSeries()}>
                <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                  <div class="animate-pulse space-y-4">
                    <div class="h-6 bg-gray-200 rounded w-1/3" />
                    <div class="h-80 bg-gray-200 rounded" />
                  </div>
                </div>
              </Show>

              {/* Accuracy time series chart */}
              <Show when={!isLoadingTimeSeries() && !timeSeriesError()}>
                <div class="mb-6">
                  <AccuracyTimeSeriesChart
                    models={timeSeriesData()}
                    parameterUnit={selectedParameterUnit()}
                  />
                </div>
              </Show>
            </>
          )}
        </Show>
      </Show>
    </div>
  );
};

export default Home;
