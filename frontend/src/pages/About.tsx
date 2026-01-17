import type { Component } from 'solid-js';

/**
 * About/Methodology page component.
 * Displays comprehensive methodology documentation including:
 * - How MétéoScore works
 * - Metrics explained (MAE, Bias)
 * - Data sources (forecast models, observation networks)
 * - Data collection process
 * - Confidence levels
 * - Limitations
 * - Open source information
 */
const About: Component = () => {
  return (
    <div class="container mx-auto px-4 py-8">
      <div class="max-w-4xl mx-auto">
        {/* Page Title */}
        <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mb-6">
          Methodology
        </h1>

        {/* How MétéoScore Works */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-gray-800 mb-4">
            How MétéoScore Works
          </h2>
          <p class="text-gray-600 leading-relaxed mb-4">
            MétéoScore objectively evaluates weather forecast model accuracy by comparing
            forecast predictions against real-world observations from weather beacons and stations.
            This helps paragliding pilots and outdoor enthusiasts understand which forecasts
            are most reliable for their specific flying sites.
          </p>
        </section>

        {/* Metrics Explained */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-gray-800 mt-8 mb-4">
            Metrics Explained
          </h2>

          {/* MAE */}
          <h3 class="text-xl font-medium text-gray-700 mt-6 mb-3">
            Mean Absolute Error (MAE)
          </h3>
          <div class="bg-gray-100 p-4 rounded-lg my-4 font-mono text-sm text-gray-800">
            MAE = Average(|Forecast - Observation|)
          </div>
          <p class="text-gray-600 leading-relaxed mb-4">
            MAE measures the average magnitude of forecast errors. Lower is better.
            For example, an MAE of 4.2 km/h for wind speed means the model is typically
            off by approximately 4.2 km/h in either direction.
          </p>

          {/* Bias */}
          <h3 class="text-xl font-medium text-gray-700 mt-6 mb-3">
            Bias (Systematic Error)
          </h3>
          <div class="bg-gray-100 p-4 rounded-lg my-4 font-mono text-sm text-gray-800">
            Bias = Average(Forecast - Observation)
          </div>
          <ul class="list-disc list-outside text-gray-600 space-y-2 mb-4 ml-6">
            <li>
              <strong>Positive bias:</strong> Model systematically overestimates
              (e.g., predicts stronger wind than actually observed)
            </li>
            <li>
              <strong>Negative bias:</strong> Model systematically underestimates
              (e.g., predicts weaker wind than actually observed)
            </li>
            <li>
              <strong>Zero bias:</strong> No systematic tendency - errors are random
            </li>
          </ul>
        </section>

        {/* Data Sources */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-gray-800 mt-8 mb-4">
            Data Sources
          </h2>

          <h3 class="text-xl font-medium text-gray-700 mt-6 mb-3">
            Forecast Models
          </h3>
          <ul class="list-disc list-outside text-gray-600 space-y-2 mb-4 ml-6">
            <li>
              <strong>AROME</strong> - Météo-France high-resolution numerical weather model
              (2.5km grid resolution, updated 4x daily)
            </li>
            <li>
              <strong>Meteo-Parapente</strong> - Specialized forecast service optimized
              for paragliding conditions
            </li>
          </ul>

          <h3 class="text-xl font-medium text-gray-700 mt-6 mb-3">
            Observation Networks
          </h3>
          <ul class="list-disc list-outside text-gray-600 space-y-2 mb-4 ml-6">
            <li>
              <strong>ROMMA</strong> - Network of automated mountain weather beacons
              providing real-time observations
            </li>
            <li>
              <strong>FFVL</strong> - French Free Flight Federation weather stations
              at popular flying sites
            </li>
          </ul>
        </section>

        {/* Data Collection Process */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-gray-800 mt-8 mb-4">
            Data Collection Process
          </h2>
          <ol class="list-decimal list-outside text-gray-600 space-y-2 mb-4 ml-6">
            <li>Forecasts are retrieved 4 times daily (00h, 06h, 12h, 18h UTC model runs)</li>
            <li>Observations are collected 6 times daily from beacon networks</li>
            <li>Forecasts are matched with observations within a 30-minute window</li>
            <li>Deviation is calculated: Forecast Value - Observed Value</li>
            <li>Aggregate metrics (MAE, Bias) are computed from 90+ days of historical deviations</li>
          </ol>
        </section>

        {/* Confidence Levels */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-gray-800 mt-8 mb-4">
            Confidence Levels
          </h2>
          <p class="text-gray-600 leading-relaxed mb-4">
            The reliability of our metrics depends on how much historical data is available
            for each site:
          </p>
          <div class="overflow-x-auto">
            <table class="min-w-full border border-gray-200 my-4">
              <thead>
                <tr class="bg-gray-50">
                  <th class="border border-gray-200 px-4 py-3 text-left font-semibold text-gray-700">
                    Level
                  </th>
                  <th class="border border-gray-200 px-4 py-3 text-left font-semibold text-gray-700">
                    Days of Data
                  </th>
                  <th class="border border-gray-200 px-4 py-3 text-left font-semibold text-gray-700">
                    Interpretation
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td class="border border-gray-200 px-4 py-3 text-gray-600">
                    <span class="inline-flex items-center">
                      <span class="mr-2">&#x2705;</span> Validated
                    </span>
                  </td>
                  <td class="border border-gray-200 px-4 py-3 text-gray-600">90+ days</td>
                  <td class="border border-gray-200 px-4 py-3 text-gray-600">
                    Statistically reliable metrics
                  </td>
                </tr>
                <tr class="bg-gray-50">
                  <td class="border border-gray-200 px-4 py-3 text-gray-600">
                    <span class="inline-flex items-center">
                      <span class="mr-2">&#x1F536;</span> Preliminary
                    </span>
                  </td>
                  <td class="border border-gray-200 px-4 py-3 text-gray-600">30-89 days</td>
                  <td class="border border-gray-200 px-4 py-3 text-gray-600">
                    Results will stabilize with more data
                  </td>
                </tr>
                <tr>
                  <td class="border border-gray-200 px-4 py-3 text-gray-600">
                    <span class="inline-flex items-center">
                      <span class="mr-2">&#x26A0;&#xFE0F;</span> Insufficient
                    </span>
                  </td>
                  <td class="border border-gray-200 px-4 py-3 text-gray-600">&lt;30 days</td>
                  <td class="border border-gray-200 px-4 py-3 text-gray-600">
                    Not enough data for reliable conclusions
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Limitations */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-gray-800 mt-8 mb-4">
            Limitations
          </h2>
          <ul class="list-disc list-outside text-gray-600 space-y-2 mb-4 ml-6">
            <li>
              <strong>Past performance:</strong> Metrics reflect historical accuracy and
              do not guarantee future forecast quality
            </li>
            <li>
              <strong>Site-specific:</strong> Results at one location may not apply to
              nearby sites with different terrain or microclimate
            </li>
            <li>
              <strong>Extreme events:</strong> Rare weather events may not be well-represented
              in the statistics
            </li>
            <li>
              <strong>Measurement uncertainty:</strong> Observation beacons have their own
              measurement errors (typically ±0.5 km/h for wind, ±0.3°C for temperature)
            </li>
          </ul>
        </section>

        {/* Transparency & Open Source */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-gray-800 mt-8 mb-4">
            Transparency & Open Source
          </h2>
          <p class="text-gray-600 leading-relaxed mb-4">
            MétéoScore is fully open source. All code, methodology, and data processing
            logic are publicly available for review and verification:
          </p>
          <ul class="list-disc list-outside text-gray-600 space-y-2 mb-4 ml-6">
            <li>
              <a
                href="https://github.com/AurelienS/meteo-score"
                class="text-primary-500 hover:text-primary-600 hover:underline focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded inline-flex items-center gap-1"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub Repository
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
              {' '}- Source code and documentation
            </li>
            <li>
              <a
                href="https://github.com/AurelienS/meteo-score/blob/main/docs/METHODOLOGY.md"
                class="text-primary-500 hover:text-primary-600 hover:underline focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded inline-flex items-center gap-1"
                target="_blank"
                rel="noopener noreferrer"
              >
                Technical Documentation
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
              {' '}- Detailed methodology and algorithms
            </li>
          </ul>
        </section>

        {/* Questions or Feedback */}
        <section class="mb-8">
          <h2 class="text-2xl font-semibold text-gray-800 mt-8 mb-4">
            Questions or Feedback?
          </h2>
          <p class="text-gray-600 leading-relaxed mb-4">
            We welcome questions, suggestions, and bug reports. Please open an issue on{' '}
            <a
              href="https://github.com/AurelienS/meteo-score/issues"
              class="text-primary-500 hover:text-primary-600 hover:underline focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded inline-flex items-center gap-1"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
            {' '}or reach out to the maintainers.
          </p>
        </section>
      </div>
    </div>
  );
};

export default About;
